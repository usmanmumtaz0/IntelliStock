"""Bounded live capture; replay reads every frame in file order."""
from datetime import datetime, timezone
from queue import Queue, Empty, Full
from threading import Event, Thread


class FrameSource:
    def __init__(self, source, replay=False):
        import cv2
        self.capture = cv2.VideoCapture(int(source) if source.isdecimal() else source)
        self.replay = replay
        self.queue = Queue(maxsize=2)
        self.stop_event = Event()
        self.thread = None
        if not replay:
            self.thread = Thread(target=self._capture, daemon=True)
            self.thread.start()

    def _capture(self):
        try:
            while not self.stop_event.is_set():
                ok, frame = self.capture.read()
                sample = (ok, frame, datetime.now(timezone.utc))
                try:
                    self.queue.put_nowait(sample)
                except Full:
                    try:
                        self.queue.get_nowait()
                    except Empty:
                        pass
                    self.queue.put_nowait(sample)
                if not ok:
                    break
        finally:
            self.capture.release()

    def read(self):
        if self.replay:
            ok, frame = self.capture.read()
            return ok, frame, datetime.now(timezone.utc)
        try:
            return self.queue.get(timeout=2)
        except Empty:
            return False, None, datetime.now(timezone.utc)

    def close(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=3)
            if self.thread.is_alive():
                raise RuntimeError("Camera read is blocked; restart the CV worker")
        else:
            self.capture.release()
