"""
Inventory history service — record and query all inventory changes.
"""
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.models.inventory_history import InventoryHistory, InventoryChangeType
from app.models.inventory import Inventory

logger = logging.getLogger(__name__)


class InventoryHistoryService:
    """Manages inventory history tracking and querying."""

    def __init__(self, db: Session):
        self.db = db

    # Recording changes
    def record_detection(
        self,
        zone_id: str,
        product_id: str,
        previous_qty: int,
        detected_qty: int,
        confidence: float,
        detection_id: str,
        notes: str = None,
    ) -> InventoryHistory:
        """Record a CV detection observation."""
        history = InventoryHistory(
            zone_id=zone_id,
            product_id=product_id,
            previous_quantity=previous_qty,
            new_quantity=detected_qty,
            quantity_delta=detected_qty - previous_qty,
            change_type=InventoryChangeType.DETECTION,
            confidence=confidence,
            source_system="cv_detection",
            related_detection_id=detection_id,
            reason="CV detection in ROI",
            notes=notes,
            actor_system="reconciliation_engine",
        )
        self.db.add(history)
        self.db.commit()
        logger.info(
            f"Recorded detection: {zone_id}/{product_id} {previous_qty}→{detected_qty}"
        )
        return history

    def record_reconciliation(
        self,
        zone_id: str,
        product_id: str,
        previous_qty: int,
        reconciled_qty: int,
        event_id: str,
        confidence: float = 0.95,
    ) -> InventoryHistory:
        """Record reconciliation engine update."""
        history = InventoryHistory(
            zone_id=zone_id,
            product_id=product_id,
            previous_quantity=previous_qty,
            new_quantity=reconciled_qty,
            quantity_delta=reconciled_qty - previous_qty,
            change_type=InventoryChangeType.RECONCILIATION,
            confidence=confidence,
            source_system="reconciliation",
            related_event_id=event_id,
            reason="Reconciliation engine verified",
            actor_system="reconciliation_engine",
        )
        self.db.add(history)
        self.db.commit()
        logger.info(
            f"Recorded reconciliation: {zone_id}/{product_id} {previous_qty}→{reconciled_qty}"
        )
        return history

    def record_manual_update(
        self,
        zone_id: str,
        product_id: str,
        previous_qty: int,
        new_qty: int,
        user_id: str,
        reason: str = None,
    ) -> InventoryHistory:
        """Record manual user update."""
        history = InventoryHistory(
            zone_id=zone_id,
            product_id=product_id,
            previous_quantity=previous_qty,
            new_quantity=new_qty,
            quantity_delta=new_qty - previous_qty,
            change_type=InventoryChangeType.MANUAL_UPDATE,
            confidence=1.0,  # Manual updates are certain
            source_system="manual",
            actor_user_id=user_id,
            reason=reason or "Manual update by user",
        )
        self.db.add(history)
        self.db.commit()
        logger.info(f"Recorded manual update: {zone_id}/{product_id} by {user_id}")
        return history

    def record_restock(
        self,
        zone_id: str,
        product_id: str,
        previous_qty: int,
        new_qty: int,
        user_id: str = None,
        notes: str = None,
    ) -> InventoryHistory:
        """Record restock event."""
        history = InventoryHistory(
            zone_id=zone_id,
            product_id=product_id,
            previous_quantity=previous_qty,
            new_quantity=new_qty,
            quantity_delta=new_qty - previous_qty,
            change_type=InventoryChangeType.RESTOCK,
            confidence=1.0,
            source_system="manual",
            actor_user_id=user_id,
            reason="Restock event",
            notes=notes,
        )
        self.db.add(history)
        self.db.commit()
        logger.info(f"Recorded restock: {zone_id}/{product_id} {previous_qty}→{new_qty}")
        return history

    # Querying
    def get_history_by_zone_product(
        self,
        zone_id: str,
        product_id: str,
        days: int = 30,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[InventoryHistory], int]:
        """Get all changes for a zone/product combination."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(InventoryHistory).filter(
            InventoryHistory.zone_id == zone_id,
            InventoryHistory.product_id == product_id,
            InventoryHistory.created_at >= cutoff,
        )

        total = query.count()
        records = (
            query.order_by(desc(InventoryHistory.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

        return records, total

    def get_recent_changes(
        self,
        limit: int = 50,
        offset: int = 0,
        days: int = 30,
    ) -> tuple[List[InventoryHistory], int]:
        """Get most recent changes across all products."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(InventoryHistory).filter(
            InventoryHistory.created_at >= cutoff
        )

        total = query.count()
        records = (
            query.order_by(desc(InventoryHistory.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

        return records, total

    def get_changes_by_type(
        self,
        change_type: str,
        days: int = 30,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[InventoryHistory], int]:
        """Get all changes of specific type."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(InventoryHistory).filter(
            InventoryHistory.change_type == change_type,
            InventoryHistory.created_at >= cutoff,
        )

        total = query.count()
        records = (
            query.order_by(desc(InventoryHistory.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

        return records, total

    def get_zone_history(
        self,
        zone_id: str,
        days: int = 30,
    ) -> tuple[List[InventoryHistory], int]:
        """Get all changes in a zone."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(InventoryHistory).filter(
            InventoryHistory.zone_id == zone_id,
            InventoryHistory.created_at >= cutoff,
        )

        total = query.count()
        records = (
            query.order_by(desc(InventoryHistory.created_at))
            .limit(1000)
            .all()
        )

        return records, total

    def get_product_history(
        self,
        product_id: str,
        days: int = 30,
    ) -> tuple[List[InventoryHistory], int]:
        """Get all changes for a product across zones."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(InventoryHistory).filter(
            InventoryHistory.product_id == product_id,
            InventoryHistory.created_at >= cutoff,
        )

        total = query.count()
        records = (
            query.order_by(desc(InventoryHistory.created_at))
            .limit(1000)
            .all()
        )

        return records, total

    # Analytics
    def get_depletion_rate(
        self,
        zone_id: str,
        product_id: str,
        days: int = 30,
    ) -> dict:
        """Calculate depletion rate (units per day)."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Get all changes in period
        records = self.db.query(InventoryHistory).filter(
            InventoryHistory.zone_id == zone_id,
            InventoryHistory.product_id == product_id,
            InventoryHistory.created_at >= cutoff,
        ).all()

        if not records:
            return {"rate_per_day": 0, "total_depleted": 0, "events": 0}

        # Calculate depletion (only count negative changes)
        total_depleted = sum(
            abs(r.quantity_delta)
            for r in records
            if r.quantity_delta < 0
        )

        # Date range
        date_range = (datetime.utcnow() - cutoff).days + 1

        rate = total_depleted / date_range if date_range > 0 else 0

        return {
            "rate_per_day": round(rate, 2),
            "total_depleted": total_depleted,
            "events": len(records),
            "date_range_days": date_range,
        }

    def get_stockout_occurrences(
        self,
        zone_id: str,
        product_id: str,
        threshold: int = 2,
        days: int = 30,
    ) -> int:
        """Count how many times inventory fell to/below threshold."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        records = self.db.query(InventoryHistory).filter(
            InventoryHistory.zone_id == zone_id,
            InventoryHistory.product_id == product_id,
            InventoryHistory.created_at >= cutoff,
            InventoryHistory.new_quantity <= threshold,
        ).count()

        return records

    def cleanup_old_records(self, retention_days: int = 90):
        """Delete records older than retention period (hard delete)."""
        cutoff = datetime.utcnow() - timedelta(days=retention_days)

        deleted = (
            self.db.query(InventoryHistory)
            .filter(InventoryHistory.created_at < cutoff)
            .delete(synchronize_session=False)
        )

        self.db.commit()
        logger.info(f"Deleted {deleted} old inventory history records")
        return deleted
