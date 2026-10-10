"""Authentication, authorization, rate-limit, and secret-regression tests."""
from __future__ import annotations

import logging
import time
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from starlette.websockets import WebSocketDisconnect

from app.core.rate_limiter import RateLimiter, shared_rate_limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.database import SessionLocal
from app.models.user import User, UserRole

PASSWORD = "A-secure-test-password-42!"


@pytest.fixture
def users():
    emails = ["admin@test.local", "manager@test.local", "staff@test.local", "inactive@test.local"]
    with SessionLocal() as db:
        db.query(User).filter(User.email.in_(emails)).delete(synchronize_session=False)
        records = {
            "admin": User(
                email=emails[0], username="test-admin", hashed_password=hash_password(PASSWORD), role=UserRole.ADMIN
            ),
            "manager": User(
                email=emails[1], username="test-manager", hashed_password=hash_password(PASSWORD), role=UserRole.MANAGER
            ),
            "staff": User(
                email=emails[2], username="test-staff", hashed_password=hash_password(PASSWORD), role=UserRole.STAFF
            ),
            "inactive": User(
                email=emails[3],
                username="test-inactive",
                hashed_password=hash_password(PASSWORD),
                role=UserRole.STAFF,
                is_active=False,
            ),
        }
        db.add_all(records.values())
        db.commit()
        for record in records.values():
            db.refresh(record)
        snapshot = {
            key: {"id": value.id, "email": value.email, "username": value.username, "role": value.role.value}
            for key, value in records.items()
        }
    yield snapshot
    with SessionLocal() as db:
        db.query(User).filter(User.email.in_(emails)).delete(synchronize_session=False)
        db.commit()


def _token(user: dict, *, expires: timedelta | None = None) -> str:
    return create_access_token(
        user_id=user["id"],
        username=user["username"],
        email=user["email"],
        role=user["role"],
        expires_delta=expires,
    )


def _headers(user: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(user)}"}


def test_passwords_use_argon2id():
    password_hash = hash_password(PASSWORD)
    assert password_hash.startswith("$argon2id$")
    assert password_hash != PASSWORD
    assert verify_password(PASSWORD, password_hash)
    assert not verify_password("incorrect", password_hash)


def test_login_with_valid_email(client: TestClient, users):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": users["admin"]["email"].upper(), "password": PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["email"] == users["admin"]["email"]
    assert body["role"] == "admin"
    assert "hashed_password" not in body


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("admin@test.local", "wrong-password"),
        ("unknown@test.local", PASSWORD),
        ("inactive@test.local", PASSWORD),
    ],
)
def test_login_failures_are_generic(client: TestClient, users, email: str, password: str):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}


def test_invalid_login_payload_returns_422(client: TestClient):
    assert client.post("/api/v1/auth/login", json={"email": "not-an-email", "password": "x"}).status_code == 422
    assert client.post("/api/v1/auth/login", json={"username": "admin", "password": "x"}).status_code == 422


def test_missing_and_invalid_tokens_are_rejected(client: TestClient):
    assert client.get("/api/v1/dashboard/metrics").status_code == 401
    assert client.get(
        "/api/v1/dashboard/metrics", headers={"Authorization": "Bearer invalid.token.value"}
    ).status_code == 401


def test_expired_and_tampered_tokens_are_rejected(client: TestClient, users):
    expired = _token(users["admin"], expires=timedelta(seconds=-1))
    valid = _token(users["admin"])
    header, payload, signature = valid.split(".")
    # Mutate significant signature bits, not optional base64 padding bits.
    # Changing only the final character can decode to the original signature.
    tampered_signature = ("A" if signature[0] != "A" else "B") + signature[1:]
    tampered = f"{header}.{payload}.{tampered_signature}"
    assert client.get(
        "/api/v1/dashboard/metrics", headers={"Authorization": f"Bearer {expired}"}
    ).status_code == 401
    assert client.get(
        "/api/v1/dashboard/metrics", headers={"Authorization": f"Bearer {tampered}"}
    ).status_code == 401


def test_valid_token_access_and_inactive_user_recheck(client: TestClient, users):
    headers = _headers(users["staff"])
    assert client.get("/api/v1/dashboard/metrics", headers=headers).status_code == 200
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == users["staff"]["id"]).one()
        user.is_active = False
        db.commit()
    assert client.get("/api/v1/dashboard/metrics", headers=headers).status_code == 401


def test_role_based_authorization(client: TestClient, users):
    payload = {"sku": "AUTHZ-001", "name": "Authorization Test Product", "low_stock_threshold": 2, "reorder_point": 5}
    assert client.post("/api/v1/products", json=payload, headers=_headers(users["staff"])).status_code == 403
    created = client.post("/api/v1/products", json=payload, headers=_headers(users["manager"]))
    assert created.status_code == 201
    product_id = created.json()["id"]
    assert client.delete(f"/api/v1/products/{product_id}", headers=_headers(users["manager"])).status_code == 403
    assert client.delete(f"/api/v1/products/{product_id}", headers=_headers(users["admin"])).status_code == 204


def test_login_rate_limit_on_prefixed_route(client: TestClient, users):
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": users["admin"]["email"], "password": "incorrect"},
        )
        assert response.status_code == 401
    blocked = client.post(
        "/api/v1/auth/login",
        json={"email": users["admin"]["email"], "password": "incorrect"},
    )
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1
    assert blocked.json() == {"detail": "Too many login attempts. Please try again later."}

    shared_rate_limiter.fallback.reset()
    reset = client.post(
        "/api/v1/auth/login",
        json={"email": users["admin"]["email"], "password": PASSWORD},
    )
    assert reset.status_code == 200


def test_in_memory_rate_limit_expires_old_entries():
    limiter = RateLimiter()
    assert limiter.is_allowed("client", limit=1, window_seconds=1)
    assert not limiter.is_allowed("client", limit=1, window_seconds=1)
    limiter.requests["client"] = [time.monotonic() - 2]
    assert limiter.is_allowed("client", limit=1, window_seconds=1)


def test_websocket_requires_active_authentication(client: TestClient, users):
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/inventory"):
            pass
    assert exc.value.code == 4401

    with client.websocket_connect(f"/ws/inventory?token={_token(users['staff'])}") as websocket:
        websocket.send_text("ping")
        assert websocket.receive_text() == "pong"


def test_health_checks_remain_public(client: TestClient):
    assert client.get("/health").status_code == 200
    assert client.get("/api/v1/health").status_code == 200


def test_login_does_not_leak_secrets_to_response_or_logs(client: TestClient, users, caplog):
    caplog.set_level(logging.INFO)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": users["admin"]["email"], "password": PASSWORD},
    )
    rendered = response.text + caplog.text
    assert PASSWORD not in rendered
    assert "hashed_password" not in rendered


def test_normalized_email_is_unique(users):
    with SessionLocal() as db:
        db.add(
            User(
                email=users["admin"]["email"].upper(),
                username="case-duplicate",
                hashed_password=hash_password(PASSWORD),
                role=UserRole.STAFF,
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
