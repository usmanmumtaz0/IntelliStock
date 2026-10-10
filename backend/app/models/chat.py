"""Owner-private durable chat memory; no shared model checkpoint state."""
from sqlalchemy import Column, String, Integer, Text, JSON, ForeignKey, UniqueConstraint
from app.models.base import BaseModel


class ChatConversation(BaseModel):
    __tablename__ = "chat_conversations"
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(100), nullable=False, default="Inventory conversation")
    turn_count = Column(Integer, nullable=False, default=0)


class ChatTurn(BaseModel):
    __tablename__ = "chat_turns"
    __table_args__ = (
        UniqueConstraint("conversation_id", "request_id", name="uq_chat_request"),
        UniqueConstraint("conversation_id", "sequence", name="uq_chat_sequence"),
    )
    conversation_id = Column(String(36), ForeignKey("chat_conversations.id"), nullable=False, index=True)
    request_id = Column(String(36), nullable=False)
    sequence = Column(Integer, nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    sources = Column(JSON, nullable=False)
    plan = Column(JSON, nullable=False)
    mode = Column(String(32), nullable=False)
    notice = Column(String(255), nullable=True)
