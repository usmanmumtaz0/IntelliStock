"""Inventory API contract tests for trusted, pending, optional, and paginated data."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.database import SessionLocal
from app.models.camera import Camera
from app.models.inventory import Inventory, InventoryStatus
from app.models.product import Product
from app.models.user import User, UserRole
from app.models.zone import ShelfZone
from app.services.observation_window import Observation, get_observation_window


@pytest.fixture
def contract_data():
    suffix = uuid4().hex[:8]
    with SessionLocal() as db:
        user = User(
            email=f"inventory-{suffix}@test.local",
            username=f"inventory-{suffix}",
            hashed_password=hash_password("inventory-test-password"),
            role=UserRole.STAFF,
        )
        camera = Camera(name=f"Camera {suffix}", location="Test aisle", is_active=True)
        product = Product(
            sku=f"INV-{suffix}",
            name="Contract Product",
            low_stock_threshold=5,
            reorder_point=10,
        )
        db.add_all([user, camera, product])
        db.flush()
        zone = ShelfZone(
            camera_id=camera.id,
            name=f"Zone {suffix}",
            roi_polygon="[[0,0],[1,0],[1,1],[0,1]]",
        )
        db.add(zone)
        db.flush()
        verified = Inventory(
            zone_id=zone.id,
            product_id=product.id,
            quantity_estimate=12,
            confidence=0.92,
            status=InventoryStatus.ADEQUATE,
            last_observation_time=datetime.utcnow().isoformat(),
            observations_count=3,
        )
        pending = Inventory(
            zone_id=zone.id,
            product_id=product.id,
            quantity_estimate=10,
            confidence=0.4,
            status=InventoryStatus.DETECTION_UNCERTAIN,
            last_observation_time=datetime.utcnow().isoformat(),
            observations_count=1,
        )
        db.add_all([verified, pending])
        db.commit()
        ids = {
            "user": user.id,
            "email": user.email,
            "username": user.username,
            "camera": camera.id,
            "zone": zone.id,
            "product": product.id,
            "verified": verified.id,
            "pending": pending.id,
        }

    token = create_access_token(
        user_id=ids["user"],
        username=ids["username"],
        email=ids["email"],
        role="staff",
    )
    ids["headers"] = {"Authorization": f"Bearer {token}"}
    yield ids

    get_observation_window(ids["camera"], ids["zone"], ids["product"]).clear()
    with SessionLocal() as db:
        db.query(Inventory).filter(Inventory.id.in_([ids["verified"], ids["pending"]])).delete(
            synchronize_session=False
        )
        db.query(ShelfZone).filter(ShelfZone.id == ids["zone"]).delete(synchronize_session=False)
        db.query(Product).filter(Product.id == ids["product"]).delete(synchronize_session=False)
        db.query(Camera).filter(Camera.id == ids["camera"]).delete(synchronize_session=False)
        db.query(User).filter(User.id == ids["user"]).delete(synchronize_session=False)
        db.commit()


def test_populated_and_verified_inventory_contract(client: TestClient, contract_data):
    response = client.get(
        f"/api/v1/inventory/{contract_data['verified']}", headers=contract_data["headers"]
    )
    assert response.status_code == 200
    item = response.json()
    assert item["id"] == contract_data["verified"]
    assert item["sku"].startswith("INV-")
    assert item["name"] == "Contract Product"
    assert item["current_quantity"] == 12
    assert item["threshold"] == 5
    assert item["status"] == "adequate"
    assert item["verified"] is True
    assert item["pending_quantity"] is None
    assert isinstance(item["confidence"], float)
    assert item["updated_at"]


def test_empty_inventory_filter(client: TestClient, contract_data):
    response = client.get(
        "/api/v1/inventory?zone_id=does-not-exist", headers=contract_data["headers"]
    )
    assert response.status_code == 200
    assert response.json() == []
    assert response.headers["X-Total-Count"] == "0"
    assert response.headers["Content-Range"] == "items */0"


def test_pending_observation_is_not_promoted_to_trusted_quantity(client: TestClient, contract_data):
    window = get_observation_window(
        contract_data["camera"], contract_data["zone"], contract_data["product"]
    )
    window.clear()
    window.add_observation(
        Observation(
            camera_id=contract_data["camera"],
            zone_id=contract_data["zone"],
            product_id=contract_data["product"],
            quantity=7,
            confidence=0.55,
        )
    )
    response = client.get(
        f"/api/v1/inventory/{contract_data['pending']}", headers=contract_data["headers"]
    )
    item = response.json()
    assert item["current_quantity"] == 10
    assert item["pending_quantity"] == 7
    assert item["verified"] is False


def test_missing_optional_product_values_are_null(client: TestClient, contract_data):
    orphan_id = str(uuid4())
    with SessionLocal() as db:
        orphan = Inventory(
            id=orphan_id,
            zone_id=contract_data["zone"],
            product_id=str(uuid4()),
            quantity_estimate=0,
            confidence=0,
            status=InventoryStatus.UNKNOWN,
            observations_count=0,
        )
        db.add(orphan)
        db.commit()
    try:
        response = client.get(f"/api/v1/inventory/{orphan_id}", headers=contract_data["headers"])
        assert response.status_code == 200
        item = response.json()
        assert item["sku"] is None
        assert item["name"] is None
        assert item["threshold"] is None
        assert item["last_observation_time"] is None
        assert item["verified"] is False
    finally:
        with SessionLocal() as db:
            db.query(Inventory).filter(Inventory.id == orphan_id).delete(synchronize_session=False)
            db.commit()


def test_inventory_filters_and_pagination(client: TestClient, contract_data):
    response = client.get(
        f"/api/v1/inventory?zone_id={contract_data['zone']}&limit=1&offset=1",
        headers=contract_data["headers"],
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.headers["X-Total-Count"] == "2"
    assert response.headers["Content-Range"] == "items 1-1/2"

    status_response = client.get(
        "/api/v1/inventory?status=adequate", headers=contract_data["headers"]
    )
    assert status_response.status_code == 200
    assert all(item["status"] == "adequate" for item in status_response.json())


@pytest.mark.parametrize("query", ["status=invalid", "limit=0", "limit=501", "offset=-1"])
def test_invalid_inventory_filters_return_422(client: TestClient, contract_data, query: str):
    assert client.get(f"/api/v1/inventory?{query}", headers=contract_data["headers"]).status_code == 422
