"""Isolated test configuration; production credentials and data are never used."""
from __future__ import annotations

import os
import tempfile
import gc
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_DATABASE_PATH = Path(tempfile.gettempdir()) / f"intellistock-tests-{os.getpid()}.sqlite3"
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_PATH.as_posix()}"
os.environ["JWT_SECRET"] = "test-only-secret-that-is-longer-than-thirty-two-characters"
os.environ["REDIS_URL"] = "redis://127.0.0.1:1/15"
os.environ["REDIS_SOCKET_TIMEOUT_SECONDS"] = "0.05"

from app.core.rate_limiter import rate_limiter, shared_rate_limiter  # noqa: E402
from app.database import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.core.security import create_access_token, hash_password  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def isolated_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    gc.collect()
    try:
        TEST_DATABASE_PATH.unlink(missing_ok=True)
    except PermissionError:
        # A few legacy tests retain Session objects until process exit on Windows.
        pass


@pytest.fixture(autouse=True)
def reset_rate_limits():
    rate_limiter.reset()
    shared_rate_limiter.fallback.reset()
    yield
    rate_limiter.reset()
    shared_rate_limiter.fallback.reset()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    email = f"api-reader-{os.urandom(6).hex()}@test.local"
    with SessionLocal() as db:
        user = User(
            email=email,
            username=f"reader-{os.urandom(6).hex()}",
            hashed_password=hash_password("test-reader-password"),
            role=UserRole.STAFF,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_access_token(
            user_id=user.id,
            username=user.username,
            email=user.email,
            role=user.role.value,
        )
        user_id = user.id
    yield {"Authorization": f"Bearer {token}"}
    with SessionLocal() as db:
        db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
        db.commit()
