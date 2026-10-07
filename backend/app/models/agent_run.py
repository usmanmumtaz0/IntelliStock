"""
Agent run model for tracking AI agent execution history (for FYP evaluation).
"""
from sqlalchemy import Column, String, Integer, Float, Text, Enum as SQLEnum, JSON
from app.models.base import BaseModel
from enum import Enum as PyEnum
from datetime import datetime


class AgentRunStatus(str, PyEnum):
    """Status of an agent run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentRun(BaseModel):
    """Log of LangGraph agent executions."""

    __tablename__ = "agent_runs"

    agent_type = Column(String(64), nullable=False, index=True)  # "supervisor", "insight", "anomaly", "notification"
    status = Column(SQLEnum(AgentRunStatus), default=AgentRunStatus.PENDING, nullable=False, index=True)
    
    # Trigger context
    trigger_event = Column(String(255), nullable=True)  # e.g., "low_stock_alert"
    trigger_data = Column(JSON, nullable=True)  # Metadata about what triggered the agent
    
    # Agent execution
    input_prompt = Column(Text, nullable=True)
    reasoning = Column(Text, nullable=True)
    output_action = Column(String(255), nullable=True)  # What the agent decided to do
    output_data = Column(JSON, nullable=True)  # Structured output
    
    # Metadata
    confidence_score = Column(Float, nullable=True)  # 0.0-1.0
    tokens_used = Column(Integer, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Traceability
    llm_model = Column(String(64), nullable=True)  # e.g., "gpt-4", "claude-3"
    llm_provider = Column(String(64), nullable=True)  # e.g., "openai", "anthropic"

    def __repr__(self):
        return f"<AgentRun {self.agent_type}/{self.status}>"
