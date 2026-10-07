"""
Anomaly Detection Agent — Flags unusual patterns and inconsistencies.
Uses statistical analysis and heuristics (no hallucination risk).
"""
import logging
from typing import Optional
from statistics import stdev, mean

logger = logging.getLogger(__name__)


class AnomalyAgent:
    """
    Detects anomalies in inventory patterns using statistical methods.
    Pure deterministic analysis — no LLM dependency.
    """
    
    def detect(self, zone_id: str, product_id: str, context: dict) -> dict:
        """
        Detect anomalies in product data.
        
        Args:
            zone_id: The zone being analyzed
            product_id: The product being analyzed
            context: Data context (quantity, history, confidence, etc.)
        
        Returns:
            dict with anomalies found, severity, recommendations
        """
        logger.info(f"Anomaly Agent analyzing {product_id} in {zone_id}")
        
        anomalies = []
        
        # Check for sudden quantity drops
        drop_anomaly = self._check_sudden_drop(context.get("history", []))
        if drop_anomaly:
            anomalies.append(drop_anomaly)
        
        # Check for confidence anomalies
        conf_anomaly = self._check_low_confidence(context.get("confidence", 1.0))
        if conf_anomaly:
            anomalies.append(conf_anomaly)
        
        # Check for count discrepancies
        discrep_anomaly = self._check_count_discrepancy(
            context.get("quantity_estimate", 0),
            context.get("observed_quantity", None)
        )
        if discrep_anomaly:
            anomalies.append(discrep_anomaly)
        
        if anomalies:
            severity = max(a["severity"] for a in anomalies)
            return {
                "agent": "anomaly",
                "anomalies_detected": len(anomalies),
                "severity": severity,
                "details": anomalies,
                "recommendation": "Review flagged items manually; escalate if severity=critical",
                "confidence": 0.92,  # High confidence (statistical)
            }
        else:
            return {
                "agent": "anomaly",
                "anomalies_detected": 0,
                "severity": "none",
                "details": [],
                "recommendation": "No anomalies detected",
                "confidence": 0.95,
            }
    
    def _check_sudden_drop(self, history: list) -> Optional[dict]:
        """
        Check if there's a sudden quantity drop (possible damage/theft).
        """
        if len(history) < 3:
            return None
        
        recent = history[:3]
        recent_avg = mean(recent)
        last_drop = recent[0] - recent[1]
        
        # Anomaly if drop is >50% and unusual for history
        if len(history) > 5:
            historical_std = stdev(history[3:])
            if last_drop > recent_avg * 0.5 and last_drop > historical_std * 2:
                return {
                    "type": "sudden_drop",
                    "severity": "critical",
                    "description": f"Quantity dropped {last_drop} units suddenly",
                    "possible_cause": "Damage, misplacement, or theft",
                }
        
        return None
    
    def _check_low_confidence(self, confidence: float) -> Optional[dict]:
        """
        Check if reconciliation confidence is too low.
        """
        if confidence < 0.70:
            severity = "critical" if confidence < 0.50 else "warning"
            return {
                "type": "low_confidence",
                "severity": severity,
                "description": f"Reconciliation confidence only {confidence:.1%}",
                "possible_cause": "Camera quality, occlusion, or tracking loss",
            }
        
        return None
    
    def _check_count_discrepancy(self, estimated: int, observed: Optional[int]) -> Optional[dict]:
        """
        Check for large discrepancies between estimated and observed counts.
        """
        if observed is None or estimated is None:
            return None
        
        discrepancy = abs(estimated - observed)
        percent_diff = (discrepancy / max(estimated, 1)) * 100
        
        # Anomaly if >25% difference
        if percent_diff > 25:
            return {
                "type": "count_discrepancy",
                "severity": "warning" if percent_diff < 50 else "critical",
                "description": f"Verified: {estimated}, Observed: {observed} ({percent_diff:.0f}% difference)",
                "possible_cause": "Misplaced items, occluded products, or tracking error",
            }
        
        return None
