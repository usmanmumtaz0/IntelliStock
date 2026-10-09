"""Regression tests for the centralized snake_case-to-wire alias policy."""
from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.api.alerts import AlertResponse
from app.database import SessionLocal
from app.models.event import EventType, InventoryEvent


def test_event_wire_contract_uses_single_frontend_mapping(client: TestClient, auth_headers):
    with SessionLocal() as db:
        event = InventoryEvent(
            event_type=EventType.STOCK_UPDATED,
            zone_id=None,
            product_id=None,
            previous_state="qty=8",
            new_state="qty=5",
            confidence=0.9,
            extra_data=json.dumps({"previous_quantity": 8, "new_quantity": 5}),
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        event_id = event.id
    try:
        response = client.get("/api/v1/events?limit=100", headers=auth_headers)
        assert response.status_code == 200
        item = next(record for record in response.json() if record["id"] == event_id)
        assert item["from"] == 8
        assert item["to"] == 5
        assert "minAgo" in item
        assert "from_qty" not in item
        assert "to_qty" not in item
        assert "min_ago" not in item
    finally:
        with SessionLocal() as db:
            db.query(InventoryEvent).filter(InventoryEvent.id == event_id).delete(synchronize_session=False)
            db.commit()


def test_alert_wire_contract_uses_min_ago_alias():
    payload = AlertResponse(
        id="alert-1",
        type="low_stock",
        severity="warning",
        title="Low stock",
        detail="Verified quantity below threshold",
        zone="A-1",
        sku="SKU-1",
        min_ago=3,
        acknowledged=False,
    ).model_dump(by_alias=True)
    assert payload["minAgo"] == 3
    assert "min_ago" not in payload
