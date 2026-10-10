"""Opt-in SMTP delivery. Never called from reconciliation or alert transactions."""
import re
import smtplib
import ssl
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from sqlalchemy import exists, or_, cast, String
from app.core.config import settings
from app.database import SessionLocal
from app.models.alert import Alert, AlertStatus
from app.models.notification import NotificationDelivery

STAGES = (AlertStatus.OPEN, AlertStatus.ESCALATED)


def approved_recipients(config=settings) -> list[str]:
    """Validate the entire allowlist; never silently drop an invalid destination."""
    raw = config.NOTIFICATION_EMAIL_TO
    if not raw or "\r" in raw or "\n" in raw:
        raise ValueError("Invalid recipient list")
    addresses = [value.strip() for value in raw.split(",")]
    if len(addresses) > 20 or any(
        len(value) > 255 or not re.fullmatch(r"[^\s@<>;,]+@[^\s@<>;,]+\.[^\s@<>;,]+", value)
        for value in addresses
    ):
        raise ValueError("Expected 1 to 20 plain email addresses")
    return list(dict.fromkeys(addresses))


def configuration_status(config=settings) -> dict:
    email = re.compile(r"^[^\s@<>;,]+@[^\s@<>;,]+\.[^\s@<>;,]+$")
    missing = [key for key in ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM", "NOTIFICATION_EMAIL_TO")
               if not getattr(config, key)]
    for key in ("SMTP_HOST", "SMTP_USERNAME", "SMTP_FROM", "NOTIFICATION_EMAIL_TO"):
        value = getattr(config, key)
        if value and (not value.strip() or "\r" in value or "\n" in value):
            missing.append(key + " (invalid whitespace)")
    if config.SMTP_PASSWORD and not config.SMTP_PASSWORD.get_secret_value().strip():
        missing.append("SMTP_PASSWORD (empty)")
    for key in ("SMTP_FROM",):
        if getattr(config, key) and not email.fullmatch(getattr(config, key)):
            missing.append(key + " (one valid email required)")
    try:
        recipients = approved_recipients(config)
    except ValueError:
        recipients = []
        missing.append("NOTIFICATION_EMAIL_TO (1 to 20 comma-separated emails required)")
    if config.SMTP_HOST and any(c.isspace() for c in config.SMTP_HOST):
        missing.append("SMTP_HOST (invalid host)")
    return {"enabled": config.NOTIFICATIONS_ENABLED, "configured": not missing,
            "ready": config.NOTIFICATIONS_ENABLED and not missing, "missing": missing,
            "channel": "email", "max_attempts": config.NOTIFICATION_MAX_ATTEMPTS,
            "recipient_count": len(recipients)}


def queue_notifications(session_factory=SessionLocal, config=settings) -> int:
    if not configuration_status(config)["ready"]:
        return 0
    now = datetime.utcnow()
    with session_factory() as db:
        with db.begin():
            queued = 0
            for recipient in sorted(approved_recipients(config)):
                # Lock alert candidates; uniqueness remains per stage AND recipient.
                already_queued = exists().where(
                    NotificationDelivery.alert_id == Alert.id,
                    NotificationDelivery.alert_stage == cast(Alert.status, String),
                    NotificationDelivery.recipient == recipient)
                alerts = db.query(Alert).filter(Alert.status.in_(STAGES),
                    or_(Alert.snoozed_until.is_(None), Alert.snoozed_until <= now),
                    ~already_queued).order_by(Alert.created_at, Alert.id).with_for_update(skip_locked=True).limit(100).all()
                for alert in alerts:
                    db.add(NotificationDelivery(alert_id=alert.id, alert_stage=alert.status.value,
                        recipient=recipient))
                queued += len(alerts)
            return queued


def send_email(delivery, alert, config=settings):
    if not configuration_status(config)["ready"] or delivery.recipient not in approved_recipients(config):
        raise RuntimeError("Delivery is disabled or recipient is not approved")
    message = EmailMessage()
    message["From"] = config.SMTP_FROM
    message["To"] = delivery.recipient
    message["Subject"] = f"IntelliStock: {alert.alert_type.value} / {alert.severity.value}"
    # Stable ID helps mail systems identify a retry, but SMTP is not exactly-once.
    message["Message-ID"] = f"<{delivery.id}@intellistock.local>"
    message["Date"] = formatdate(localtime=False)
    message.set_content(f"{alert.title}\n\nAlert: {alert.id}\nStage: {alert.status.value}\n"
                        f"Product: {alert.product.name if alert.product else alert.product_id}\n"
                        f"Shelf: {alert.zone.name if alert.zone else alert.zone_id}\n"
                        f"Quantity at alert creation: {alert.current_quantity}\n"
                        "Review current inventory in IntelliStock before acting.\n")
    _submit_email(message, config)


def send_test_email(confirmed_recipient: str, config=settings) -> None:
    """Explicit operator test only; does not enable or drain the alert queue."""
    if not configuration_status(config)["configured"]:
        raise ValueError("SMTP configuration is incomplete")
    if confirmed_recipient not in approved_recipients(config):
        raise ValueError("Confirmation must match one configured recipient")
    message = EmailMessage()
    message["From"] = config.SMTP_FROM
    message["To"] = confirmed_recipient
    message["Subject"] = "IntelliStock: email configuration test"
    message["Date"] = formatdate(localtime=False)
    message["Message-ID"] = make_msgid(domain="intellistock.local")
    message.set_content(
        "This is an explicitly requested IntelliStock email configuration test.\n"
        "It is not a stock alert and contains no inventory records or credentials.\n"
        "Automatic alert delivery has not been enabled by this test.\n"
    )
    _submit_email(message, config)


def _submit_email(message: EmailMessage, config) -> None:
    """Shared verified-TLS transport; never log SMTP responses or credentials."""
    context = ssl.create_default_context()
    factory = smtplib.SMTP_SSL if config.SMTP_SECURITY == "ssl" else smtplib.SMTP
    kwargs = {"host": config.SMTP_HOST, "port": config.SMTP_PORT, "timeout": config.SMTP_TIMEOUT_SECONDS}
    if config.SMTP_SECURITY == "ssl":
        kwargs["context"] = context
    with factory(**kwargs) as smtp:
        if config.SMTP_SECURITY == "starttls":
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
        smtp.login(config.SMTP_USERNAME, config.SMTP_PASSWORD.get_secret_value())
        refused = smtp.send_message(message)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)


def deliver_one(session_factory=SessionLocal, config=settings, sender=None) -> bool:
    if not configuration_status(config)["ready"]:
        return False
    now = datetime.utcnow()
    with session_factory() as db:
        with db.begin():
            delivery = db.query(NotificationDelivery).filter(
                NotificationDelivery.status.in_(("pending", "retry")),
                NotificationDelivery.available_at <= now).order_by(
                    NotificationDelivery.available_at, NotificationDelivery.id).with_for_update(skip_locked=True).first()
            if not delivery:
                return False
            alert = db.get(Alert, delivery.alert_id)
            if (not alert or alert.status.value != delivery.alert_stage or
                    alert.status not in STAGES or delivery.recipient not in approved_recipients(config)):
                delivery.status, delivery.last_error = "cancelled", "Alert stage or approved recipient changed"
                return True
            if alert.snoozed_until and alert.snoozed_until > now:
                delivery.available_at = alert.snoozed_until
                return True
            if delivery.attempts >= config.NOTIFICATION_MAX_ATTEMPTS:
                delivery.status = "failed"
                return True
            delivery.attempts += 1
            try:
                (sender or send_email)(delivery, alert, config)
            except Exception as exc:
                # Never persist SMTP exception text: it can contain credentials/recipients.
                delivery.last_error = type(exc).__name__[:100]
                delivery.status = "failed" if delivery.attempts >= config.NOTIFICATION_MAX_ATTEMPTS else "retry"
                delivery.available_at = now + timedelta(seconds=min(3600, 30 * 2 ** delivery.attempts))
            else:
                delivery.status, delivery.accepted_at, delivery.last_error = "accepted", datetime.utcnow(), None
                alert.notification_sent = True
                alert.notification_sent_at = delivery.accepted_at
                alert.notification_channels = "email"
            return True
