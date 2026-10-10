"""Audit evidence using disposable databases; known defects await approval to fix."""
from unittest.mock import Mock
import pytest
from tests.test_operations import ops  # noqa: F401
from tests.test_notifications_reports import mail_data  # noqa: F401
from app.models import Inventory, Alert
from app.models.inventory import InventoryStatus
from app.models.alert import AlertStatus
from app.services.notifications import queue_notifications, deliver_one
from app.services.stock_alerts import evaluate_committed_stock


def test_manual_correction_status_transitions(client, ops):
    path = f"/api/v1/inventory/{ops['inventory']}"
    for quantity, expected in [(2, "low_stock"), (0, "out_of_stock"), (10, "adequate")]:
        current = client.get(path, headers=ops["headers"]["manager"])
        assert current.status_code == 200
        result = client.post(path + "/corrections", headers=ops["headers"]["manager"], json={
            "quantity": quantity, "reason": "Isolated workflow audit", "expected_updated_at": current.json()["updated_at"],
        })
        assert result.status_code == 200
        assert result.json()["status"] == expected


@pytest.mark.xfail(strict=True, reason="Audit: mail worker does not recheck inventory after restock")
def test_mail_does_not_send_stale_low_stock_after_restock(mail_data):
    factory, config, _, _ = mail_data
    queue_notifications(factory, config)
    with factory() as db:
        inv = db.query(Inventory).one()
        inv.quantity_estimate = 100
        inv.status = InventoryStatus.ADEQUATE
        db.commit()
    sender = Mock()
    deliver_one(factory, config, sender)
    sender.assert_not_called()


@pytest.mark.xfail(strict=True, reason="Audit: delayed stock payload can create alert against newer adequate inventory")
def test_old_low_stock_event_cannot_reopen_restocked_inventory(mail_data):
    factory, _, _, _ = mail_data
    with factory() as db:
        inv = db.query(Inventory).one()
        inv.quantity_estimate = 100
        inv.status = InventoryStatus.ADEQUATE
        alert = db.query(Alert).one()
        alert.status = AlertStatus.RESOLVED
        alert.active_key = None
        # Remove cooldown as a confounder: test a genuinely delayed event.
        from datetime import datetime, timedelta
        alert.created_at = datetime.utcnow() - timedelta(days=1)
        db.flush()
        evaluate_committed_stock(db, {"zone_id": inv.zone_id, "product_id": inv.product_id,
                                     "quantity": 1, "status": "low_stock", "confidence": 0})
        db.flush()
        assert db.query(Alert).filter(Alert.status == AlertStatus.OPEN).count() == 0
