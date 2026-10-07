"""
Video Ingestion Service (CV-001)
Handles video source input (file or webcam) with configurable frame sampling.
Outputs frames at target FPS with minimal latency.
"""
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class Frame:
    """Represents a sampled frame from video source."""

    def __init__(
        self,
        frame_id: int,
        timestamp: str,
        image: np.ndarray,
        source_name: str,
    ):
        self.frame_id = frame_id
        self.timestamp = timestamp  # ISO format
        self.image = image  # BGR numpy array (H, W, 3)
        self.source_name = source_name
        self.height, self.width = image.shape[:2]

    def __repr__(self):
        return f"<Frame {self.frame_id} [{self.width}x{self.height}] @ {self.source_name}>"


class FrameBuffer:
    """Thread-safe queue for sampled frames."""

    def __init__(self, max_size: int = 30):
        self.queue = Queue(maxsize=max_size)
        self.max_size = max_size

    def put(self, frame: Frame, timeout: float = 1.0):
        """Add frame to buffer."""
        try:
            self.queue.put(frame, timeout=timeout)
        except Exception as e:
            logger.warning(f"Frame buffer full, dropping frame {frame.frame_id}: {e}")

    def get(self, timeout: float = 1.0) -> Optional[Frame]:
        """Get next frame from buffer."""
        try:
            return self.queue.get(timeout=timeout)
        except:
            return None

    def size(self) -> int:
        """Get current buffer size."""
        return self.queue.qsize()


class VideoIngestionService:
    """
    Ingests video from file or webcam with frame sampling.
    Runs in background thread, outputs frames at configurable FPS.
    """

    def __init__(
        self,
        source: str,
        target_fps: int = 2,
        source_name: str = "default",
    ):
        """
        Initialize video ingestion service.

        Args:
            source: File path, URL, or "0" for webcam
            target_fps: Target sampling rate (frames per second)
            source_name: Human-readable source identifier
        """
        self.source = source
        self.target_fps = target_fps
        self.source_name = source_name
        self.frame_interval = 1.0 / target_fps  # seconds between frames

        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.frame_buffer = FrameBuffer(max_size=30)

        self.frame_count = 0
        self.drop_count = 0
        self.total_frames_read = 0

    def start(self):
        """Start the ingestion thread."""
        if self.running:
            logger.warning("Video ingestion already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._ingestion_loop, daemon=True)
        self.thread.start()
        logger.info(
            f"Video ingestion started: {self.source} @ {self.target_fps} FPS "
            f"({self.frame_interval:.3f}s per frame)"
        )

    def stop(self):
        """Stop the ingestion thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info(f"Video ingestion stopped: {self.source_name}")
        self._log_stats()

    def get_frame(self, timeout: float = 2.0) -> Optional[Frame]:
        """Get next frame from buffer."""
        return self.frame_buffer.get(timeout=timeout)

    def _ingestion_loop(self):
        """Main ingestion loop (runs in background thread)."""
        cap = None
        try:
            # Open video source
            cap = self._open_source()
            if cap is None:
                logger.error(f"Failed to open video source: {self.source}")
                return

            logger.info(f"Video source opened: {self.source_name}")

            # Get source FPS (for file sources)
            source_fps = cap.get(cv2.CAP_PROP_FPS)
            if source_fps > 0:
                logger.info(f"Source FPS: {source_fps:.1f}")

            last_frame_time = time.time()

            while self.running:
                ret, frame = cap.read()
                self.total_frames_read += 1

                if not ret:
                    # End of video file or camera disconnected
                    logger.warning(f"End of stream or camera disconnected: {self.source}")
                    break

                # Check if enough time has passed for next sampled frame
                current_time = time.time()
                time_since_last = current_time - last_frame_time

                if time_since_last >= self.frame_interval:
                    # Yield this frame
                    frame_obj = Frame(
                        frame_id=self.frame_count,
                        timestamp=datetime.utcnow().isoformat(),
                        image=frame,
                        source_name=self.source_name,
                    )

                    self.frame_buffer.put(frame_obj)
                    self.frame_count += 1
                    last_frame_time = current_time

                    logger.debug(
                        f"Frame {self.frame_count} sampled "
                        f"({frame.shape[1]}x{frame.shape[0]})"
                    )
                else:
                    # Skip this frame
                    self.drop_count += 1

        except Exception as e:
            logger.error(f"Error in ingestion loop: {e}")
        finally:
            if cap:
                cap.release()
                logger.info(f"Video source released: {self.source_name}")

    def _open_source(self) -> Optional[cv2.VideoCapture]:
        """Open video source (file or webcam)."""
        try:
            # Try to open as integer (webcam)
            if self.source.isdigit():
                cap = cv2.VideoCapture(int(self.source))
                if cap.isOpened():
                    return cap
                logger.error(f"Failed to open webcam {self.source}")
                return None

            # Try to open as file
            if Path(self.source).exists():
                cap = cv2.VideoCapture(self.source)
                if cap.isOpened():
                    return cap
                logger.error(f"File exists but cannot open: {self.source}")
                return None

            # Try to open as URL (RTSP, HTTP, etc.)
            cap = cv2.VideoCapture(self.source)
            if cap.isOpened():
                return cap

            logger.error(f"Cannot open video source: {self.source}")
            return None

        except Exception as e:
            logger.error(f"Exception opening video source: {e}")
            return None

    def _log_stats(self):
        """Log ingestion statistics."""
        total_sampled = self.frame_count
        total_dropped = self.drop_count
        pct_dropped = (total_dropped / max(self.total_frames_read, 1)) * 100

        logger.info(
            f"Ingestion stats for {self.source_name}: "
            f"read={self.total_frames_read}, sampled={total_sampled}, "
            f"dropped={total_dropped} ({pct_dropped:.1f}%)"
        )
