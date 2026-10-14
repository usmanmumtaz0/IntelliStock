"""Cross-feature HTTP acceptance on isolated fixtures; no real emails or providers."""
import pytest
from app.database import SessionLocal
from app.models import User
from app.core.permissions import permissions_for
from tests.test_operations import ops


@pytest.mark.parametrize("role", ["admin", "manager", "staff"])
def test_login_permissions_and_business_reads(client, ops, role):
    with SessionLocal() as db:
        user = db.get(User, ops["users"][role])
        email, expected = user.email, sorted(permissions_for(user))
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "operations-password"})
    assert login.status_code == 200
    assert sorted(login.json()["permissions"]) == expected
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    for path in ("auth/verify", "inventory", "products", "alerts", "cameras", "zones",
                 "reports/summary", "requests", "operational-audit", "chat/conversations"):
        response = client.get("/api/v1/" + path, headers=headers)
        assert response.status_code == 200, (role, path, response.text)
    for path in ("users", "notifications/configuration", "notifications/deliveries"):
        assert client.get("/api/v1/" + path, headers=headers).status_code == (200 if role == "admin" else 403)
    assert client.get("/api/v1/reports/export", headers=headers).status_code == (403 if role == "staff" else 200)


@pytest.mark.parametrize("role", ["admin", "manager", "staff"])
def test_deactivated_sessions_cannot_read_or_mutate_any_workflow(client, ops, role):
    headers = ops["headers"][role]
    with SessionLocal() as db:
        db.get(User, ops["users"][role]).is_active = False
        db.commit()
    for path in ("auth/verify", "inventory", "alerts", "users", "reports/export", "chat/conversations", "requests"):
        assert client.get("/api/v1/" + path, headers=headers).status_code == 401, path
    for path in ("requests", "chat/conversations", "inventory/reconcile", "users"):
        assert client.post("/api/v1/" + path, headers=headers, json={}).status_code == 401, path


def test_staff_cannot_promote_self_or_invoke_management_with_forged_headers(client, ops):
    headers = {**ops["headers"]["staff"], "X-Role": "admin", "X-User-Id": ops["users"]["admin"]}
    response = client.put(f"/api/v1/users/{ops['users']['staff']}", headers=headers,
                          json={"role": "admin", "is_active": True})
    assert response.status_code == 403
    for path in (f"alerts/{'missing'}/resolve", "alerts/acknowledge-all", "users", "cameras", "zones"):
        assert client.post("/api/v1/" + path, headers=headers, json={}).status_code == 403
    with SessionLocal() as db:
        assert db.get(User, ops["users"]["staff"]).role.value == "staff"
