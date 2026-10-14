"""Approved permission matrix exercised through real HTTP handlers and isolated DBs."""
from uuid import uuid4
import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute
from app.main import app
from app.database import SessionLocal
from app.models import Inventory, User, Camera, OperationalRequest
from app.models.audit_log import AuditLog
from app.core.security import create_access_token
from app.core.permissions import ROUTE_PERMISSIONS, authorize, permissions_for
from app.services.chat_tools import execute_read
from tests.test_operations import ops, zone_data


def test_all_registered_business_routes_have_explicit_permissions():
    public = {"/api/v1/health", "/health"}
    for route in app.routes:
        if isinstance(route, APIRoute) and not route.path.startswith("/api/v1/auth/") and route.path not in public:
            for method in route.methods:
                assert (method, route.path) in ROUTE_PERMISSIONS, (method, route.path)
            assert any(d.call.__name__ == "enforce_route_permission" for d in route.dependant.dependencies)


def test_permission_matrix_and_camera_secret_redaction(client, ops):
    h = ops["headers"]
    for role in ("staff", "manager"):
        assert client.put(f"/api/v1/cameras/{ops['camera']}", headers=h[role], json={"fps": 3}).status_code == 403
        assert client.post("/api/v1/zones", headers=h[role], json=zone_data(ops)).status_code == 403
        assert client.put(f"/api/v1/products/{ops['product']}", headers=h[role], json={"low_stock_threshold": 4}).status_code == 403
        assert client.get("/api/v1/agents/runs/unknown/trace", headers=h[role]).status_code == 403
        assert client.post("/api/v1/inventory/reconcile", headers=h[role], json={}).status_code == 403
    assert client.get("/api/v1/reports/export", headers=h["staff"]).status_code == 403
    assert client.get("/api/v1/reports/export", headers=h["manager"]).status_code == 200
    assert client.put(f"/api/v1/products/{ops['product']}", headers=h["manager"], json={"name": "New name"}).status_code == 200
    assert client.post("/api/v1/products", headers=h["manager"], json={"sku":uuid4().hex, "name":"New product"}).status_code == 201
    assert client.post("/api/v1/products", headers=h["manager"], json={"sku":uuid4().hex, "name":"New product", "reorder_point":2}).status_code == 403
    with SessionLocal() as db:
        db.get(Camera, ops["camera"]).source_url = "rtsp://secret:password@camera/live?token=hidden"
        db.commit()
    for role in ("admin", "manager", "staff"):
        response = client.get(f"/api/v1/cameras/{ops['camera']}", headers=h[role])
        assert response.status_code == 200
        assert response.json()["source_url"] is None
        assert "password" not in response.text and "hidden" not in response.text


def submit(client, ops, kind="physical_count", quantity=2):
    payload = {"inventory_id":ops["inventory"], "kind":kind, "reason":"Observed during shelf check"}
    if kind == "physical_count":
        payload["quantity"] = quantity
    r = client.post("/api/v1/requests", headers=ops["headers"]["staff"], json=payload)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_count_approval_atomicity_and_replay(client, ops):
    request_id = submit(client, ops)
    with SessionLocal() as db:
        assert db.get(Inventory, ops["inventory"]).quantity_estimate == 5
    url = f"/api/v1/requests/{request_id}/review"
    payload = {"decision":"approved", "reason":"Verified by manager"}
    assert client.post(url, headers=ops["headers"]["staff"], json=payload).status_code == 403
    assert client.post(url, headers=ops["headers"]["manager"], json=payload).status_code == 200
    assert client.post(url, headers=ops["headers"]["manager"], json=payload).status_code == 409
    with SessionLocal() as db:
        assert db.get(Inventory, ops["inventory"]).quantity_estimate == 2
        assert db.query(AuditLog).filter_by(resource_id=request_id, action="review").count() == 1


def test_stale_count_does_not_overwrite_inventory(client, ops):
    request_id = submit(client, ops)
    r = client.post(f"/api/v1/inventory/{ops['inventory']}/corrections", headers=ops["headers"]["manager"],
        json={"quantity":9, "reason":"More recent physical count", "expected_updated_at":ops["updated_at"]})
    assert r.status_code == 200, r.text
    r = client.post(f"/api/v1/requests/{request_id}/review", headers=ops["headers"]["manager"],
        json={"decision":"approved", "reason":"Review old count"})
    assert r.status_code == 409
    with SessionLocal() as db:
        assert db.get(OperationalRequest, request_id).status == "pending"
        assert db.get(Inventory, ops["inventory"]).quantity_estimate == 9


@pytest.mark.parametrize("kind", ["restock", "discrepancy"])
def test_non_count_requests_never_change_stock_and_are_private(client, ops, kind):
    request_id = submit(client, ops, kind)
    with SessionLocal() as db:
        other = User(username=uuid4().hex, email=f"{uuid4().hex}@test.local", role="staff", hashed_password="unused")
        db.add(other); db.commit()
        headers={"Authorization":"Bearer " + create_access_token(other.id, other.username, "staff", other.email)}
    assert client.get(f"/api/v1/requests/{request_id}", headers=headers).status_code == 404
    assert client.get("/api/v1/requests", headers=headers).json() == []
    assert client.get("/api/v1/operational-audit", headers=headers).json() == []
    r = client.post(f"/api/v1/requests/{request_id}/review", headers=ops["headers"]["manager"],
        json={"decision":"approved", "reason":"Reviewed operational request"})
    assert r.status_code == 200
    with SessionLocal() as db:
        assert db.get(Inventory, ops["inventory"]).quantity_estimate == 5


def test_logout_and_role_change_revoke_tokens(client, ops):
    h = ops["headers"]
    verify = client.get("/api/v1/auth/verify", headers=h["staff"]).json()
    assert "requests.submit" in verify["permissions"] and "users.create" not in verify["permissions"]
    assert client.post("/api/v1/auth/logout", headers=h["staff"]).status_code == 200
    assert client.get("/api/v1/products", headers=h["staff"]).status_code == 401
    r = client.put(f"/api/v1/users/{ops['users']['manager']}", headers=h["admin"], json={"role":"staff","is_active":True})
    assert r.status_code == 200
    assert client.get("/api/v1/products", headers=h["manager"]).status_code == 401
    with SessionLocal() as db:
        email = db.get(User, ops["users"]["manager"]).email
    fresh = client.post("/api/v1/auth/login", json={"email":email, "password":"operations-password"})
    assert fresh.status_code == 200
    new_headers = {"Authorization": "Bearer " + fresh.json()["access_token"]}
    assert client.get("/api/v1/products", headers=new_headers).status_code == 200
    assert client.get("/api/v1/reports/export", headers=new_headers).status_code == 403


def test_submissions_validate_and_cannot_supply_actor_or_status(client, ops):
    payload = {"inventory_id":ops["inventory"], "kind":"physical_count", "reason":"Physical shelf check", "quantity":2}
    for patch in ({"quantity":-1}, {"quantity":None}, {"quantity":True}, {"reason":" "},
                  {"submitter_id":ops["users"]["admin"]}, {"status":"approved"}):
        assert client.post("/api/v1/requests", headers=ops["headers"]["staff"], json={**payload, **patch}).status_code == 422
    assert client.post("/api/v1/requests", json=payload).status_code == 401
    request_id = submit(client, ops)
    r = client.post(f"/api/v1/requests/{request_id}/review", headers=ops["headers"]["manager"],
        json={"decision":"rejected", "reason":"Needs a new physical count"})
    assert r.status_code == 200
    with SessionLocal() as db:
        assert db.get(Inventory, ops["inventory"]).quantity_estimate == 5


def test_chat_tools_fail_closed_without_user_and_for_missing_permission(ops, monkeypatch):
    plan={"intent":"inventory", "product_query":"", "stock_filter":"all", "days":7, "use_previous_product":False}
    with SessionLocal() as db:
        with pytest.raises(HTTPException) as error:
            execute_read(db, plan)
        assert error.value.status_code == 403
        user = db.get(User, ops["users"]["staff"])
        assert execute_read(db, plan, user=user)["sources"]
        monkeypatch.setitem(__import__('app.core.permissions',fromlist=['ROLE_PERMISSIONS']).ROLE_PERMISSIONS,
                            "staff", frozenset({"chatbot.use"}))
        with pytest.raises(HTTPException):
            execute_read(db, plan, user=user)
        with pytest.raises(HTTPException):
            authorize(user, "unknown.new.permission")
