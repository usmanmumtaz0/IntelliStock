"""
Tests for Phase 9 Week 2: Alert service and rule engine.
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.database.connection import init_db
from app.models.product import Product
from app.models.camera import Camera
from app.models.zone import ShelfZone
from app.models.inventory import Inventory
from app.models.alert import Alert, AlertType, AlertSeverity, AlertStatus
from app.services.alert_service import AlertService
from app.services.alert_rule_engine import AlertRuleEngine


@pytest.fixture
def db():
    """Initialize database and return session."""
    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_data(db: Session):
    """Create sample entities."""
    product = Product(
        sku=f"TEST-SKU-{str(uuid4())[:8]}",
        name="Test Product",
        low_stock_threshold=5,
        reorder_point=20,
    )
    db.add(product)
    
    camera = Camera(
        name="Test Camera",
        location="Test Location",
        source_url="test://camera",
        fps=2,
        offline_timeout_seconds=30,
    )
    db.add(camera)
    db.flush()
    
    zone = ShelfZone(
        camera_id=camera.id,
        name="Test Zone",
        roi_polygon='[[0,0],[1,0],[1,1],[0,1]]',
        detection_confidence_threshold=0.6,
    )
    db.add(zone)
    db.commit()
    
    return {"product": product, "camera": camera, "zone": zone}


class TestAlertCreation:
    """Test alert creation."""

    def test_create_low_stock_alert(self, db: Session, sample_data):
        """Test creating a low stock alert."""
        service = AlertService(db)
        
        alert = service.alert_low_stock(
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
            current_qty=3,
            low_stock_threshold=5,
        )
        
        assert alert.alert_type == AlertType.LOW_STOCK
        assert alert.severity == AlertSeverity.MEDIUM
        assert alert.status == AlertStatus.OPEN
        assert alert.current_quantity == 3

    def test_create_out_of_stock_alert(self, db: Session, sample_data):
        """Test creating an out of stock alert."""
        service = AlertService(db)
        
        alert = service.alert_out_of_stock(
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
        )
        
        assert alert.alert_type == AlertType.OUT_OF_STOCK
        assert alert.severity == AlertSeverity.HIGH
        assert alert.current_quantity == 0

    def test_create_anomaly_alert(self, db: Session, sample_data):
        """Test creating an anomaly alert."""
        service = AlertService(db)
        
        alert = service.alert_anomaly(
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
            current_qty=5,
            expected_qty=15,
            variance=0.67,
        )
        
        assert alert.alert_type == AlertType.ANOMALY
        assert alert.severity == AlertSeverity.HIGH

    def test_create_stockout_risk_alert(self, db: Session, sample_data):
        """Test creating a stockout risk alert."""
        service = AlertService(db)
        
        alert = service.alert_stockout_risk(
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
            current_qty=10,
            days_to_stockout=2,
            depletion_rate=5.0,
        )
        
        assert alert.alert_type == AlertType.STOCKOUT_RISK
        assert alert.severity == AlertSeverity.HIGH  # 2 days is <=3


class TestAlertManagement:
    """Test alert lifecycle management."""

    def test_acknowledge_alert(self, db: Session, sample_data):
        """Test acknowledging an alert."""
        service = AlertService(db)
        user_id = str(uuid4())
        
        alert = service.alert_low_stock(
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
            current_qty=3,
            low_stock_threshold=5,
        )
        
        updated = service.acknowledge_alert(alert.id, user_id)
        
        assert updated.status == AlertStatus.ACKNOWLEDGED
        assert updated.acknowledged_by_user == user_id
        assert updated.acknowledged_at is not None

    def test_resolve_alert(self, db: Session, sample_data):
        """Test resolving an alert."""
        service = AlertService(db)
        user_id = str(uuid4())
        
        alert = service.alert_low_stock(
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
            current_qty=3,
            low_stock_threshold=5,
        )
        
        updated = service.resolve_alert(alert.id, user_id)
        
        assert updated.status == AlertStatus.RESOLVED
        assert updated.resolved_by_user == user_id
        assert updated.resolved_at is not None

    def test_dismiss_alert(self, db: Session, sample_data):
        """Test dismissing an alert."""
        service = AlertService(db)
        
        alert = service.alert_low_stock(
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
            current_qty=3,
            low_stock_threshold=5,
        )
        
        updated = service.dismiss_alert(alert.id)
        
        assert updated.status == AlertStatus.DISMISSED

    def test_escalate_alert(self, db: Session, sample_data):
        """Test escalating an alert."""
        service = AlertService(db)
        
        alert = service.alert_low_stock(
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
            current_qty=3,
            low_stock_threshold=5,
        )
        
        updated = service.escalate_alert(alert.id, AlertSeverity.HIGH)
        
        assert updated.status == AlertStatus.ESCALATED
        assert updated.severity == AlertSeverity.HIGH


class TestAlertQuerying:
    """Test alert queries."""

    def test_get_open_alerts(self, db: Session, sample_data):
        """Test querying open alerts."""
        service = AlertService(db)
        
        # Create alerts
        for i in range(3):
            service.alert_low_stock(
                zone_id=sample_data["zone"].id,
                product_id=sample_data["product"].id,
                current_qty=i,
                low_stock_threshold=5,
            )
        
        records, total = service.get_open_alerts(limit=100, offset=0)
        
        assert total >= 3
        assert len(records) >= 3

    def test_get_open_alerts_by_zone(self, db: Session, sample_data):
        """Test querying open alerts by zone."""
        service = AlertService(db)
        
        service.alert_low_stock(
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
            current_qty=3,
            low_stock_threshold=5,
        )
        
        records, total = service.get_open_alerts(
            zone_id=sample_data["zone"].id,
            limit=100,
            offset=0,
        )
        
        assert total >= 1
        assert all(r.zone_id == sample_data["zone"].id for r in records)

    def test_get_alerts_by_zone(self, db: Session, sample_data):
        """Test getting all alerts for a zone."""
        service = AlertService(db)
        
        for i in range(3):
            service.alert_low_stock(
                zone_id=sample_data["zone"].id,
                product_id=sample_data["product"].id,
                current_qty=i,
                low_stock_threshold=5,
            )
        
        records, total = service.get_alerts_by_zone(
            zone_id=sample_data["zone"].id,
            days=30,
        )
        
        assert total >= 3

    def test_get_alerts_by_product(self, db: Session, sample_data):
        """Test getting all alerts for a product."""
        service = AlertService(db)
        
        for i in range(2):
            service.alert_low_stock(
                zone_id=sample_data["zone"].id,
                product_id=sample_data["product"].id,
                current_qty=i,
                low_stock_threshold=5,
            )
        
        records, total = service.get_alerts_by_product(
            product_id=sample_data["product"].id,
            days=30,
        )
        
        assert total >= 2

    def test_get_alerts_by_severity(self, db: Session, sample_data):
        """Test querying alerts by severity."""
        service = AlertService(db)
        
        # Create alerts with different severities
        service.alert_low_stock(
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
            current_qty=3,
            low_stock_threshold=5,
        )
        
        service.alert_out_of_stock(
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
        )
        
        # Query by severity
        records, total = service.get_alerts_by_severity(
            severity=AlertSeverity.HIGH,
            days=30,
        )
        
        assert total >= 1
        assert all(r.severity == AlertSeverity.HIGH for r in records)

    def test_get_critical_alerts(self, db: Session, sample_data):
        """Test getting critical and high severity alerts."""
        service = AlertService(db)
        
        # Create high severity alert
        service.alert_out_of_stock(
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
        )
        
        records = service.get_critical_alerts()
        
        assert len(records) >= 1
        assert all(
            r.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]
            for r in records
        )

    def test_get_unacknowledged_alerts(self, db: Session, sample_data):
        """Test getting unacknowledged alerts."""
        service = AlertService(db)
        
        service.alert_low_stock(
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
            current_qty=3,
            low_stock_threshold=5,
        )
        
        records = service.get_unacknowledged_alerts()
        
        assert len(records) >= 1
        assert all(r.status == AlertStatus.OPEN for r in records)


class TestAlertStatistics:
    """Test alert statistics."""

    def test_get_alert_stats(self, db: Session, sample_data):
        """Test alert statistics."""
        service = AlertService(db)
        
        # Create various alerts
        service.alert_low_stock(
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
            current_qty=3,
            low_stock_threshold=5,
        )
        
        service.alert_out_of_stock(
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
        )
        
        stats = service.get_alert_stats(days=30)
        
        assert stats["total_alerts"] >= 2
        assert stats["open_alerts"] >= 2
        assert stats["critical"] >= 0
        assert stats["high"] >= 1
        assert "by_type" in stats

    def test_alert_stats_after_resolve(self, db: Session, sample_data):
        """Test statistics reflect resolved alerts."""
        service = AlertService(db)
        user_id = str(uuid4())
        
        alert = service.alert_low_stock(
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
            current_qty=3,
            low_stock_threshold=5,
        )
        
        stats_before = service.get_alert_stats(days=30)
        open_before = stats_before["open_alerts"]
        
        service.resolve_alert(alert.id, user_id)
        
        stats_after = service.get_alert_stats(days=30)
        open_after = stats_after["open_alerts"]
        
        assert open_after < open_before


class TestAlertCleanup:
    """Test alert retention and cleanup."""

    def test_cleanup_old_alerts(self, db: Session, sample_data):
        """Test cleanup of old alerts."""
        service = AlertService(db)
        
        # Create an old alert
        old_alert = Alert(
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
            alert_type=AlertType.LOW_STOCK,
            severity=AlertSeverity.MEDIUM,
            status=AlertStatus.RESOLVED,
            title="Old alert",
            current_quantity=3,
            source_system="rule_engine",
        )
        old_alert.created_at = datetime.utcnow() - timedelta(days=100)
        db.add(old_alert)
        
        # Create recent alert
        service.alert_low_stock(
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
            current_qty=3,
            low_stock_threshold=5,
        )
        
        db.commit()
        
        # Cleanup
        deleted = service.cleanup_expired_alerts(retention_days=90)
        
        assert deleted >= 1
        
        # Verify old alert is deleted
        old = db.query(Alert).filter(Alert.title == "Old alert").first()
        assert old is None


class TestAlertRuleEngine:
    """Test alert rule engine."""

    def test_low_stock_rule(self, db: Session, sample_data):
        """Test low stock rule triggers alert."""
        # Create inventory below threshold
        inv = Inventory(
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
            quantity_estimate=3,  # Below threshold of 5
        )
        db.add(inv)
        db.commit()
        
        engine = AlertRuleEngine(db)
        engine.evaluate_inventory(inv)
        
        # Check alert was created
        alerts = db.query(Alert).filter(
            Alert.zone_id == sample_data["zone"].id,
            Alert.product_id == sample_data["product"].id,
            Alert.alert_type == AlertType.LOW_STOCK,
        ).all()
        
        assert len(alerts) >= 1

    def test_out_of_stock_rule(self, db: Session, sample_data):
        """Test out of stock rule."""
        inv = Inventory(
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
            quantity_estimate=0,
        )
        db.add(inv)
        db.commit()
        
        engine = AlertRuleEngine(db)
        engine.evaluate_inventory(inv)
        
        alerts = db.query(Alert).filter(
            Alert.zone_id == sample_data["zone"].id,
            Alert.product_id == sample_data["product"].id,
            Alert.alert_type == AlertType.OUT_OF_STOCK,
        ).all()
        
        assert len(alerts) >= 1
