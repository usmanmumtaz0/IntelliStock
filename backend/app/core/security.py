"""
Security module — JWT authentication, RBAC, and token management.
"""
import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from pydantic import BaseModel

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


class TokenData(BaseModel):
    """JWT token payload."""
    user_id: str
    username: str
    role: str  # admin, manager, staff


class User(BaseModel):
    """User model for authentication."""
    user_id: str
    username: str
    role: str  # admin, manager, staff
    is_active: bool = True


def hash_password(password: str) -> str:
    """
    Hash a password using SHA256.
    Note: Use bcrypt in production. This is for development/testing.
    """
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


def create_access_token(
    user_id: str,
    username: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: User ID
        username: Username
        role: User role (admin, manager, staff)
        expires_delta: Token expiration time delta
    
    Returns:
        JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    expire = datetime.utcnow() + expires_delta
    to_encode = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """
    Decode and verify a JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        TokenData if valid, None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        role: str = payload.get("role")
        
        if user_id is None or username is None or role is None:
            return None
        
        return TokenData(user_id=user_id, username=username, role=role)
    except JWTError:
        return None


# Mock user database (replace with real database in production)
MOCK_USERS = None


def _init_mock_users():
    """Initialize mock users (lazy-loaded to avoid bcrypt issues on import)."""
    global MOCK_USERS
    if MOCK_USERS is not None:
        return MOCK_USERS
    
    MOCK_USERS = {
        "admin": {
            "username": "admin",
            "hashed_password": hash_password("admin123"),
            "role": "admin",
            "user_id": "user-001",
            "is_active": True,
        },
        "manager": {
            "username": "manager",
            "hashed_password": hash_password("manager123"),
            "role": "manager",
            "user_id": "user-002",
            "is_active": True,
        },
        "staff": {
            "username": "staff",
            "hashed_password": hash_password("staff123"),
            "role": "staff",
            "user_id": "user-003",
            "is_active": True,
        },
    }
    return MOCK_USERS


def authenticate_user(username: str, password: str) -> Optional[User]:
    """
    Authenticate a user by username and password.
    
    Args:
        username: Username
        password: Password
    
    Returns:
        User if authenticated, None otherwise
    """
    users = _init_mock_users()
    user_data = users.get(username)
    if not user_data:
        return None
    
    if not verify_password(password, user_data["hashed_password"]):
        return None
    
    if not user_data["is_active"]:
        return None
    
    return User(
        user_id=user_data["user_id"],
        username=user_data["username"],
        role=user_data["role"],
        is_active=user_data["is_active"],
    )


# Role-based access control
ROLE_PERMISSIONS = {
    "admin": ["read", "write", "delete", "admin"],
    "manager": ["read", "write"],
    "staff": ["read"],
}


def has_permission(role: str, permission: str) -> bool:
    """
    Check if a role has a specific permission.
    
    Args:
        role: User role
        permission: Permission to check
    
    Returns:
        True if role has permission, False otherwise
    """
    return permission in ROLE_PERMISSIONS.get(role, [])
