"""
Authentication endpoints — user login/logout and token management.
"""
import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.security import (
    authenticate_user,
    create_access_token,
    get_current_user,
    normalize_email,
)
from app.core.rate_limiter import enforce_login_rate_limit
from app.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Email-based login request used by the frontend."""

    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=1024)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = normalize_email(value)
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized):
            raise ValueError("Enter a valid email address")
        return normalized


class LoginResponse(BaseModel):
    """Login response schema."""

    access_token: str
    token_type: str
    user_id: str
    username: str
    email: str
    role: str


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticate a user and return a JWT."""
    enforce_login_rate_limit(request, payload.email)

    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        logger.warning("Failed login attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(
        user_id=user.id,
        username=user.username,
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
    )

    logger.info("Successful login for user_id=%s", user.id)
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Invalidate a token by validating it and returning success."""
    logger.info("Logout for user: %s", current_user.username)
    return {"message": "Successfully logged out", "user_id": current_user.id}


@router.post("/refresh")
async def refresh_token(current_user: User = Depends(get_current_user)):
    """Rotate the access token for the current user."""
    new_access_token = create_access_token(
        user_id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
    )
    logger.info("Token refreshed for user: %s", current_user.username)
    return LoginResponse(
        access_token=new_access_token,
        token_type="bearer",
        user_id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
    )


@router.get("/verify")
async def verify_token(current_user: User = Depends(get_current_user)):
    """Verify that the caller possesses a valid JWT."""
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        "valid": True,
    }
