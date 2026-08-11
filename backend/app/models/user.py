"""
User model for authentication and authorization.
"""
from sqlalchemy import Column, String, Boolean, Enum as SQLEnum
from app.models.base import BaseModel
from enum import Enum as PyEnum


class UserRole(str, PyEnum):
    """User roles for RBAC."""

    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class User(BaseModel):
    """User model for system authentication."""

    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"
