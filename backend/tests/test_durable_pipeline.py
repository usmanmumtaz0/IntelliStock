"""Synthetic detector replay through reconciliation, rules, retry and lifecycle."""
import json
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Camera, Product, ShelfZone, Inventory, InventoryStatus, Alert
from app.models.delivery import OutboxEvent
from app.models.alert import AlertStatus
from app.cv.runtime import Detection, ShelfPipeline, Zone
from app.workers.vision import apply_observations
from app.workers.events import process_rules, deliver
from app.services.stock_alerts import maintain_alerts
from app.services.alert_service import AlertService
from app.services.outbox import enqueue
from app.services.camera_heartbeat import CameraHeartbeatService


@pytest.fixture
def scenario(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'pipeline.sqlite3'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        camera = Camera(name="replay", location="test")
        product = Product(sku=str(uuid4()), name="Test product", low_stock_threshold=2)
        db.add_all([camera, product]); db.flush()
        zone = ShelfZone(name="A", camera_id=camera.id, roi_polygon="[[0,0],[1,0],[1,1],[0,1]]")
        db.add(zone); db.commit()
    yield factory, camera, product, zone
    engine.dispose()


class Publisher:
    def __init__(self, fails=False):
        self.fails = fails
        self.messages = []

    def publish(self, channel, payload):
        if self.fails:
            raise ConnectionError("redis unavailable")
        self.messages.append(json.loads(payload))
        return 1


def replay(factory, camera, product, zone, counts):
    region = Zone(zone.id, [[0,0],[1,0],[1,1],[0,1]], {0: product.id}, frozenset({0}))
    pipeline = ShelfPipeline([region], min_hits=2)
    for sequence, quantity in enumerate(counts):
        detections = [Detection(0, i, .95, (.1, .1, .2, .2)) for i in range(quantity)]
        observations = pipeline.observe(detections, sequence, datetime.now(timezone.utc))
        with factory() as db:
            apply_observations(db, camera.id, [region], observations)
        process_rules(factory)
    return region


def test_replay_creates_one_alert_and_recovers_delivery(scenario):
    factory, camera, product, zone = scenario
    replay(factory, camera, product, zone, [1] * 8)
    with factory() as db:
        assert db.query(Inventory).one().quantity_estimate == 1
        assert db.query(Alert).count() == 1
        assert db.query(OutboxEvent).filter(OutboxEvent.published_at.is_(None)).count() >= 2
    process_rules(factory)  # Retrying processed records must not duplicate alerts.
    assert deliver(Publisher(fails=True), factory) == 0
    with factory() as db:
        for event in db.query(OutboxEvent).all():
            assert event.last_error == "ConnectionError"
            event.available_at = datetime.utcnow() - timedelta(seconds=1)
        db.commit()
    publisher = Publisher()
    assert deliver(publisher, factory) >= 2
    assert deliver(publisher, factory) == 0
    with factory() as db:
        assert db.query(Alert).count() == 1


def test_empty_then_restock_resolves_stockout(scenario):
    factory, camera, product, zone = scenario
    replay(factory, camera, product, zone, [0] * 8 + [6] * 10)
    with factory() as db:
        assert db.query(Inventory).one().quantity_estimate == 6
        assert db.query(Alert).one().status == AlertStatus.RESOLVED


def test_failed_frame_preserves_count_and_marks_uncertain(scenario):
    factory, camera, product, zone = scenario
    region = replay(factory, camera, product, zone, [6] * 8)
    with factory() as db:
        apply_observations(db, camera.id, [region], [])
        inv = db.query(Inventory).one()
        assert inv.quantity_estimate == 6
        assert inv.status == InventoryStatus.DETECTION_UNCERTAIN
        apply_observations(db, camera.id, [region], [], offline=True)
        assert inv.status == InventoryStatus.CAMERA_OFFLINE


def test_snooze_defers_escalation_then_expires(scenario):
    factory, camera, product, zone = scenario
    replay(factory, camera, product, zone, [1] * 8)
    with factory() as db:
        alert = db.query(Alert).one()
        alert.created_at = datetime.utcnow() - timedelta(hours=1)
        db.commit()
        AlertService(db).snooze_alert(alert.id, "manager", 60)
        maintain_alerts(db); db.commit()
        assert alert.status == AlertStatus.OPEN
        maintain_alerts(db, datetime.utcnow() + timedelta(hours=2)); db.commit()
        assert alert.status == AlertStatus.ESCALATED
        assert alert.snoozed_until is None


def test_rollback_does_not_leave_event(scenario):
    factory, *_ = scenario
    with factory() as db:
        enqueue(db, "test", {})
        db.rollback()
        assert db.query(OutboxEvent).count() == 0


@pytest.mark.parametrize("healthy,age", [(False, 0), (True, 60)])
def test_bad_or_stale_frame_cannot_produce_zero(healthy, age):
    zone = Zone("z", [[0,0],[1,0],[1,1],[0,1]], {0: "p"}, frozenset({0}))
    pipeline = ShelfPipeline([zone])
    assert pipeline.observe([], 1, datetime.now(timezone.utc) - timedelta(seconds=age), healthy) == []


def test_empty_requires_explicit_calibration_and_occlusion_abstains():
    zone = Zone("z", [[0,0],[1,0],[1,1],[0,1]], {0: "p"})
    pipeline = ShelfPipeline([zone])
    assert pipeline.observe([], 1, datetime.now(timezone.utc)) == []
    zone = Zone("z", zone.polygon, zone.products, frozenset({0}))
    pipeline = ShelfPipeline([zone])
    assert pipeline.observe([Detection(99, 1, .9, (.1,.1,.8,.8))], 1, datetime.now(timezone.utc)) == []


def test_camera_offline_does_not_affect_other_camera(scenario):
    factory, camera, product, zone = scenario
    replay(factory, camera, product, zone, [6] * 8)
    with factory() as db:
        other = Camera(name="other", location="test")
        db.add(other); db.flush()
        CameraHeartbeatService()._mark_camera_offline(db, other)
        assert db.query(Inventory).one().status == InventoryStatus.ADEQUATE


def test_zone_health_preserves_offline_and_uncertain_states(scenario):
    from app.api.zones import zone_health
    factory, camera, product, zone = scenario
    replay(factory, camera, product, zone, [6] * 8)
    with factory() as db:
        inventory = db.query(Inventory).one()
        inventory.status = InventoryStatus.CAMERA_OFFLINE
        assert zone_health(camera, [inventory], .99) == "offline"
        inventory.status = InventoryStatus.DETECTION_UNCERTAIN
        assert zone_health(camera, [inventory], .99) == "pending"
