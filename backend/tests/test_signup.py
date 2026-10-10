"""Signup and admin approval use isolated test accounts; no external services."""
from uuid import uuid4
import json

import pytest

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.audit_log import AuditLog
from app.core.security import create_access_token, verify_password


def signup_payload():
    name = uuid4().hex
    return {"email": f"{name}@example.com", "username": name, "password": "test-password-long-enough"}


@pytest.fixture
def approval_accounts():
    headers = {}
    with SessionLocal() as db:
        for role in UserRole:
            unique = uuid4().hex
            user = User(email=f"{unique}@example.com", username=unique, role=role,
                        hashed_password="unused", is_active=True)
            db.add(user)
            db.flush()
            headers[role.value] = {"Authorization": "Bearer " + create_access_token(user.id, user.username, role.value, user.email)}
        db.commit()
    return headers


def test_signup_requires_approval_and_stores_hash_only(client, approval_accounts):
    payload = signup_payload()
    response = client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 202, response.text
    assert "access_token" not in response.text and payload["password"] not in response.text
    with SessionLocal() as db:
        account = db.query(User).filter_by(email=payload["email"]).one()
        account_id = account.id
        assert account.signup_pending and not account.is_active and account.role == UserRole.STAFF
        assert account.hashed_password.startswith("$argon2id$")
        assert verify_password(payload["password"], account.hashed_password)
        token = create_access_token(account.id, account.username, "staff", account.email)
    login = {"email": payload["email"], "password": payload["password"]}
    assert client.post("/api/v1/auth/login", json=login).status_code == 401
    assert client.get("/api/v1/auth/verify", headers={"Authorization": "Bearer " + token}).status_code == 401
    for role in ("manager", "staff"):
        assert client.post(f"/api/v1/users/{account_id}/approve", headers=approval_accounts[role]).status_code == 403
    assert client.post(f"/api/v1/users/{account_id}/approve").status_code == 401
    assert client.put(f"/api/v1/users/{account_id}", headers=approval_accounts["admin"],
                      json={"role": "admin", "is_active": True}).status_code == 409
    approved = client.post(f"/api/v1/users/{account_id}/approve", headers=approval_accounts["admin"])
    assert approved.status_code == 200, approved.text
    assert approved.json()["role"] == "staff"
    assert approved.json()["is_active"] and not approved.json()["signup_pending"]
    assert "hashed_password" not in approved.text
    assert client.post(f"/api/v1/users/{account_id}/approve", headers=approval_accounts["admin"]).status_code == 409
    signed_in = client.post("/api/v1/auth/login", json=login)
    assert signed_in.status_code == 200 and signed_in.json()["role"] == "staff"
    with SessionLocal() as db:
        log = db.query(AuditLog).filter_by(resource_id=account_id, action="approve_signup").one()
        assert payload["password"] not in json.dumps(log.new_values)


@pytest.mark.parametrize("extra", [{"role": "admin"}, {"role": "manager"}, {"is_active": True}, {"signup_pending": False}])
def test_public_signup_rejects_privilege_fields(client, extra):
    payload = {**signup_payload(), **extra}
    response = client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 422
    assert payload["password"] not in response.text
    with SessionLocal() as db:
        assert not db.query(User).filter_by(email=payload["email"]).first()


@pytest.mark.parametrize("password", ["short-test", "x" * 129])
def test_password_validation_does_not_echo_password(client, password):
    payload = {**signup_payload(), "password": password}
    response = client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 422
    assert password not in response.text


def test_duplicate_signup_does_not_reset_account(client):
    payload = signup_payload()
    first = client.post("/api/v1/auth/signup", json=payload)
    with SessionLocal() as db:
        row = db.query(User).filter_by(email=payload["email"]).one()
        initial_hash = row.hashed_password
    second = client.post("/api/v1/auth/signup", json={**payload, "email": payload["email"].upper(),
                                                   "password": "different-test-password"})
    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()
    with SessionLocal() as db:
        row = db.query(User).filter_by(email=payload["email"]).one()
        assert row.hashed_password == initial_hash and row.signup_pending and not row.is_active


def test_signup_has_separate_ip_rate_limit(client):
    payload = signup_payload()
    for _ in range(5):
        assert client.post("/api/v1/auth/signup", json=payload).status_code == 202
    limited = client.post("/api/v1/auth/signup", json=signup_payload())
    assert limited.status_code == 429 and "retry-after" in limited.headers


def test_pending_flag_blocks_even_accidentally_active_account(client):
    payload = signup_payload()
    assert client.post("/api/v1/auth/signup", json=payload).status_code == 202
    with SessionLocal() as db:
        row = db.query(User).filter_by(email=payload["email"]).one()
        row.is_active = True
        token = create_access_token(row.id, row.username, "staff", row.email)
        db.commit()
    assert client.post("/api/v1/auth/login", json={"email": payload["email"], "password": payload["password"]}).status_code == 401
    assert client.get("/api/v1/auth/verify", headers={"Authorization": "Bearer " + token}).status_code == 401
