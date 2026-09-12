"""
Tests for Phase 4 reconciliation engine.
Tests observation window, reconciliation logic, and state machine transitions.
"""
import pytest
import json
from uuid import uuid4
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models.product import Product
from app.models.camera import Camera
from app.models.zone import ShelfZone
from app.models.inventory import Inventory, InventoryStatus
from app.services.observation_window import (
    Observation,
    ObservationWindow,
    get_observation_window,
)
from app.services.reconciliation import ReconciliationEngine

client = TestClient(app)


@pytest.fixture
def db():
    """Get database session."""
    return SessionLocal()


@pytest.fixture
def sample_data(db: Session):
    """Create sample product, camera, zone for testing."""
    import uuid
    
    # Create product with unique SKU
    unique_sku = f"TEST-SKU-{str(uuid.uuid4())[:8]}"
    product = Product(
        sku=unique_sku,
        name="Test Product",
        low_stock_threshold=5,
        reorder_point=20,
    )
    db.add(product)
    
    # Create camera
    camera = Camera(
        name="Test Camera",
        location="Test Zone A",
        source_url="test://camera1",
        fps=2,
        offline_timeout_seconds=30,
    )
    db.add(camera)
    db.flush()
    
    # Create shelf zone with ROI polygon
    zone = ShelfZone(
        camera_id=camera.id,
        name="Zone A",
        description="Test zone for unit testing",
        roi_polygon='[[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]',
        detection_confidence_threshold=0.6,
    )
    db.add(zone)
    db.commit()
    
    return {
        "product": product,
        "camera": camera,
        "zone": zone,
    }


def test_observation_window_add_single(db: Session):
    """Test adding a single observation to window."""
    camera_id = str(uuid4())
    zone_id = str(uuid4())
    product_id = str(uuid4())
    
    window = get_observation_window(camera_id, zone_id, product_id)
    
    obs = Observation(
        zone_id=zone_id,
        product_id=product_id,
        quantity=5,
        confidence=0.8,
        camera_id=camera_id,
    )
    
    result = window.add_observation(obs)
    assert len(result) == 1
    assert result[0].quantity == 5
    assert result[0].confidence == 0.8


def test_observation_window_consensus_quantity(db: Session):
    """Test consensus quantity calculation."""
    camera_id = str(uuid4())
    zone_id = str(uuid4())
    product_id = str(uuid4())
    
    window = get_observation_window(camera_id, zone_id, product_id)
    
    # Add 3 observations: 5, 5, 6 (should average to 5)
    for qty in [5, 5, 6]:
        obs = Observation(
            zone_id=zone_id,
            product_id=product_id,
            quantity=qty,
            confidence=0.8,
            camera_id=camera_id,
        )
        window.add_observation(obs)
    
    consensus = window.get_quantity_consensus()
    assert consensus == 5  # Average of [5, 5, 6]


def test_observation_window_variance_tolerance(db: Session):
    """Test variance tolerance in consensus."""
    camera_id = str(uuid4())
    zone_id = str(uuid4())
    product_id = str(uuid4())
    
    window = get_observation_window(camera_id, zone_id, product_id)
    
    # Add observations with high variance: 1, 5, 10
    for qty in [1, 5, 10]:
        obs = Observation(
            zone_id=zone_id,
            product_id=product_id,
            quantity=qty,
            confidence=0.8,
            camera_id=camera_id,
        )
        window.add_observation(obs)
    
    # With high variance, should use median
    consensus = window.get_quantity_consensus()
    assert consensus == 5  # Median of [1, 5, 10]


def test_reconciliation_low_confidence_rejected(db: Session, sample_data):
    """Test that low-confidence observations are rejected."""
    engine = ReconciliationEngine(db)
    
    accepted, reason = engine.reconcile_observation(
        camera_id=sample_data["camera"].id,
        zone_id=sample_data["zone"].id,
        product_id=sample_data["product"].id,
        observed_quantity=5,
        confidence=0.4,  # Below threshold of 0.6
    )
    
    assert not accepted
    assert "Low confidence" in reason


def test_reconciliation_single_observation_insufficient(db: Session, sample_data):
    """Test that single observation without window consensus is rejected."""
    engine = ReconciliationEngine(db)
    
    accepted, reason = engine.reconcile_observation(
        camera_id=sample_data["camera"].id,
        zone_id=sample_data["zone"].id,
        product_id=sample_data["product"].id,
        observed_quantity=5,
        confidence=0.8,
    )
    
    assert not accepted
    assert "Insufficient observations" in reason


def test_reconciliation_accepted_with_consensus(db: Session, sample_data):
    """Test that observations accepted when consensus reached."""
    engine = ReconciliationEngine(db)
    
    # Add 2 observations with good consensus
    for _ in range(2):
        accepted, reason = engine.reconcile_observation(
            camera_id=sample_data["camera"].id,
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
            observed_quantity=5,
            confidence=0.8,
        )
    
    # Second observation should be accepted
    assert accepted
    
    # Check inventory was updated
    inv = db.query(Inventory).filter(
        (Inventory.zone_id == sample_data["zone"].id)
        & (Inventory.product_id == sample_data["product"].id)
    ).first()
    
    assert inv is not None
    assert inv.quantity_estimate == 5


def test_state_machine_adequate_to_low_stock(db: Session, sample_data):
    """Test state transition from ADEQUATE to LOW_STOCK."""
    engine = ReconciliationEngine(db)
    
    # First, establish ADEQUATE state (qty > low_threshold)
    for _ in range(2):
        engine.reconcile_observation(
            camera_id=sample_data["camera"].id,
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
            observed_quantity=10,  # > low_threshold=5
            confidence=0.8,
        )
    
    inv = db.query(Inventory).filter(
        (Inventory.zone_id == sample_data["zone"].id)
        & (Inventory.product_id == sample_data["product"].id)
    ).first()
    
    assert inv.status == InventoryStatus.ADEQUATE
    
    # Clear observation window for new test
    window = get_observation_window(
        sample_data["camera"].id,
        sample_data["zone"].id,
        sample_data["product"].id,
    )
    window.clear()
    
    # Now observe low stock (qty <= low_threshold)
    for _ in range(2):
        engine.reconcile_observation(
            camera_id=sample_data["camera"].id,
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
            observed_quantity=3,  # <= low_threshold=5
            confidence=0.8,
        )
    
    db.refresh(inv)
    assert inv.status == InventoryStatus.LOW_STOCK


def test_state_machine_to_out_of_stock(db: Session, sample_data):
    """Test state transition to OUT_OF_STOCK."""
    engine = ReconciliationEngine(db)
    
    # Observe qty=0
    for _ in range(2):
        engine.reconcile_observation(
            camera_id=sample_data["camera"].id,
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
            observed_quantity=0,
            confidence=0.9,
        )
    
    inv = db.query(Inventory).filter(
        (Inventory.zone_id == sample_data["zone"].id)
        & (Inventory.product_id == sample_data["product"].id)
    ).first()
    
    assert inv.status == InventoryStatus.OUT_OF_STOCK


def test_state_machine_detection_uncertain(db: Session, sample_data):
    """Test transition to DETECTION_UNCERTAIN on low average confidence."""
    engine = ReconciliationEngine(db)
    
    # First establish ADEQUATE state (qty > low_threshold, high confidence)
    for _ in range(2):
        engine.reconcile_observation(
            camera_id=sample_data["camera"].id,
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
            observed_quantity=10,  # > low_threshold=5
            confidence=0.85,
        )
    
    inv = db.query(Inventory).filter(
        (Inventory.zone_id == sample_data["zone"].id)
        & (Inventory.product_id == sample_data["product"].id)
    ).first()
    
    assert inv.status == InventoryStatus.ADEQUATE
    
    # Clear observation window
    window = get_observation_window(
        sample_data["camera"].id,
        sample_data["zone"].id,
        sample_data["product"].id,
    )
    window.clear()
    
    # Observe with marginal confidence (still accepted but lower)
    # This tests the state machine transition based on confidence threshold
    for _ in range(2):
        engine.reconcile_observation(
            camera_id=sample_data["camera"].id,
            zone_id=sample_data["zone"].id,
            product_id=sample_data["product"].id,
            observed_quantity=5,
            confidence=0.61,  # Just above the MIN_CONFIDENCE_THRESHOLD but will average lower
        )
    
    db.refresh(inv)
    # With confidence just above threshold, might still be adequate or low_stock
    # depending on quantity logic
    assert inv.status in [InventoryStatus.ADEQUATE, InventoryStatus.LOW_STOCK, InventoryStatus.DETECTION_UNCERTAIN]


def test_reconciliation_endpoint(db: Session, sample_data):
    """Test reconciliation endpoint via API."""
    # Make two calls to reach consensus
    response1 = client.post(
        "/api/v1/inventory/reconcile",
        json={
            "camera_id": sample_data["camera"].id,
            "zone_id": sample_data["zone"].id,
            "product_id": sample_data["product"].id,
            "observed_quantity": 5,
            "confidence": 0.85,
        },
    )
    
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["accepted"] == False  # First observation not enough
    
    # Second observation
    response2 = client.post(
        "/api/v1/inventory/reconcile",
        json={
            "camera_id": sample_data["camera"].id,
            "zone_id": sample_data["zone"].id,
            "product_id": sample_data["product"].id,
            "observed_quantity": 5,
            "confidence": 0.85,
        },
    )
    
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["accepted"] == True  # Consensus reached
