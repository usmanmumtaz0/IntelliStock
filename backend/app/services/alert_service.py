"""
Alert service — generates, manages, and queries alerts.
Phase 9 Week 2: Alert Lifecycle & Analytics.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.alert import Alert, AlertType, AlertSeverity, AlertStatus
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.inventory_history import InventoryHistory

logger = logging.getLogger(__name__)


class AlertService:
    """Manages alert lifecycle, creation, and querying."""

    def __init__(self, db: Session):
        self.db = db

    # Alert Creation Methods
    def create_alert(
        self,
        zone_id: str,
        product_id: str,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        current_quantity: int,
        description: str = None,
        recommendation: str = None,
        threshold_value: int = None,
        threshold_type: str = None,
        confidence: float = 1.0,
        impact_score: float = 0.5,
        source_system: str = "rule_engine",
        related_event_id: str = None,
    ) -> Alert:
        """Create a new alert."""
        alert = Alert(
            zone_id=zone_id,
            product_id=product_id,
            alert_type=alert_type,
            severity=severity,
            status=AlertStatus.OPEN,
            title=title,
            description=description,
            recommendation=recommendation,
            current_quantity=current_quantity,
            threshold_value=threshold_value,
            threshold_type=threshold_type,
            confidence=confidence,
            impact_score=impact_score,
            source_system=source_system,
            related_event_id=related_event_id,
        )
        self.db.add(alert)
        self.db.commit()
        logger.info(f"Created alert: {alert_type.value} for {zone_id}/{product_id}")
        return alert

    def alert_low_stock(
        self,
        zone_id: str,
        product_id: str,
        current_qty: int,
        low_stock_threshold: int,
    ) -> Alert:
        """Create LOW_STOCK alert."""
        return self.create_alert(
            zone_id=zone_id,
            product_id=product_id,
            alert_type=AlertType.LOW_STOCK,
            severity=AlertSeverity.MEDIUM,
            title=f"Low stock alert",
            current_quantity=current_qty,
            description=f"Inventory is {current_qty} units, below threshold of {low_stock_threshold}",
            recommendation="Prepare for restocking",
            threshold_value=low_stock_threshold,
            threshold_type="low_stock",
            impact_score=0.6,
        )

    def alert_out_of_stock(
        self,
        zone_id: str,
        product_id: str,
    ) -> Alert:
        """Create OUT_OF_STOCK alert."""
        return self.create_alert(
            zone_id=zone_id,
            product_id=product_id,
            alert_type=AlertType.OUT_OF_STOCK,
            severity=AlertSeverity.HIGH,
            title="Out of stock",
            current_quantity=0,
            description="Product is completely out of stock",
            recommendation="Restock immediately",
            impact_score=0.95,
        )

    def alert_anomaly(
        self,
        zone_id: str,
        product_id: str,
        current_qty: int,
        expected_qty: int,
        variance: float,
    ) -> Alert:
        """Create ANOMALY alert for unusual quantity changes."""
        return self.create_alert(
            zone_id=zone_id,
            product_id=product_id,
            alert_type=AlertType.ANOMALY,
            severity=AlertSeverity.HIGH,
            title="Unusual quantity change detected",
            current_quantity=current_qty,
            description=f"Quantity changed unexpectedly. Expected ~{expected_qty}, got {current_qty} ({variance:.1%} variance)",
            recommendation="Review for theft, damage, or detection error",
            impact_score=0.75,
        )

    def alert_detection_failure(
        self,
        zone_id: str,
        product_id: str,
        confidence: float,
    ) -> Alert:
        """Create DETECTION_FAILURE alert."""
        return self.create_alert(
            zone_id=zone_id,
            product_id=product_id,
            alert_type=AlertType.DETECTION_FAILURE,
            severity=AlertSeverity.MEDIUM,
            title="Detection confidence low",
            current_quantity=-1,  # Unknown
            description=f"CV detection confidence is {confidence:.2f}, below threshold",
            recommendation="Check camera angle, lighting, or ROI configuration",
            confidence=confidence,
            impact_score=0.5,
        )

    def alert_stockout_risk(
        self,
        zone_id: str,
        product_id: str,
        current_qty: int,
        days_to_stockout: int,
        depletion_rate: float,
    ) -> Alert:
        """Create STOCKOUT_RISK alert (predictive)."""
        return self.create_alert(
            zone_id=zone_id,
            product_id=product_id,
            alert_type=AlertType.STOCKOUT_RISK,
            severity=AlertSeverity.HIGH if days_to_stockout <= 3 else AlertSeverity.MEDIUM,
            title=f"Stockout risk: {days_to_stockout} days",
            current_quantity=current_qty,
            description=f"At current depletion rate of {depletion_rate:.2f} units/day, "
                       f"product will stock out in ~{days_to_stockout} days",
            recommendation="Schedule restocking soon",
            impact_score=0.8,
        )

    # Alert Management
    def acknowledge_alert(self, alert_id: str, user_id: str) -> Alert:
        """Mark alert as acknowledged by user."""
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_by_user = user_id
            alert.acknowledged_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"Acknowledged alert {alert_id}")
        return alert

    def resolve_alert(self, alert_id: str, user_id: str) -> Alert:
        """Mark alert as resolved."""
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_by_user = user_id
            alert.resolved_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"Resolved alert {alert_id}")
        return alert

    def dismiss_alert(self, alert_id: str) -> Alert:
        """Dismiss alert (acknowledged but no action needed)."""
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.status = AlertStatus.DISMISSED
            self.db.commit()
            logger.info(f"Dismissed alert {alert_id}")
        return alert

    def escalate_alert(self, alert_id: str, new_severity: AlertSeverity) -> Alert:
        """Escalate alert to higher severity."""
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.status = AlertStatus.ESCALATED
            alert.severity = new_severity
            self.db.commit()
            logger.info(f"Escalated alert {alert_id} to {new_severity.value}")
        return alert

    # Querying
    def get_open_alerts(
        self,
        zone_id: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[Alert], int]:
        """Get all open alerts, optionally filtered by zone."""
        query = self.db.query(Alert).filter(Alert.status == AlertStatus.OPEN)
        
        if zone_id:
            query = query.filter(Alert.zone_id == zone_id)
        
        total = query.count()
        records = (
            query.order_by(desc(Alert.severity), desc(Alert.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
        
        return records, total

    def list_alerts(
        self,
        *,
        status: AlertStatus | None = None,
        severity: AlertSeverity | None = None,
        alert_type: AlertType | None = None,
        zone_id: str | None = None,
        product_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[Alert], int]:
        """List persistent alerts using validated lifecycle filters."""
        query = self.db.query(Alert)
        if status is not None:
            query = query.filter(Alert.status == status)
        if severity is not None:
            query = query.filter(Alert.severity == severity)
        if alert_type is not None:
            query = query.filter(Alert.alert_type == alert_type)
        if zone_id:
            query = query.filter(Alert.zone_id == zone_id)
        if product_id:
            query = query.filter(Alert.product_id == product_id)

        total = query.count()
        records = (
            query.order_by(desc(Alert.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
        return records, total

    def acknowledge_all(self, user_id: str) -> int:
        """Acknowledge every currently open alert and return the affected count."""
        alerts = self.db.query(Alert).filter(Alert.status == AlertStatus.OPEN).all()
        acknowledged_at = datetime.utcnow()
        for alert in alerts:
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_by_user = user_id
            alert.acknowledged_at = acknowledged_at
        self.db.commit()
        return len(alerts)

    def get_alerts_by_zone(
        self,
        zone_id: str,
        days: int = 30,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[Alert], int]:
        """Get all alerts in a zone."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = self.db.query(Alert).filter(
            Alert.zone_id == zone_id,
            Alert.created_at >= cutoff,
        )
        
        total = query.count()
        records = (
            query.order_by(desc(Alert.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
        
        return records, total

    def get_alerts_by_product(
        self,
        product_id: str,
        days: int = 30,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[Alert], int]:
        """Get all alerts for a product across zones."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = self.db.query(Alert).filter(
            Alert.product_id == product_id,
            Alert.created_at >= cutoff,
        )
        
        total = query.count()
        records = (
            query.order_by(desc(Alert.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
        
        return records, total

    def get_alerts_by_severity(
        self,
        severity: AlertSeverity,
        days: int = 30,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[Alert], int]:
        """Get alerts by severity level."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = self.db.query(Alert).filter(
            Alert.severity == severity,
            Alert.created_at >= cutoff,
        )
        
        total = query.count()
        records = (
            query.order_by(desc(Alert.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
        
        return records, total

    def get_critical_alerts(self) -> List[Alert]:
        """Get all CRITICAL and HIGH severity open alerts."""
        return self.db.query(Alert).filter(
            Alert.status == AlertStatus.OPEN,
            Alert.severity.in_([AlertSeverity.CRITICAL, AlertSeverity.HIGH]),
        ).order_by(desc(Alert.created_at)).all()

    def get_unacknowledged_alerts(self, limit: int = 50) -> List[Alert]:
        """Get unacknowledged alerts."""
        return self.db.query(Alert).filter(
            Alert.status == AlertStatus.OPEN,
        ).order_by(desc(Alert.severity), desc(Alert.created_at)).limit(limit).all()

    # Statistics
    def get_alert_stats(self, days: int = 30) -> dict:
        """Get alert statistics."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        total = self.db.query(Alert).filter(Alert.created_at >= cutoff).count()
        open_alerts = self.db.query(Alert).filter(
            Alert.status == AlertStatus.OPEN,
            Alert.created_at >= cutoff,
        ).count()
        critical = self.db.query(Alert).filter(
            Alert.severity == AlertSeverity.CRITICAL,
            Alert.created_at >= cutoff,
        ).count()
        high = self.db.query(Alert).filter(
            Alert.severity == AlertSeverity.HIGH,
            Alert.created_at >= cutoff,
        ).count()
        
        # By type
        by_type = {}
        for alert_type in AlertType:
            count = self.db.query(Alert).filter(
                Alert.alert_type == alert_type,
                Alert.created_at >= cutoff,
            ).count()
            if count > 0:
                by_type[alert_type.value] = count
        
        return {
            "total_alerts": total,
            "open_alerts": open_alerts,
            "critical": critical,
            "high": high,
            "by_type": by_type,
        }

    def cleanup_expired_alerts(self, retention_days: int = 90):
        """Delete alerts older than retention period (hard delete)."""
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        
        deleted = (
            self.db.query(Alert)
            .filter(Alert.created_at < cutoff)
            .delete(synchronize_session=False)
        )
        
        self.db.commit()
        logger.info(f"Deleted {deleted} old alerts")
        return deleted
