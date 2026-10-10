"""Independent mail worker: python -m app.workers.notifications."""
import logging
import signal
from threading import Event
from app.services.notifications import queue_notifications, deliver_one, configuration_status


def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    stop = Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    logger.info("Notification worker started; ready=%s", configuration_status()["ready"])
    while not stop.is_set():
        try:
            queue_notifications()
            for _ in range(5):
                if stop.is_set() or not deliver_one():
                    break
        except Exception as exc:
            logger.error("Notification iteration failed (%s); retrying", type(exc).__name__)
        stop.wait(5)


if __name__ == "__main__":
    main()
