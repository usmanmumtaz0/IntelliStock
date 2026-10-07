"""
Authentication endpoints — user login/logout and token management.
"""
import logging
from fastapi import APIRouter, HTTPException, status, Header
from typing import Optional
from pydantic import BaseModel

from app.core.security import (
    authenticate_user,
    create_access_token,
    decode_access_token,
    TokenData,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Login request schema."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response schema."""
    access_token: str
    token_type: str
    user_id: str
    username: str
    role: str


class LogoutRequest(BaseModel):
    """Logout request schema."""
    pass


class TokenRefreshRequest(BaseModel):
    """Token refresh request schema."""
    pass


def extract_token_from_header(authorization: Optional[str] = Header(None)) -> str:
    """Extract JWT token from Authorization header."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
        )
    
    return authorization[7:]


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return JWT token.
    
    Args:
        request: Login credentials (username, password)
    
    Returns:
        LoginResponse with access token
    
    Raises:
        HTTPException: 401 if credentials invalid
    """
    logger.info(f"Login attempt for user: {request.username}")
    
    # Authenticate user
    user = authenticate_user(request.username, request.password)
    if not user:
        logger.warning(f"Failed login attempt for user: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    
    # Create access token
    access_token = create_access_token(
        user_id=user.user_id,
        username=user.username,
        role=user.role,
    )
    
    logger.info(f"Successful login for user: {user.username} (role: {user.role})")
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.user_id,
        username=user.username,
        role=user.role,
    )


@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """
    Logout user (invalidate token).
    
    Note: In a production system, you would:
    1. Add token to a blacklist
    2. Store blacklist in Redis
    3. Check blacklist in authentication middleware
    
    Args:
        authorization: Authorization header with JWT token
    
    Returns:
        Success message
    """
    token = extract_token_from_header(authorization)
    token_data = decode_access_token(token)
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    
    logger.info(f"Logout for user: {token_data.username}")
    
    # In production, add token to Redis blacklist here
    # redis_client.setex(f"blacklist:{token}", TOKEN_EXPIRY_SECONDS, "true")
    
    return {"message": "Successfully logged out"}


@router.post("/refresh")
async def refresh_token(authorization: Optional[str] = Header(None)):
    """
    Refresh access token.
    
    Args:
        authorization: Current JWT token from Authorization header
    
    Returns:
        LoginResponse with new access token
    
    Raises:
        HTTPException: 401 if token invalid
    """
    token = extract_token_from_header(authorization)
    token_data = decode_access_token(token)
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    
    # Create new access token
    new_access_token = create_access_token(
        user_id=token_data.user_id,
        username=token_data.username,
        role=token_data.role,
    )
    
    logger.info(f"Token refreshed for user: {token_data.username}")
    
    return LoginResponse(
        access_token=new_access_token,
        token_type="bearer",
        user_id=token_data.user_id,
        username=token_data.username,
        role=token_data.role,
    )


@router.get("/verify")
async def verify_token(authorization: Optional[str] = Header(None)):
    """
    Verify and decode JWT token.
    
    Args:
        authorization: JWT token from Authorization header
    
    Returns:
        Token data (user_id, username, role)
    
    Raises:
        HTTPException: 401 if token invalid
    """
    token = extract_token_from_header(authorization)
    token_data = decode_access_token(token)
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    
    return {
        "user_id": token_data.user_id,
        "username": token_data.username,
        "role": token_data.role,
        "valid": True,
    }
