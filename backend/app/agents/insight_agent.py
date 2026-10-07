"""
Insight Agent — Analyzes inventory trends and provides recommendations.
Read-only access to database for analysis.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class InsightAgent:
    """
    Analyzes inventory trends and generates insights.
    Uses deterministic rules + optional LLM for explanation.
    """
    
    def analyze(self, zone_id: str, product_id: str, context: dict) -> dict:
        """
        Analyze product trends in a zone.
        
        Args:
            zone_id: The zone to analyze
            product_id: The product to analyze
            context: Additional context (inventory history, threshold, etc.)
        
        Returns:
            dict with insight, recommendation, confidence
        """
        logger.info(f"Insight Agent analyzing {product_id} in {zone_id}")
        
        # Deterministic analysis (non-LLM, no hallucination risk)
        quantity = context.get("quantity_estimate", 0)
        threshold = context.get("threshold", 0)
        history = context.get("history", [])
        
        # Rule-based analysis
        if quantity == 0:
            insight = "Product is completely out of stock"
            recommendation = "Immediate restock required"
            urgency = "critical"
        elif quantity < threshold / 2:
            insight = "Product quantity below 50% of threshold"
            recommendation = f"Restock to reach threshold of {threshold}"
            urgency = "high"
        elif quantity < threshold:
            insight = "Product approaching threshold"
            recommendation = f"Plan restock soon (current: {quantity}, threshold: {threshold})"
            urgency = "medium"
        else:
            trend = self._analyze_trend(history)
            if trend == "declining":
                insight = f"Product showing declining trend (currently {quantity})"
                recommendation = "Monitor closely; prepare restock if trend continues"
                urgency = "low"
            else:
                insight = f"Product stock is adequate (currently {quantity})"
                recommendation = "No immediate action needed"
                urgency = "info"
        
        return {
            "agent": "insight",
            "insight": insight,
            "recommendation": recommendation,
            "urgency": urgency,
            "confidence": 0.95,  # Deterministic rules = high confidence
        }
    
    def _analyze_trend(self, history: list) -> str:
        """
        Analyze a quantity history to determine trend.
        
        Args:
            history: List of quantities over time (most recent first)
        
        Returns:
            "increasing", "declining", or "stable"
        """
        if len(history) < 2:
            return "stable"
        
        recent = history[:min(3, len(history))]
        decreases = sum(1 for i in range(len(recent) - 1) if recent[i] < recent[i + 1])
        increases = sum(1 for i in range(len(recent) - 1) if recent[i] > recent[i + 1])
        
        if decreases > increases:
            return "declining"
        elif increases > decreases:
            return "increasing"
        else:
            return "stable"
