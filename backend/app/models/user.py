"""
User model for authentication and authorization.
"""
from sqlalchemy import Boolean, Column, Enum as SQLEnum, Index, String, UniqueConstraint, func
from enum import Enum as PyEnum

from app.models.base import BaseModel


class UserRole(str, PyEnum):
    """User roles for RBAC."""

    ADMIN = "admin"
    MANAGER = "manager"
    STAFF = "staff"


class User(BaseModel):
    """User model for system authentication."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("username", name="uq_users_username"),
    )

    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.STAFF, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"


Index("uq_users_email_normalized", func.lower(User.email), unique=True)
