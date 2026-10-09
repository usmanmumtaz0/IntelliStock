"""User persistence operations used by authentication and provisioning."""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: str) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, normalized_email: str) -> User | None:
        return self.db.query(User).filter(func.lower(User.email) == normalized_email).first()

    def get_by_username(self, username: str) -> User | None:
        return self.db.query(User).filter(func.lower(User.username) == username.strip().lower()).first()

    def add(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
