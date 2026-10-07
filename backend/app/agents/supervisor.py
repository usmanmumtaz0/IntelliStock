"""
LangGraph Supervisor Agent — Routes tasks to specialized agents.
Handles decision-making about which agent should handle each situation.
"""
import logging
from enum import Enum
from typing import TypedDict, Optional

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """Available agent types."""
    INSIGHT = "insight"
    ANOMALY = "anomaly"
    NOTIFICATION = "notification"


class SupervisorState(TypedDict):
    """State passed through the supervisor graph."""
    trigger_event: str  # e.g., "low_stock_detected", "anomaly_found"
    trigger_data: dict  # Metadata about the trigger
    selected_agent: Optional[AgentType]
    reasoning: str
    final_action: Optional[str]


class SupervisorAgent:
    """
    Routes incoming events to specialized agents.
    Placeholder for Phase 7 LangGraph implementation.
    """
    
    def __init__(self):
        """Initialize the supervisor agent."""
        self.agents = {
            AgentType.INSIGHT: "Analyzes trends and generates insights",
            AgentType.ANOMALY: "Detects anomalies and flags unusual patterns",
            AgentType.NOTIFICATION: "Sends alerts and notifications",
        }
    
    def route(self, event_type: str, event_data: dict) -> dict:
        """
        Route an event to the appropriate agent.
        
        Args:
            event_type: Type of event (e.g., "low_stock", "camera_offline")
            event_data: Event metadata
        
        Returns:
            dict with selected agent and reasoning
        """
        logger.info(f"Supervisor routing event: {event_type}")
        
        # Simple routing rules (to be replaced with LangGraph in Phase 7)
        if event_type == "low_stock_detected":
            agent = AgentType.INSIGHT
            reasoning = "Low stock requires trend analysis and recommendations"
        elif event_type == "anomaly_detected":
            agent = AgentType.ANOMALY
            reasoning = "Anomaly requires investigation and pattern detection"
        elif event_type in ["camera_offline", "critical_alert"]:
            agent = AgentType.NOTIFICATION
            reasoning = "Critical event requires immediate notification"
        else:
            agent = AgentType.INSIGHT
            reasoning = "Default routing to insight agent"
        
        return {
            "selected_agent": agent,
            "reasoning": reasoning,
            "event_type": event_type,
            "event_data": event_data,
        }
    
    def should_route(self, event_type: str) -> bool:
        """Check if an event should be routed to an agent."""
        # Route only significant business events
        routable_events = {
            "low_stock_detected",
            "out_of_stock_detected",
            "anomaly_detected",
            "camera_offline",
            "reconciliation_confidence_low",
        }
        return event_type in routable_events
