"""Private conversations; backend ownership checks apply to every read and turn."""
from datetime import datetime, timedelta
from time import monotonic
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User
from app.models.chat import ChatConversation, ChatTurn
from app.models.agent_run import AgentRun, AgentRunStatus
from app.services.chat_providers import provider_ready, data_policy
from app.services.chat_graph import run_chat
from app.core.rate_limiter import shared_rate_limiter

router = APIRouter(prefix="/api/v1/chat", tags=["assistant"])


class TurnInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request_id: UUID
    question: str = Field(min_length=1, max_length=2000)


def serialize_turn(row):
    return {"id":row.id, "request_id":row.request_id, "sequence":row.sequence,
            "question":row.question, "answer":row.answer, "sources":row.sources,
            "mode":row.mode, "notice":row.notice, "created_at":row.created_at.isoformat()+"Z"}


def owned(db, conversation_id, user, lock=False):
    query = db.query(ChatConversation).filter_by(id=conversation_id, user_id=user.id)
    if lock:
        query = query.populate_existing().with_for_update()
    row = query.first()
    if not row:
        raise HTTPException(404, "Conversation not found")
    return row


@router.get("/status")
def chat_status():
    return {"provider":settings.CHAT_PROVIDER, "provider_ready":provider_ready(),
            "read_only":True, "max_turns":settings.CHAT_MAX_TURNS,
            "data_policy":data_policy()}


@router.get("/conversations")
def conversations(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(ChatConversation).filter_by(user_id=user.id).order_by(ChatConversation.updated_at.desc(),ChatConversation.id).limit(50).all()
    return [{"id":row.id,"title":row.title,"turn_count":row.turn_count,"updated_at":row.updated_at.isoformat()+"Z"} for row in rows]


@router.post("/conversations", status_code=201)
def create_conversation(db: Session = Depends(get_db), user=Depends(get_current_user)):
    db.query(User).filter_by(id=user.id).with_for_update().one()
    if db.query(ChatConversation).filter_by(user_id=user.id).count() >= 50:
        raise HTTPException(409, "Conversation limit reached (50). Delete an old conversation first.")
    row = ChatConversation(user_id=user.id)
    db.add(row); db.commit()
    return {"id":row.id,"title":row.title,"turn_count":row.turn_count,"updated_at":row.updated_at.isoformat()+"Z"}


@router.get("/conversations/{conversation_id}")
def conversation(conversation_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = owned(db, conversation_id, user)
    turns = db.query(ChatTurn).filter_by(conversation_id=row.id).order_by(ChatTurn.sequence).all()
    return {"id":row.id,"title":row.title,"turns":[serialize_turn(turn) for turn in turns]}


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    db.query(User).filter_by(id=user.id).with_for_update().one()
    row = owned(db, conversation_id, user, lock=True)
    db.query(ChatTurn).filter_by(conversation_id=row.id).delete(synchronize_session=False)
    db.delete(row); db.commit()


@router.post("/conversations/{conversation_id}/turns")
def post_turn(conversation_id: str, data: TurnInput, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # Serialize this user's chat requests across API workers; no inventory locks.
    current = db.query(User).filter_by(id=user.id).populate_existing().with_for_update().one()
    if not current.is_active:
        raise HTTPException(401, "Account disabled")
    row = owned(db, conversation_id, user, lock=True)
    existing = db.query(ChatTurn).filter_by(conversation_id=row.id, request_id=str(data.request_id)).first()
    if existing:
        if existing.question != data.question:
            raise HTTPException(409, "Request ID was already used for another question")
        return serialize_turn(existing)
    if row.turn_count >= settings.CHAT_MAX_TURNS:
        raise HTTPException(409, "Conversation is full; start a new conversation")
    recent = db.query(ChatTurn).join(ChatConversation).filter(ChatConversation.user_id==user.id,
        ChatTurn.created_at >= datetime.utcnow()-timedelta(minutes=1)).count()
    if recent >= settings.CHAT_REQUESTS_PER_MINUTE:
        raise HTTPException(429, "Assistant request limit reached; wait a minute", headers={"Retry-After":"60"})
    decision = shared_rate_limiter.check(f"chat:user:{user.id}", settings.CHAT_REQUESTS_PER_MINUTE, 60)
    if not decision.allowed:
        raise HTTPException(429, "Assistant request limit reached; wait a minute",
                            headers={"Retry-After":str(decision.retry_after)})
    previous = db.query(ChatTurn).filter_by(conversation_id=row.id).order_by(ChatTurn.sequence.desc()).first()
    start = monotonic()
    try:
        result = run_chat(db, data.question, previous.plan if previous else None)
    except Exception:
        db.rollback()
        raise HTTPException(503, "Assistant temporarily unavailable. Inventory monitoring is unaffected.")
    row.turn_count += 1
    if row.turn_count == 1:
        row.title = data.question[:100]
    row.updated_at = datetime.utcnow()
    turn = ChatTurn(conversation_id=row.id, request_id=str(data.request_id), sequence=row.turn_count,
        question=data.question, answer=result["answer"], sources=result["sources"], plan=result["plan"],
        mode=result["mode"], notice=result["notice"])
    db.add(turn)
    # Agent Activity is shared: never put private prompts, filters, answers or IDs there.
    db.add(AgentRun(agent_type="chat", status=AgentRunStatus.COMPLETED,
        trigger_event="user_question", output_action="Read-only answer generated",
        execution_time_ms=int((monotonic()-start)*1000), llm_provider=result["mode"]))
    db.commit()
    return serialize_turn(turn)
