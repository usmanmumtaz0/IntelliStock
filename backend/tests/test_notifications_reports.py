"""No external mail: disposable DB and injected/fake SMTP transport throughout."""
import csv
import io
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.models import Base, Camera, Product, ShelfZone, Inventory, Alert, NotificationDelivery
from app.models.alert import AlertType, AlertSeverity, AlertStatus
from app.models.inventory import InventoryStatus
from app.models.inventory_history import InventoryHistory, InventoryChangeType
from app.models.user import User, UserRole
from app.core.config import settings
from app.core.security import create_access_token
from app.database import get_db
from app.main import app
from app.services.notifications import configuration_status, queue_notifications, deliver_one, send_email


@pytest.fixture
def mail_data():
    engine = create_engine("sqlite://", connect_args={"check_same_thread":False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        camera = Camera(name="Test camera", location="test")
        product = Product(sku="=SUM(A1)", name="Test item")
        db.add_all([camera, product]); db.flush()
        zone = ShelfZone(camera_id=camera.id, name="Shelf", roi_polygon="[[0,0],[1,0],[1,1]]")
        db.add(zone); db.flush()
        db.add(Inventory(zone_id=zone.id, product_id=product.id, quantity_estimate=2, status=InventoryStatus.CAMERA_OFFLINE))
        alert = Alert(zone_id=zone.id, product_id=product.id, alert_type=AlertType.LOW_STOCK,
            severity=AlertSeverity.HIGH, status=AlertStatus.OPEN, title="Low stock", current_quantity=2, source_system="test")
        db.add(alert)
        db.add(InventoryHistory(zone_id=zone.id, product_id=product.id, previous_quantity=4,
            new_quantity=2, quantity_delta=-2, change_type=InventoryChangeType.CORRECTION,
            source_system="manual", reason="@malicious-formula"))
        headers = {}
        for role in ("admin", "manager", "staff"):
            user = User(email=f"{role}@example.com", username=role, role=UserRole(role), hashed_password="unused")
            db.add(user); db.flush()
            headers[role] = {"Authorization":"Bearer " + create_access_token(user.id, user.username, role, user.email)}
        db.commit()
        ids = {"alert":alert.id, "zone":zone.id}
    config = settings.model_copy(update={"NOTIFICATIONS_ENABLED":True, "NOTIFICATION_EMAIL_TO":"approved@example.com",
        "SMTP_HOST":"smtp.example.com", "SMTP_USERNAME":"test", "SMTP_PASSWORD":SecretStr("never-real"),
        "SMTP_FROM":"sender@example.com", "NOTIFICATION_MAX_ATTEMPTS":2})
    def override_db():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = override_db
    yield factory, config, ids, headers
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def test_disabled_and_incomplete_configuration_never_queues_or_sends(mail_data):
    factory, config, _, _ = mail_data
    sender = Mock()
    config.NOTIFICATIONS_ENABLED = False
    assert queue_notifications(factory, config) == 0
    assert not deliver_one(factory, config, sender)
    config.NOTIFICATIONS_ENABLED = True
    config.NOTIFICATION_EMAIL_TO = "one@example.com,invalid-address"
    assert not configuration_status(config)["ready"]
    assert queue_notifications(factory, config) == 0
    assert not deliver_one(factory, config, sender)
    sender.assert_not_called()


def test_deduplication_acceptance_and_escalation(mail_data):
    factory, config, ids, _ = mail_data
    assert queue_notifications(factory, config) == 1
    assert queue_notifications(factory, config) == 0
    sender = Mock()
    assert deliver_one(factory, config, sender)
    assert not deliver_one(factory, config, sender)
    assert sender.call_count == 1
    with factory() as db:
        row = db.query(NotificationDelivery).one()
        assert row.status == "accepted" and row.attempts == 1 and row.accepted_at
        alert = db.get(Alert, ids["alert"])
        assert alert.notification_sent
        alert.status = AlertStatus.ESCALATED; db.commit()
    assert queue_notifications(factory, config) == 1
    assert deliver_one(factory, config, sender)
    assert sender.call_count == 2


def test_multiple_recipients_independent_retries_and_deduplication(mail_data):
    factory, config, _, _ = mail_data
    config.NOTIFICATION_EMAIL_TO = "first@example.com, second@example.com, first@example.com"
    assert configuration_status(config)["recipient_count"] == 2
    assert queue_notifications(factory, config) == 2
    assert queue_notifications(factory, config) == 0
    def sender(delivery, alert, settings):
        if delivery.recipient == "first@example.com":
            raise RuntimeError("unavailable")
    assert deliver_one(factory, config, sender)
    assert deliver_one(factory, config, sender)
    with factory() as db:
        rows = {row.recipient: row.status for row in db.query(NotificationDelivery)}
        assert rows == {"first@example.com": "retry", "second@example.com": "accepted"}
        row = db.query(NotificationDelivery).filter_by(recipient="first@example.com").one()
        row.available_at = datetime.utcnow() - timedelta(seconds=1)
        db.commit()
    config.NOTIFICATION_EMAIL_TO = "second@example.com, third@example.com"
    assert queue_notifications(factory, config) == 1
    sender_mock = Mock()
    while deliver_one(factory, config, sender_mock):
        pass
    assert sender_mock.call_count == 1
    with factory() as db:
        assert db.query(NotificationDelivery).filter_by(recipient="third@example.com").one().status == "accepted"
        assert db.query(NotificationDelivery).filter_by(recipient="first@example.com").one().status == "cancelled"


def test_multiple_recipient_test_email_is_only_sent_to_confirmed_address(mail_data, monkeypatch):
    from app.services.notifications import send_test_email
    _, config, _, _ = mail_data
    config.NOTIFICATION_EMAIL_TO = "first@example.com, second@example.com"
    transport = Mock()
    monkeypatch.setattr("app.services.notifications._submit_email", transport)
    send_test_email("second@example.com", config)
    message = transport.call_args.args[0]
    assert message["To"] == "second@example.com"
    assert "first@example.com" not in message.as_string()


@pytest.mark.parametrize("value", ["a@example.com,", "a@example.com\r\nBcc:b@example.com", "a@example.com; b@example.com", ",".join(f"a{i}@example.com" for i in range(21))])
def test_invalid_recipient_list_fails_closed(mail_data, value):
    factory, config, _, _ = mail_data
    config.NOTIFICATION_EMAIL_TO = value
    assert not configuration_status(config)["ready"]
    assert queue_notifications(factory, config) == 0


def test_retry_backoff_terminal_failure_and_secret_redaction(mail_data):
    factory, config, _, _ = mail_data
    queue_notifications(factory, config)
    sender = Mock(side_effect=RuntimeError("password=never-real"))
    assert deliver_one(factory, config, sender)
    assert not deliver_one(factory, config, sender)
    with factory() as db:
        row = db.query(NotificationDelivery).one()
        assert row.status == "retry" and row.last_error == "RuntimeError"
        assert row.available_at > datetime.utcnow()
        row.available_at = datetime.utcnow() - timedelta(seconds=1); db.commit()
    assert deliver_one(factory, config, sender)
    with factory() as db:
        assert db.query(NotificationDelivery).one().status == "failed"
    assert not deliver_one(factory, config, sender)
    assert sender.call_count == 2


@pytest.mark.parametrize("status", [AlertStatus.RESOLVED, AlertStatus.ACKNOWLEDGED, AlertStatus.DISMISSED, AlertStatus.ESCALATED])
def test_obsolete_stage_is_cancelled(mail_data, status):
    factory, config, ids, _ = mail_data
    queue_notifications(factory, config)
    with factory() as db:
        db.get(Alert, ids["alert"]).status = status; db.commit()
    sender = Mock()
    assert deliver_one(factory, config, sender)
    sender.assert_not_called()
    with factory() as db:
        assert db.query(NotificationDelivery).one().status == "cancelled"


def test_snooze_defers_delivery_and_recipient_change_cancels_old(mail_data):
    factory, config, ids, _ = mail_data
    queue_notifications(factory, config)
    with factory() as db:
        db.get(Alert, ids["alert"]).snoozed_until = datetime.utcnow() + timedelta(hours=1); db.commit()
    sender = Mock()
    deliver_one(factory, config, sender)
    sender.assert_not_called()
    with factory() as db:
        row = db.query(NotificationDelivery).one()
        assert row.attempts == 0
        row.available_at = datetime.utcnow() - timedelta(seconds=1); db.commit()
    config.NOTIFICATION_EMAIL_TO = "different-approved@example.com"
    deliver_one(factory, config, sender)
    with factory() as db:
        assert db.query(NotificationDelivery).one().status == "cancelled"
    sender.assert_not_called()


@pytest.mark.parametrize("security", ["starttls", "ssl"])
def test_smtp_transport_uses_tls_and_stable_message_id(mail_data, monkeypatch, security):
    factory, config, ids, _ = mail_data
    config.SMTP_SECURITY = security
    queue_notifications(factory, config)
    smtp = Mock()
    smtp.send_message.return_value = {}
    context = Mock()
    context.__enter__ = Mock(return_value=smtp)
    context.__exit__ = Mock(return_value=False)
    transport = Mock(return_value=context)
    monkeypatch.setattr(f"app.services.notifications.smtplib.{'SMTP_SSL' if security == 'ssl' else 'SMTP'}", transport)
    assert deliver_one(factory, config)
    smtp.login.assert_called_once_with("test", "never-real")
    if security == "starttls":
        smtp.starttls.assert_called_once()
        assert [call[0] for call in smtp.method_calls][:3] == ["ehlo", "starttls", "ehlo"]
    else:
        assert "context" in transport.call_args.kwargs
    message = smtp.send_message.call_args.args[0]
    assert message["To"] == config.NOTIFICATION_EMAIL_TO
    with factory() as db:
        assert message["Message-ID"] == f"<{db.query(NotificationDelivery).one().id}@intellistock.local>"


def test_notification_api_permissions_and_safe_configuration(client, mail_data):
    _, _, _, headers = mail_data
    assert client.get("/api/v1/notifications/configuration").status_code == 401
    for role in ("staff", "manager"):
        assert client.get("/api/v1/notifications/deliveries", headers=headers[role]).status_code == 403
    response = client.get("/api/v1/notifications/configuration", headers=headers["admin"])
    assert response.status_code == 200
    assert "SMTP_PASSWORD" not in response.json() # Names may appear in missing[], never values.
    assert "never-real" not in response.text
    assert client.get("/api/v1/notifications/deliveries?limit=0", headers=headers["admin"]).status_code == 422


def test_explicit_test_mail_does_not_enable_or_queue_alerts(mail_data, monkeypatch):
    from app.services.notifications import send_test_email
    factory, config, _, _ = mail_data
    config.NOTIFICATIONS_ENABLED = False
    transport = Mock()
    monkeypatch.setattr("app.services.notifications._submit_email", transport)
    send_test_email(config.NOTIFICATION_EMAIL_TO, config)
    message = transport.call_args.args[0]
    assert message["To"] == config.NOTIFICATION_EMAIL_TO
    assert "configuration test" in message["Subject"]
    assert "never-real" not in message.as_string()
    assert not config.NOTIFICATIONS_ENABLED
    with factory() as db:
        assert db.query(NotificationDelivery).count() == 0
    with pytest.raises(ValueError):
        send_test_email("not-approved@example.com", config)
    assert transport.call_count == 1


def test_email_setup_command_is_offline_by_default(mail_data, monkeypatch, capsys):
    from scripts import check_email
    _, config, _, _ = mail_data
    monkeypatch.setattr(check_email, "settings", config)
    sender = Mock()
    monkeypatch.setattr(check_email, "send_test_email", sender)
    assert check_email.main([]) == 0
    sender.assert_not_called()
    with pytest.raises(SystemExit):
        check_email.main(["--send-test"])
    sender.assert_not_called()
    sender.side_effect = RuntimeError("secret-password")
    assert check_email.main(["--send-test", "--confirm-recipient", config.NOTIFICATION_EMAIL_TO]) == 1
    assert "secret-password" not in capsys.readouterr().out


@pytest.mark.parametrize("field", ["SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_HOST"])
def test_whitespace_credentials_are_not_ready(mail_data, field):
    _, config, _, _ = mail_data
    setattr(config, field, SecretStr("   ") if field == "SMTP_PASSWORD" else "   ")
    assert not configuration_status(config)["configured"]


def test_report_summary_filters_and_csv_formula_safety(client, mail_data):
    _, _, ids, headers = mail_data
    assert client.get("/api/v1/reports/summary").status_code == 401
    result = client.get("/api/v1/reports/summary", headers=headers["staff"]).json()
    assert result["committed_units"] == 2
    assert result["states"] == {"camera_offline":1}
    assert result["history_changes"] == 1
    assert result["active_alerts"] == 1
    assert client.get("/api/v1/reports/summary?zone_id=absent", headers=headers["staff"]).json()["inventory_records"] == 0
    for kind in ("inventory", "history"):
        response = client.get(f"/api/v1/reports/export?kind={kind}&zone_id={ids['zone']}", headers=headers["staff"])
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        rows = list(csv.DictReader(io.StringIO(response.text.lstrip("\ufeff"))))
        assert len(rows) == 1 and rows[0]["sku"] == "'=SUM(A1)"
        if kind == "history":
            assert rows[0]["reason"] == "'@malicious-formula"
            assert rows[0]["delta"] == "-2"


def test_report_bounds_and_limit(client, mail_data, monkeypatch):
    _, _, _, headers = mail_data
    for query in ("days=0", "days=91", "kind=invalid"):
        assert client.get(f"/api/v1/reports/export?{query}", headers=headers["staff"]).status_code == 422
    monkeypatch.setattr("app.api.reports.EXPORT_LIMIT", 0)
    assert client.get("/api/v1/reports/export", headers=headers["staff"]).status_code == 413


@pytest.mark.parametrize("text", ["=1+1", " +cmd", "\t@SUM(A1)", "\r-1", "\n=1"])
def test_csv_formula_escape(text):
    from app.api.reports import csv_cell
    assert csv_cell(text).startswith("'")
    assert csv_cell(-2) == -2
