"""Contract tests for the persistent alert API used by the React client."""
from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.database import SessionLocal
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.camera import Camera
from app.models.product import Product
from app.models.user import User, UserRole
from app.models.zone import ShelfZone


def _headers(user: User) -> dict[str, str]:
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        email=user.email,
        role=user.role.value,
    )
    return {"Authorization": f"Bearer {token}"}


def test_snooze_permissions_and_contract(client, alert_contract_data):
    data = alert_contract_data
    path = f"/api/v1/alerts/{data['alert_ids'][0]}/snooze"
    assert client.post(path, json={"minutes": 60}, headers=data["staff_headers"]).status_code == 403
    assert client.post(path, json={"minutes": 2}, headers=data["manager_headers"]).status_code == 422
    response = client.post(path, json={"minutes": 60}, headers=data["manager_headers"])
    assert response.status_code == 200
    with SessionLocal() as db:
        assert db.get(Alert, data["alert_ids"][0]).snoozed_until is not None
    listing = client.get(f"/api/v1/alerts?zone_id={data['zone_id']}", headers=data["manager_headers"]).json()
    snoozed = next(item for item in listing["data"] if item["id"] == data["alert_ids"][0])
    assert snoozed["snoozed_until"].endswith("+00:00")
    base = f"/api/v1/alerts/{data['alert_ids'][0]}"
    assert client.post(base + "/resolve", headers=data["manager_headers"]).status_code == 200
    assert client.post(base + "/acknowledge", headers=data["manager_headers"]).status_code == 409


@pytest.fixture
def alert_contract_data():
    suffix = uuid4().hex[:10]
    with SessionLocal() as db:
        camera = Camera(name=f"Contract camera {suffix}", location="Test aisle")
        product = Product(sku=f"ALERT-{suffix}", name="Contract product")
        manager = User(
            email=f"alert-manager-{suffix}@test.local",
            username=f"alert-manager-{suffix}",
            hashed_password=hash_password("contract-test-password"),
            role=UserRole.MANAGER,
        )
        staff = User(
            email=f"alert-staff-{suffix}@test.local",
            username=f"alert-staff-{suffix}",
            hashed_password=hash_password("contract-test-password"),
            role=UserRole.STAFF,
        )
        db.add_all([camera, product, manager, staff])
        db.flush()
        zone = ShelfZone(
            camera_id=camera.id,
            name=f"Contract zone {suffix}",
            roi_polygon="[[0,0],[1,0],[1,1],[0,1]]",
        )
        db.add(zone)
        db.flush()
        alerts = [
            Alert(
                zone_id=zone.id,
                product_id=product.id,
                alert_type=AlertType.LOW_STOCK,
                severity=AlertSeverity.HIGH,
                status=AlertStatus.OPEN,
                title=f"Contract alert {suffix}-{index}",
                current_quantity=index,
                confidence=0.91,
                impact_score=0.8,
                source_system="contract_test",
            )
            for index in range(2)
        ]
        db.add_all(alerts)
        db.commit()
        snapshot = {
            "alert_ids": [alert.id for alert in alerts],
            "zone_id": zone.id,
            "product_id": product.id,
            "camera_id": camera.id,
            "manager_id": manager.id,
            "staff_id": staff.id,
            "manager_headers": _headers(manager),
            "staff_headers": _headers(staff),
        }

    yield snapshot

    with SessionLocal() as db:
        db.query(Alert).filter(Alert.id.in_(snapshot["alert_ids"])).delete(synchronize_session=False)
        db.query(ShelfZone).filter(ShelfZone.id == snapshot["zone_id"]).delete(synchronize_session=False)
        db.query(Product).filter(Product.id == snapshot["product_id"]).delete(synchronize_session=False)
        db.query(Camera).filter(Camera.id == snapshot["camera_id"]).delete(synchronize_session=False)
        db.query(User).filter(User.id.in_([snapshot["manager_id"], snapshot["staff_id"]])).delete(synchronize_session=False)
        db.commit()


def test_alert_list_has_stable_pagination_and_filters(client: TestClient, alert_contract_data):
    response = client.get(
        "/api/v1/alerts?status=OPEN&severity=HIGH&limit=1",
        headers=alert_contract_data["staff_headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"data", "pagination"}
    assert body["pagination"]["limit"] == 1
    assert body["pagination"]["total"] >= 2
    assert len(body["data"]) == 1
    assert body["data"][0]["status"] == "OPEN"
    assert body["data"][0]["severity"] == "HIGH"


def test_alert_mutations_use_authenticated_actor_and_roles(client: TestClient, alert_contract_data):
    alert_id = alert_contract_data["alert_ids"][0]
    forbidden = client.post(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        headers=alert_contract_data["staff_headers"],
    )
    assert forbidden.status_code == 403

    response = client.post(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        headers=alert_contract_data["manager_headers"],
    )
    assert response.status_code == 200
    assert response.json() == {
        "status": "acknowledged",
        "alert_id": alert_id,
        "affected": 1,
        "message": "Alert acknowledged",
    }
    with SessionLocal() as db:
        alert = db.query(Alert).filter(Alert.id == alert_id).one()
        assert alert.status == AlertStatus.ACKNOWLEDGED
        assert alert.acknowledged_by_user == alert_contract_data["manager_id"]

    missing = client.post(
        f"/api/v1/alerts/{uuid4()}/resolve",
        headers=alert_contract_data["manager_headers"],
    )
    assert missing.status_code == 404


def test_acknowledge_all_returns_real_affected_count(client: TestClient, alert_contract_data):
    response = client.post(
        "/api/v1/alerts/acknowledge-all",
        headers=alert_contract_data["manager_headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "acknowledged"
    assert body["alert_id"] is None
    assert body["affected"] >= 2

    with SessionLocal() as db:
        records = db.query(Alert).filter(Alert.id.in_(alert_contract_data["alert_ids"])).all()
        assert all(record.status == AlertStatus.ACKNOWLEDGED for record in records)
        assert all(record.acknowledged_by_user == alert_contract_data["manager_id"] for record in records)
