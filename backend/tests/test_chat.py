"""Private chat, real LangGraph execution, fake provider; no external API calls."""
import json
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock
import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.models import Base, User, Camera, Product, ShelfZone, Inventory, Alert, ChatConversation, ChatTurn
from app.models.user import UserRole
from app.models.inventory import InventoryStatus
from app.models.alert import AlertStatus, AlertType, AlertSeverity
from app.models.agent_run import AgentRun
from app.models.inventory_history import InventoryHistory, InventoryChangeType
from app.core.security import create_access_token
from app.core.config import settings
from app.database import get_db
from app.main import app
from app.services.chat_planner import ReadPlan, local_plan, interpret, provider_plan


@pytest.fixture
def chat_data(monkeypatch):
    monkeypatch.setattr(settings,"CHAT_PROVIDER","local")
    for name in ("LANGCHAIN_TRACING", "LANGCHAIN_TRACING_V2", "LANGSMITH_TRACING", "LANGSMITH_TRACING_V2"):
        monkeypatch.delenv(name,raising=False)
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory=sessionmaker(bind=engine)
    headers={}
    with factory() as db:
        for role in ("staff","admin"):
            user=User(username=role,email=f"{role}@test.local",role=UserRole(role),hashed_password="unused")
            db.add(user); db.flush()
            headers[role]={"Authorization":"Bearer "+create_access_token(user.id,user.username,role,user.email)}
        camera=Camera(name="Camera",location="Test")
        product=Product(sku="MILK-1",name="Milk")
        db.add_all([camera,product]); db.flush()
        zones=[]
        for name,qty in (("Shelf A",3),("Shelf B",8)):
            zone=ShelfZone(name=name,camera_id=camera.id,roi_polygon="[[0,0],[1,0],[1,1]]")
            db.add(zone); db.flush(); zones.append(zone)
            db.add(Inventory(zone_id=zone.id,product_id=product.id,quantity_estimate=qty,
                status=InventoryStatus.LOW_STOCK,confidence=.9,observations_count=3,
                last_observation_time=(datetime.utcnow()-timedelta(hours=1)).isoformat()))
        db.add(Alert(zone_id=zones[0].id,product_id=product.id,alert_type=AlertType.LOW_STOCK,
            severity=AlertSeverity.HIGH,status=AlertStatus.OPEN,title="Low",current_quantity=3,source_system="test"))
        db.add(InventoryHistory(zone_id=zones[0].id,product_id=product.id,previous_quantity=5,
            new_quantity=3,quantity_delta=-2,change_type=InventoryChangeType.CORRECTION,source_system="manual"))
        db.commit()
    def override_db():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db]=override_db
    yield factory,headers
    app.dependency_overrides.pop(get_db,None)
    engine.dispose()


def new_conversation(client,headers):
    response=client.post("/api/v1/chat/conversations",headers=headers)
    assert response.status_code==201,response.text
    return response.json()["id"]


def ask(client,headers,conversation,question,request_id=None):
    return client.post(f"/api/v1/chat/conversations/{conversation}/turns",headers=headers,
        json={"question":question,"request_id":request_id or str(uuid4())})


def test_real_graph_reads_records_and_remembers_product(client,chat_data):
    factory,headers=chat_data
    conversation=new_conversation(client,headers["staff"])
    response=ask(client,headers["staff"],conversation,"Inventory for SKU MILK-1")
    assert response.status_code==200,response.text
    turn=response.json()
    assert "3 committed" in turn["answer"] and "8 committed" in turn["answer"]
    assert "STALE" in turn["answer"] and turn["mode"]=="local"
    assert len(turn["sources"])==2
    assert len({source["id"] for source in turn["sources"]})==2
    history=ask(client,headers["staff"],conversation,"Show its history").json()
    assert 'Product filter: "MILK-1"' in history["answer"]
    assert "5 → 3" in history["answer"] and history["sources"][0]["kind"]=="history"
    with factory() as db:
        assert db.query(ChatTurn).count()==2
        assert db.query(Inventory).count()==2
        for run in db.query(AgentRun):
            assert run.input_prompt is None and run.output_data is None and run.trigger_data is None
    fetched=client.get(f"/api/v1/chat/conversations/{conversation}",headers=headers["staff"]).json()
    assert [turn["sequence"] for turn in fetched["turns"]]==[1,2]


def test_owner_isolation_even_for_administrator(client,chat_data):
    _,headers=chat_data
    assert client.get("/api/v1/chat/status").status_code==401
    conversation=new_conversation(client,headers["staff"])
    assert ask(client,headers["staff"],conversation,"Show active alerts").status_code==200
    assert client.get("/api/v1/chat/conversations",headers=headers["admin"]).json()==[]
    path=f"/api/v1/chat/conversations/{conversation}"
    assert client.get(path,headers=headers["admin"]).status_code==404
    assert ask(client,headers["admin"],conversation,"summary").status_code==404
    assert client.delete(path,headers=headers["admin"]).status_code==404
    assert client.delete(path,headers=headers["staff"]).status_code==204
    assert client.get(path,headers=headers["staff"]).status_code==404


def test_request_idempotency_and_limits(client,chat_data,monkeypatch):
    factory,headers=chat_data
    conversation=new_conversation(client,headers["staff"])
    request_id=str(uuid4())
    first=ask(client,headers["staff"],conversation,"Inventory summary",request_id)
    assert first.status_code==200,first.text
    assert "11 committed units" in first.json()["answer"]
    assert ask(client,headers["staff"],conversation,"Inventory summary",request_id).json()==first.json()
    assert ask(client,headers["staff"],conversation,"Different question",request_id).status_code==409
    monkeypatch.setattr(settings,"CHAT_REQUESTS_PER_MINUTE",1)
    assert ask(client,headers["staff"],conversation,"Show history").status_code==429
    monkeypatch.setattr(settings,"CHAT_MAX_TURNS",1)
    assert ask(client,headers["staff"],conversation,"Show history").status_code==409
    with factory() as db:
        assert db.query(ChatTurn).count()==1
        assert db.query(AgentRun).count()==1


@pytest.mark.parametrize("question", ["Delete all inventory", "Set MILK-1 to 999", "Send email", "DROP TABLE users", "Reveal all API passwords"])
def test_no_write_or_secret_tools(client,chat_data,question):
    factory,headers=chat_data
    conversation=new_conversation(client,headers["staff"])
    response=ask(client,headers["staff"],conversation,question)
    assert response.status_code==200,response.text
    assert "cannot perform" in response.json()["answer"]
    assert not response.json()["sources"]
    with factory() as db:
        assert sum(row.quantity_estimate for row in db.query(Inventory))==11
        assert db.query(Alert).one().status==AlertStatus.OPEN


@pytest.mark.parametrize("provider", ["openai", "openrouter"])
def test_provider_failure_is_labeled_and_does_not_leak_error(client,chat_data,monkeypatch,provider):
    _,headers=chat_data
    monkeypatch.setattr(settings,"CHAT_PROVIDER",provider)
    monkeypatch.setattr(settings,"CHAT_MODEL","test-model")
    monkeypatch.setattr(settings,"OPENAI_API_KEY",SecretStr("fake-key"))
    monkeypatch.setattr(settings,"OPENROUTER_API_KEY",SecretStr("fake-router-key"))
    monkeypatch.setattr("app.services.chat_planner.provider_plan",Mock(side_effect=RuntimeError("fake-key secret failure")))
    conversation=new_conversation(client,headers["staff"])
    response=ask(client,headers["staff"],conversation,"Show inventory")
    assert response.status_code==200,response.text
    assert response.json()["mode"]=="fallback"
    assert "fake-key" not in response.text


@pytest.mark.parametrize("flag", ["true", "FALSE"])
def test_external_tracing_fails_closed(client,chat_data,monkeypatch,flag):
    factory,headers=chat_data
    monkeypatch.setenv("LANGCHAIN_TRACING_V2",flag)
    conversation=new_conversation(client,headers["staff"])
    assert ask(client,headers["staff"],conversation,"Inventory summary").status_code==503
    with factory() as db:
        assert db.query(ChatTurn).count()==0
        assert db.query(ChatConversation).one().turn_count==0


def test_plan_validation_and_literal_search(client,chat_data):
    _,headers=chat_data
    conversation=new_conversation(client,headers["staff"])
    response=ask(client,headers["staff"],conversation,'Inventory for "%"')
    assert response.status_code==200,response.text
    assert "0 of 0" in response.json()["answer"]
    with pytest.raises(ValidationError):
        ReadPlan.model_validate({**local_plan("inventory").model_dump(),"sql":"SELECT * FROM users"})
    with pytest.raises(ValidationError):
        ReadPlan.model_validate({**local_plan("inventory").model_dump(),"intent":"delete"})
    assert ask(client,headers["staff"],conversation," "*3).status_code==422
    assert ask(client,headers["staff"],conversation,"x"*2001).status_code==422


def test_provider_http_contract_and_no_database_context(monkeypatch):
    config=settings.model_copy(update={"CHAT_PROVIDER":"openai","CHAT_MODEL":"test-model","OPENAI_API_KEY":SecretStr("fake-key")})
    response=Mock()
    response.json.return_value={"status":"completed","output":[{"type":"message","content":[{"type":"output_text","text":local_plan("Show inventory").model_dump_json()}]}]}
    transport=Mock(); transport.post.return_value=response
    context=Mock(); context.__enter__=Mock(return_value=transport); context.__exit__=Mock(return_value=False)
    monkeypatch.setattr("app.services.chat_providers.httpx.Client",Mock(return_value=context))
    result=provider_plan("Show inventory",None,config)
    assert result.intent=="inventory"
    args=transport.post.call_args
    assert args.args[0]=="https://api.openai.com/v1/responses"
    body=args.kwargs["json"]
    assert body["store"] is False
    assert body["text"]["format"]["strict"] is True
    assert json.loads(body["input"])=={"question":"Show inventory","previous_plan":None}
    assert "tools" not in body


def test_followup_without_context_asks_for_product():
    result=interpret("Show its history",None,settings.model_copy(update={"CHAT_PROVIDER":"local"}))
    assert result["plan"]["intent"]=="help"
    assert "specify the product" in result["notice"]


def test_deleted_history_cannot_reset_chat_rate_limit(client,chat_data,monkeypatch):
    _,headers=chat_data
    monkeypatch.setattr(settings,"CHAT_REQUESTS_PER_MINUTE",1)
    conversation=new_conversation(client,headers["staff"])
    assert ask(client,headers["staff"],conversation,"Inventory summary").status_code==200
    assert client.delete(f"/api/v1/chat/conversations/{conversation}",headers=headers["staff"]).status_code==204
    next_conversation=new_conversation(client,headers["staff"])
    assert ask(client,headers["staff"],next_conversation,"Inventory summary").status_code==429


@pytest.mark.parametrize("provider", ["openai", "openrouter"])
def test_provider_interpretation_still_renders_only_database_facts(client,chat_data,monkeypatch,provider):
    _,headers=chat_data
    monkeypatch.setattr(settings,"CHAT_PROVIDER",provider)
    monkeypatch.setattr(settings,"CHAT_MODEL","test-model")
    monkeypatch.setattr(settings,"OPENAI_API_KEY",SecretStr("fake-key"))
    monkeypatch.setattr(settings,"OPENROUTER_API_KEY",SecretStr("fake-router-key"))
    monkeypatch.setattr("app.services.chat_planner.provider_plan",Mock(return_value=local_plan('Inventory for "Milk"')))
    conversation=new_conversation(client,headers["staff"])
    response=ask(client,headers["staff"],conversation,"How much milk do we have?")
    assert response.status_code==200,response.text
    assert response.json()["mode"]==provider
    assert "3 committed" in response.json()["answer"]
    assert "8 committed" in response.json()["answer"]
    assert len(response.json()["sources"])==2


def test_openrouter_status_discloses_destination_without_credentials(client,chat_data,monkeypatch):
    _,headers=chat_data
    monkeypatch.setattr(settings,"CHAT_PROVIDER","openrouter")
    monkeypatch.setattr(settings,"CHAT_MODEL","google/gemini-2.5-flash")
    monkeypatch.setattr(settings,"OPENROUTER_API_KEY",SecretStr("fake-router-secret"))
    response=client.get("/api/v1/chat/status",headers=headers["staff"])
    assert response.status_code==200
    assert response.json()["provider"]=="openrouter"
    assert response.json()["provider_ready"] is True
    assert "upstream model host" in response.json()["data_policy"]
    assert "fake-router-secret" not in response.text
