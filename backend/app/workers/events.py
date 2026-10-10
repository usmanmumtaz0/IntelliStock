"""Durable rule processing followed by at-least-once realtime delivery."""
import json
import logging
import signal
from datetime import datetime, timedelta
from threading import Event
import redis
from app.core.config import settings
from app.database import SessionLocal
from app.models.delivery import OutboxEvent
from app.services.stock_alerts import evaluate_committed_stock, maintain_alerts

logger = logging.getLogger(__name__)


def process_rules(session_factory=SessionLocal):
    with session_factory() as db:
        with db.begin():
            events = db.query(OutboxEvent).filter(OutboxEvent.processed_at.is_(None)).order_by(
                OutboxEvent.created_at, OutboxEvent.id).with_for_update(skip_locked=True).limit(100).all()
            for event in events:
                if event.topic == "stock_updated":
                    evaluate_committed_stock(db, json.loads(event.payload))
                event.processed_at = datetime.utcnow()
            maintain_alerts(db)
    return len(events)


def deliver(publisher, session_factory=SessionLocal):
    count = 0
    with session_factory() as db:
        with db.begin():
            events = db.query(OutboxEvent).filter(
                OutboxEvent.processed_at.isnot(None), OutboxEvent.published_at.is_(None),
                OutboxEvent.available_at <= datetime.utcnow()).order_by(
                    OutboxEvent.created_at, OutboxEvent.id).with_for_update(skip_locked=True).limit(50).all()
            for event in events:
                event.attempts += 1
                try:
                    publisher.publish("inventory.events", event.payload)
                except Exception as exc:
                    # Persist a safe error type; provider messages may contain credentials.
                    event.last_error = type(exc).__name__
                    event.available_at = datetime.utcnow() + timedelta(seconds=min(300, 2 ** min(event.attempts, 8)))
                else:
                    event.published_at = datetime.utcnow()
                    event.last_error = None
                    count += 1
    return count


def main():
    logging.basicConfig(level=settings.LOG_LEVEL)
    stop = Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    publisher = redis.from_url(settings.REDIS_URL, socket_timeout=1, socket_connect_timeout=1)
    try:
        while not stop.is_set():
            try:
                process_rules()
                deliver(publisher)
            except Exception:
                logger.exception("Event worker iteration failed; will retry")
            stop.wait(1)
    finally:
        publisher.close()


if __name__ == "__main__":
    main()
