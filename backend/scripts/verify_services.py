"""Explicit disposable-service smoke test, used by CI (not the user's database)."""
import json
import time
from uuid import uuid4
import redis
from pydantic import SecretStr
from sqlalchemy.engine import make_url
from app.core.config import settings
from app.database import SessionLocal
from app.models import Camera, Product, ShelfZone, Alert, Inventory
from app.services.reconciliation import ReconciliationEngine
from app.workers.events import process_rules, deliver
from app.services.notifications import queue_notifications, deliver_one
from app.services.chat_graph import run_chat


def main():
    if settings.APP_ENV != "test" or make_url(settings.DATABASE_URL).database != "intellistock_test":
        raise RuntimeError("This smoke test only writes to APP_ENV=test / intellistock_test")
    if settings.CHAT_PROVIDER != "local":
        raise RuntimeError("Service smoke requires CHAT_PROVIDER=local; no provider calls are allowed")
    suffix = uuid4().hex
    client = redis.from_url(settings.REDIS_URL, socket_timeout=2)
    client.ping()
    with SessionLocal() as db:
        camera = Camera(name=f"smoke-{suffix}", location="disposable CI")
        product = Product(sku=suffix, name="Smoke product", low_stock_threshold=2)
        db.add_all([camera, product]); db.flush()
        zone = ShelfZone(camera_id=camera.id, name="Smoke shelf", roi_polygon="[[0,0],[1,0],[1,1],[0,1]]")
        db.add(zone); db.commit()
        camera_id, zone_id, product_id = camera.id, zone.id, product.id
        for _ in range(3):
            ReconciliationEngine(db).reconcile_observation(camera_id, zone_id, product_id, 1, .95)
        assert db.query(Inventory).filter_by(zone_id=zone_id).one().quantity_estimate == 1
    process_rules()
    process_rules()
    with SessionLocal() as db:
        assert db.query(Alert).filter_by(zone_id=zone_id).count() == 1
    with client.pubsub() as subscription:
        subscription.subscribe("inventory.events")
        assert subscription.get_message(timeout=2)["type"] == "subscribe"
        assert deliver(client) >= 1
        deadline = time.monotonic() + 5
        seen = False
        while time.monotonic() < deadline:
            message = subscription.get_message(ignore_subscribe_messages=True, timeout=1)
            if message and json.loads(message["data"]).get("zone_id") == zone_id:
                seen = True
                break
        assert seen, "Committed event did not reach Redis subscriber"
    client.close()
    # Exercise real PostgreSQL enum comparisons/queueing, but never contact SMTP.
    mail_config = settings.model_copy(update={"NOTIFICATIONS_ENABLED":True,
        "NOTIFICATION_EMAIL_TO":"ci-approved@example.com", "SMTP_HOST":"unused.example.com",
        "SMTP_USERNAME":"ci", "SMTP_PASSWORD":SecretStr("ci-only"), "SMTP_FROM":"ci@example.com"})
    assert queue_notifications(config=mail_config) >= 1
    sent = []
    assert deliver_one(config=mail_config, sender=lambda delivery, alert, config: sent.append(delivery.id))
    assert sent
    with SessionLocal() as db:
        answer = run_chat(db, f"Inventory for SKU {suffix}")
        assert answer["mode"] == "local"
        assert len(answer["sources"]) == 1
        assert "1 committed" in answer["answer"]
    print("PostgreSQL reconciliation, durable alert and Redis delivery smoke passed")


if __name__ == "__main__":
    main()
