"""
Alert Rule Engine — generates alerts based on inventory conditions.
Phase 9 Week 2: Rules for low stock, anomalies, performance issues.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.models.alert import AlertType, AlertSeverity
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.inventory_history import InventoryHistory, InventoryChangeType
from app.services.alert_service import AlertService
from app.services.inventory_history_service import InventoryHistoryService

logger = logging.getLogger(__name__)


class AlertRuleEngine:
    """Evaluates conditions and generates alerts."""

    def __init__(self, db: Session):
        self.db = db
        self.alert_service = AlertService(db)
        self.history_service = InventoryHistoryService(db)
        self.anomaly_threshold = 0.3  # 30% variance threshold
        self.detection_failure_threshold = 0.5  # 50% confidence threshold

    def evaluate_all_zones(self):
        """Run all rules across all zones/products."""
        logger.info("Running alert rule engine on all zones")
        
        # Get all inventory records
        inventories = self.db.query(Inventory).all()
        
        for inv in inventories:
            self.evaluate_inventory(inv)

    def evaluate_inventory(self, inv: Inventory):
        """Evaluate rules for a specific inventory record."""
        product = self.db.query(Product).filter(Product.id == inv.product_id).first()
        
        if not product:
            return
        
        # Rule 1: Low stock
        self.check_low_stock(inv, product)
        
        # Rule 2: Out of stock
        self.check_out_of_stock(inv)
        
        # Rule 3: Anomaly detection
        self.check_anomaly(inv)
        
        # Rule 4: Stockout risk (predictive)
        self.check_stockout_risk(inv, product)

    def check_low_stock(self, inv: Inventory, product: Product):
        """Check if inventory is below low stock threshold."""
        if (inv.quantity_estimate is not None and 
            product.low_stock_threshold is not None and
            inv.quantity_estimate <= product.low_stock_threshold and
            inv.quantity_estimate > 0):
            
            # Check if alert already exists (open or recent)
            from app.models.alert import Alert, AlertStatus
            existing = self.db.query(Alert).filter(
                Alert.zone_id == inv.zone_id,
                Alert.product_id == inv.product_id,
                Alert.alert_type == AlertType.LOW_STOCK,
                Alert.status == AlertStatus.OPEN,
            ).first()
            
            if not existing:
                self.alert_service.alert_low_stock(
                    zone_id=inv.zone_id,
                    product_id=inv.product_id,
                    current_qty=inv.quantity_estimate,
                    low_stock_threshold=product.low_stock_threshold,
                )

    def check_out_of_stock(self, inv: Inventory):
        """Check if inventory is completely out of stock."""
        if inv.quantity_estimate == 0:
            # Check if alert already exists
            from app.models.alert import Alert, AlertStatus
            existing = self.db.query(Alert).filter(
                Alert.zone_id == inv.zone_id,
                Alert.product_id == inv.product_id,
                Alert.alert_type == AlertType.OUT_OF_STOCK,
                Alert.status == AlertStatus.OPEN,
            ).first()
            
            if not existing:
                self.alert_service.alert_out_of_stock(
                    zone_id=inv.zone_id,
                    product_id=inv.product_id,
                )

    def check_anomaly(self, inv: Inventory):
        """Detect unusual quantity changes (theft, damage, etc.)."""
        if not inv.quantity_estimate:
            return
        
        # Get recent history (last 7 days)
        records, _ = self.history_service.get_history_by_zone_product(
            zone_id=inv.zone_id,
            product_id=inv.product_id,
            days=7,
            limit=100,
            offset=0,
        )
        
        if len(records) < 3:
            return
        
        # Calculate variance in recent changes
        recent_changes = [abs(r.quantity_delta) for r in records[-5:]]
        if not recent_changes:
            return
        
        avg_change = sum(recent_changes) / len(recent_changes)
        max_change = max(recent_changes)
        
        # Flag if change is >50% larger than average
        if avg_change > 0 and max_change > avg_change * 1.5:
            from app.models.alert import Alert, AlertStatus
            
            existing = self.db.query(Alert).filter(
                Alert.zone_id == inv.zone_id,
                Alert.product_id == inv.product_id,
                Alert.alert_type == AlertType.ANOMALY,
                Alert.status == AlertStatus.OPEN,
            ).first()
            
            if not existing:
                variance = (max_change - avg_change) / avg_change
                self.alert_service.alert_anomaly(
                    zone_id=inv.zone_id,
                    product_id=inv.product_id,
                    current_qty=inv.quantity_estimate,
                    expected_qty=int(avg_change),
                    variance=variance,
                )

    def check_stockout_risk(self, inv: Inventory, product: Product):
        """Predict stockout risk based on depletion rate."""
        metric = self.history_service.get_depletion_rate(
            zone_id=inv.zone_id,
            product_id=inv.product_id,
            days=30,
        )
        
        depletion_rate = metric.get("rate_per_day", 0)
        
        if depletion_rate > 0 and inv.quantity_estimate:
            days_to_stockout = int(inv.quantity_estimate / depletion_rate)
            
            # Alert if stockout expected within 7 days
            if days_to_stockout <= 7:
                from app.models.alert import Alert, AlertStatus
                
                existing = self.db.query(Alert).filter(
                    Alert.zone_id == inv.zone_id,
                    Alert.product_id == inv.product_id,
                    Alert.alert_type == AlertType.STOCKOUT_RISK,
                    Alert.status == AlertStatus.OPEN,
                ).first()
                
                if not existing:
                    self.alert_service.alert_stockout_risk(
                        zone_id=inv.zone_id,
                        product_id=inv.product_id,
                        current_qty=inv.quantity_estimate,
                        days_to_stockout=days_to_stockout,
                        depletion_rate=depletion_rate,
                    )
