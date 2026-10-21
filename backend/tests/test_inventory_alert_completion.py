"""Completion coverage for committed-stock alert episodes and email content."""
from unittest.mock import Mock

from app.models import Alert, Inventory, NotificationDelivery
from app.models.alert import AlertStatus, AlertType
from app.models.inventory import InventoryStatus
from app.services.notifications import send_email
from app.services.stock_alerts import evaluate_committed_stock
from tests.test_durable_pipeline import scenario  # noqa: F401
from tests.test_notifications_reports import mail_data  # noqa: F401


def _evaluate(factory, zone_id, product_id, quantity, threshold):
    with factory() as db:
        inventory = db.query(Inventory).filter_by(
            zone_id=zone_id, product_id=product_id
        ).first()
        if inventory is None:
            inventory = Inventory(
                zone_id=zone_id,
                product_id=product_id,
                quantity_estimate=quantity,
                confidence=1.0,
                status=InventoryStatus.ADEQUATE,
            )
            db.add(inventory)
        inventory.quantity_estimate = quantity
        inventory.status = (
            InventoryStatus.OUT_OF_STOCK
            if quantity == 0
            else InventoryStatus.LOW_STOCK
            if quantity <= threshold
            else InventoryStatus.ADEQUATE
        )
        db.flush()
        evaluate_committed_stock(
            db,
            {
                "zone_id": zone_id,
                "product_id": product_id,
                "event_id": f"quantity-{quantity}",
            },
        )
        db.commit()


def test_threshold_boundaries_refresh_deduplicate_and_create_new_episode(scenario):
    factory, _camera, product, zone = scenario
    threshold = product.low_stock_threshold

    _evaluate(factory, zone.id, product.id, 20, threshold)
    with factory() as db:
        assert db.query(Alert).count() == 0

    _evaluate(factory, zone.id, product.id, threshold, threshold)
    with factory() as db:
        first = db.query(Alert).one()
        first_id = first.id
        assert first.alert_type == AlertType.LOW_STOCK
        assert first.current_quantity == threshold
        assert first.threshold_value == threshold

    _evaluate(factory, zone.id, product.id, threshold - 1, threshold)
    _evaluate(factory, zone.id, product.id, threshold - 1, threshold)
    with factory() as db:
        assert db.query(Alert).count() == 1
        refreshed = db.get(Alert, first_id)
        assert refreshed.current_quantity == threshold - 1
        assert refreshed.status == AlertStatus.OPEN

    _evaluate(factory, zone.id, product.id, threshold + 10, threshold)
    with factory() as db:
        assert db.get(Alert, first_id).status == AlertStatus.RESOLVED

    # Re-entry is a new episode even inside ALERT_COOLDOWN_SECONDS.
    _evaluate(factory, zone.id, product.id, threshold, threshold)
    with factory() as db:
        assert db.query(Alert).count() == 2
        assert db.query(Alert).filter(Alert.status == AlertStatus.OPEN).count() == 1

    _evaluate(factory, zone.id, product.id, 0, threshold)
    with factory() as db:
        active = db.query(Alert).filter(Alert.status == AlertStatus.OPEN).one()
        assert active.alert_type == AlertType.OUT_OF_STOCK
        assert active.current_quantity == 0
        assert active.threshold_value == threshold


def test_stock_email_contains_required_context(mail_data, monkeypatch):
    factory, config, _ids, _headers = mail_data
    submit = Mock()
    monkeypatch.setattr("app.services.notifications._submit_email", submit)

    with factory() as db:
        alert = db.query(Alert).one()
        alert.threshold_value = 10
        alert.product.brand = "Test Brand"
        delivery = NotificationDelivery(
            alert_id=alert.id,
            alert_stage=alert.status.value,
            recipient=config.NOTIFICATION_EMAIL_TO,
        )
        db.add(delivery)
        db.flush()

        send_email(delivery, alert, config)
        message = submit.call_args.args[0]
        body = message.get_content()
        assert message["Subject"] == "IntelliStock Low stock Alert - Test item"
        assert "Product: Test item" in body
        assert "Brand: Test Brand" in body
        assert "SKU: =SUM(A1)" in body
        assert "Current stock: 2" in body
        assert "Minimum threshold: 10" in body
        assert "Status: Low stock" in body
        assert "Event time:" in body
        assert "/inventory?product_id=" in body

        alert.alert_type = AlertType.OUT_OF_STOCK
        alert.current_quantity = 0
        submit.reset_mock()
        send_email(delivery, alert, config)
        message = submit.call_args.args[0]
        assert message["Subject"] == "IntelliStock Out of stock Alert - Test item"
        assert "Current stock: 0" in message.get_content()
        assert "Status: Out of stock" in message.get_content()