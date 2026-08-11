"""
Base model with common fields for all entities.
"""
from datetime import datetime
from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import declarative_base
from uuid import uuid4

Base = declarative_base()


class BaseModel(Base):
    """Base class for all models with common audit fields."""

    __abstract__ = True

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
