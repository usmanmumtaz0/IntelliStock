"""Phase 4 role enforcement, atomic operator writes and geometry contracts."""
import json
from datetime import datetime
from uuid import uuid4

import pytest
from app.core.security import create_access_token, hash_password, verify_password
from app.database import SessionLocal
from app.models import Camera, Product, ShelfZone, Inventory, ZoneProductMapping, OutboxEvent
from app.models.user import User, UserRole
from app.models.inventory import InventoryStatus
from app.models.inventory_history import InventoryHistory
from app.models.audit_log import AuditLog
from app.schemas.zone import ZoneInput
from app.api.inventory import CorrectionRequest
from app.services.operations import correct_inventory


@pytest.fixture
def ops():
    suffix = uuid4().hex[:10]
    with SessionLocal() as db:
        users = {role: User(username=f"{role}-{suffix}", email=f"{role}-{suffix}@test.local",
                           hashed_password=hash_password("operations-password"), role=UserRole(role))
                 for role in ("admin", "manager", "staff")}
        camera = Camera(name=suffix, location="Test", is_active=False)
        product = Product(sku=suffix, name="Test product", low_stock_threshold=2)
        db.add_all([camera, product, *users.values()]); db.flush()
        zone = ShelfZone(name="A1", camera_id=camera.id, roi_polygon="[[0,0],[1,0],[1,1],[0,1]]")
        db.add(zone); db.flush()
        db.add(ZoneProductMapping(zone_id=zone.id, product_id=product.id, class_id=0))
        inv = Inventory(zone_id=zone.id, product_id=product.id, quantity_estimate=5,
                        confidence=.9, observations_count=3, last_observation_time=datetime.utcnow().isoformat(),
                        status=InventoryStatus.ADEQUATE)
        db.add(inv); db.commit()
        yield {"camera": camera.id, "product": product.id, "zone": zone.id, "inventory": inv.id,
               "updated_at": inv.updated_at.isoformat(), "users": {role: user.id for role,user in users.items()},
               "headers": {role: {"Authorization": "Bearer " + create_access_token(user.id, user.username, role, user.email)}
                           for role, user in users.items()}}


def zone_data(ops):
    return {"camera_id": ops["camera"], "name": "New shelf", "polygon": [[0,0],[1,0],[1,1],[0,1]],
            "products": [{"class_id": 0, "product_id": ops["product"], "allow_empty": False}]}


def test_account_management_and_revocation(client, ops):
    headers = ops["headers"]
    assert client.get("/api/v1/users", headers=headers["staff"]).status_code == 403
    assert client.get("/api/v1/users", headers=headers["manager"]).status_code == 403
    payload = {"email": f"New-{uuid4().hex}@example.com", "username": uuid4().hex,
               "password": "long-test-password", "role": "staff"}
    created = client.post("/api/v1/users", headers=headers["admin"], json=payload)
    assert created.status_code == 201, created.text
    result = created.json()
    assert "password" not in result and "hashed_password" not in result
    assert result["email"] == payload["email"].lower()
    assert client.post("/api/v1/users", headers=headers["admin"], json=payload).status_code == 409
    with SessionLocal() as db:
        assert verify_password(payload["password"], db.get(User, result["id"]).hashed_password)
        log = db.query(AuditLog).filter_by(resource_id=result["id"]).one()
        assert "password" not in json.dumps(log.new_values)
    change = {"role": "staff", "is_active": False}
    assert client.put(f"/api/v1/users/{ops['users']['admin']}", json=change, headers=headers["admin"]).status_code == 409
    assert client.put(f"/api/v1/users/{ops['users']['staff']}", json=change, headers=headers["admin"]).status_code == 200
    assert client.get("/api/v1/products", headers=headers["staff"]).status_code == 401
    # Existing signed manager token cannot retain privileges after demotion.
    assert client.put(f"/api/v1/users/{ops['users']['manager']}", json={"role":"staff", "is_active":True}, headers=headers["admin"]).status_code == 200
    assert client.post("/api/v1/products", json={"sku":"denied", "name":"denied"}, headers=headers["manager"]).status_code == 403


def test_threshold_update_preserves_offline_and_emits_state(client, ops):
    url = f"/api/v1/products/{ops['product']}"
    assert client.put(url, headers=ops["headers"]["staff"], json={"low_stock_threshold":10}).status_code == 403
    assert client.put(url, headers=ops["headers"]["manager"], json={"low_stock_threshold":None}).status_code == 422
    assert client.put(url, headers=ops["headers"]["manager"], json={"low_stock_threshold":10}).status_code == 200
    with SessionLocal() as db:
        inv = db.get(Inventory, ops["inventory"])
        assert inv.status == InventoryStatus.LOW_STOCK
        assert db.query(AuditLog).filter_by(resource_id=ops["product"], action="update").count() == 1
        assert any(json.loads(row.payload).get("product_id") == ops["product"] for row in db.query(OutboxEvent).filter_by(topic="stock_updated"))
        inv.status = InventoryStatus.CAMERA_OFFLINE; db.commit()
    assert client.put(url, headers=ops["headers"]["manager"], json={"low_stock_threshold":0}).status_code == 200
    with SessionLocal() as db:
        assert db.get(Inventory, ops["inventory"]).status == InventoryStatus.CAMERA_OFFLINE
    assert client.delete(url, headers=ops["headers"]["admin"]).status_code == 409


def test_manual_correction_audit_history_and_conflict(client, ops):
    url = f"/api/v1/inventory/{ops['inventory']}/corrections"
    payload = {"quantity": 0, "reason": "Physical shelf count", "expected_updated_at":ops["updated_at"]}
    assert client.post(url, headers=ops["headers"]["staff"], json=payload).status_code == 403
    assert client.post(url, headers=ops["headers"]["manager"], json={**payload, "quantity":-1}).status_code == 422
    response = client.post(url, headers=ops["headers"]["manager"], json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["current_quantity"] == 0
    assert response.json()["verified"] is False
    assert client.post(url, headers=ops["headers"]["manager"], json=payload).status_code == 409
    with SessionLocal() as db:
        history = db.query(InventoryHistory).filter_by(zone_id=ops["zone"]).one()
        assert (history.previous_quantity, history.new_quantity, history.quantity_delta) == (5,0,-5)
        assert history.actor_user_id == ops["users"]["manager"]
        assert history.reason == payload["reason"]
        assert db.query(AuditLog).filter_by(resource_id=ops["inventory"]).count() == 1


def test_correction_rollback_keeps_inventory_history_outbox_atomic(ops):
    with SessionLocal() as db:
        count = db.query(OutboxEvent).count()
        correct_inventory(db, ops["inventory"], CorrectionRequest(quantity=1, reason="Test rollback", expected_updated_at=ops["updated_at"]), db.get(User, ops["users"]["manager"]))
        db.flush(); db.rollback()
        assert db.get(Inventory, ops["inventory"]).quantity_estimate == 5
        assert db.query(InventoryHistory).filter_by(zone_id=ops["zone"]).count() == 0
        assert db.query(AuditLog).filter_by(resource_id=ops["inventory"]).count() == 0
        assert db.query(OutboxEvent).count() == count


def test_shelf_configuration_permissions_and_safety(client, ops):
    data = zone_data(ops)
    assert client.post("/api/v1/zones", json=data, headers=ops["headers"]["staff"]).status_code == 403
    response = client.post("/api/v1/zones", json=data, headers=ops["headers"]["manager"])
    assert response.status_code == 201, response.text
    config = response.json()
    assert config["restart_required"] and config["products"][0]["allow_empty"] is False
    assert client.post("/api/v1/zones", json=data, headers=ops["headers"]["manager"]).status_code == 409
    assert client.get(f"/api/v1/zones/{config['id']}/configuration", headers=ops["headers"]["staff"]).json()["polygon"] == data["polygon"]
    data["name"] = "Changed shelf"
    assert client.put(f"/api/v1/zones/{config['id']}", json=data, headers=ops["headers"]["manager"]).status_code == 200
    with SessionLocal() as db:
        assert db.query(AuditLog).filter_by(resource_id=config["id"]).count() == 2
        db.get(Camera, ops["camera"]).is_active = True; db.commit()
    assert client.put(f"/api/v1/zones/{config['id']}", json=data, headers=ops["headers"]["manager"]).status_code == 409


@pytest.mark.parametrize("polygon", [
    [[0,0],[2,0],[1,1]], [[0,0],[.5,.5],[1,1]],
    [[0,0],[1,1],[0,1],[1,0]], [[0,0],[1,0],[1,1],[0,0]],
    [[0,0],[1,1],[0,1],[.8,0]],
])
def test_reject_invalid_roi(polygon, ops):
    with pytest.raises(ValueError):
        ZoneInput.model_validate({**zone_data(ops), "polygon": polygon})


def test_mapping_and_camera_validation(client, ops):
    data = zone_data(ops)
    data["products"] *= 2
    assert client.post("/api/v1/zones", json=data, headers=ops["headers"]["manager"]).status_code == 422
    camera_url = f"/api/v1/cameras/{ops['camera']}"
    assert client.put(camera_url, json={"fps":None}, headers=ops["headers"]["manager"]).status_code == 422
    assert client.put(camera_url, json={"offline_timeout_seconds":45}, headers=ops["headers"]["manager"]).json()["offline_timeout_seconds"] == 45
    assert client.delete(camera_url, headers=ops["headers"]["admin"]).status_code == 409
    assert client.put(camera_url, json={"is_active":False, "source_url":"rtsp://secret:password@camera"}, headers=ops["headers"]["manager"]).status_code == 200
    with SessionLocal() as db:
        assert db.get(Inventory, ops["inventory"]).status == InventoryStatus.CAMERA_OFFLINE
        assert all("password" not in json.dumps(log.new_values) for log in db.query(AuditLog).filter_by(resource_id=ops["camera"]))


def test_configuration_revision_stops_old_worker(client, ops):
    from app.workers.vision import camera_configuration_current
    with SessionLocal() as db:
        camera = db.get(Camera, ops["camera"])
        camera.is_active = True; db.commit()
        revision = camera.updated_at
        assert camera_configuration_current(db, camera.id, revision)
    url = f"/api/v1/cameras/{ops['camera']}"
    assert client.put(url, json={"is_active":False}, headers=ops["headers"]["manager"]).status_code == 200
    assert client.post("/api/v1/zones", json=zone_data(ops), headers=ops["headers"]["manager"]).status_code == 201
    assert client.put(url, json={"is_active":True}, headers=ops["headers"]["manager"]).status_code == 200
    with SessionLocal() as db:
        assert not camera_configuration_current(db, ops["camera"], revision)


def test_invalid_user_input_does_not_create_account(client, ops):
    for patch in ({"password":"short"}, {"email":"invalid"}, {"role":"owner"}, {"username":"   "}):
        payload = {"email": f"{uuid4().hex}@example.com", "username":uuid4().hex,
                   "password":"long-test-password", "role":"staff", **patch}
        assert client.post("/api/v1/users", json=payload, headers=ops["headers"]["admin"]).status_code == 422
