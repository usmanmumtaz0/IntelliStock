"""Password hashing, JWT validation, database-backed authentication, and RBAC."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import SessionLocal, get_db
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository

# New hashes use Argon2id. Bcrypt remains available only to verify existing rows;
# successful legacy logins are transparently upgraded to Argon2id.
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    """Validated claims from an access token."""

    user_id: str
    username: str
    email: str
    role: UserRole
    token_id: str


def normalize_email(value: str) -> str:
    """Normalize an email for case-insensitive storage and lookup."""
    return (value or "").strip().lower()


def hash_password(password: str) -> str:
    """Hash a password with Argon2id."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify an Argon2id or legacy bcrypt password hash."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (TypeError, ValueError):
        return False


def create_access_token(
    user_id: str,
    username: str,
    role: str,
    email: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed, expiring access token for an existing user."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(hours=settings.JWT_EXPIRATION_HOURS))
    claims = {
        "sub": str(user_id),
        "username": username,
        "email": normalize_email(email),
        "role": role,
        "type": "access",
        "jti": str(uuid4()),
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(
        claims,
        settings.JWT_SECRET.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> Optional[TokenData]:
    """Validate signature, expiry, type, required claims, and role syntax."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET.get_secret_value(),
            algorithms=[settings.JWT_ALGORITHM],
        )
        required = ("sub", "username", "email", "role", "jti", "iat", "exp")
        if payload.get("type") != "access" or any(payload.get(key) is None for key in required):
            return None
        return TokenData(
            user_id=str(payload["sub"]),
            username=str(payload["username"]),
            email=normalize_email(str(payload["email"])),
            role=UserRole(str(payload["role"])),
            token_id=str(payload["jti"]),
        )
    except (JWTError, ValueError):
        return None


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate an active user by normalized email with a generic result."""
    if not email or not password:
        return None

    user = UserRepository(db).get_by_email(normalize_email(email))
    if user is None or not verify_password(password, user.hashed_password) or not user.is_active or user.signup_pending:
        return None

    if pwd_context.needs_update(user.hashed_password):
        user.hashed_password = hash_password(password)
        db.commit()
        db.refresh(user)
    return user


def _authentication_error(detail: str = "Invalid or expired token") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_user_for_token(db: Session, token: str) -> Optional[User]:
    """Resolve an access token to the current active database user."""
    token_data = decode_access_token(token)
    if token_data is None:
        return None
    user = UserRepository(db).get_by_id(token_data.user_id)
    if user is None or not user.is_active or user.signup_pending:
        return None
    return user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Return the active database user represented by a bearer token."""
    auth_header = request.headers.get("authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise _authentication_error("Authentication required")

    user = get_user_for_token(db, token.strip())
    if user is None:
        raise _authentication_error()

    request.state.user = user
    return user


def require_roles(*allowed_roles: str | UserRole):
    """Create a dependency that enforces a server-side role allowlist."""
    allowed = {role.value if isinstance(role, UserRole) else str(role) for role in allowed_roles}

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        current_role = current_user.role.value if isinstance(current_user.role, UserRole) else str(current_user.role)
        if current_role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return dependency


ROLE_PERMISSIONS = {
    UserRole.ADMIN.value: {"read", "write", "delete", "admin"},
    UserRole.MANAGER.value: {"read", "write"},
    UserRole.STAFF.value: {"read"},
}


def has_permission(role: str, permission: str) -> bool:
    """Check a role's documented capability."""
    return permission in ROLE_PERMISSIONS.get(role, set())


def validate_websocket_token(token: str) -> bool:
    """Validate a WebSocket token against the current user record."""
    with SessionLocal() as db:
        return get_user_for_token(db, token) is not None
