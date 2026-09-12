"""
Video Ingestion Service (CV-001)
Handles video input (file or webcam) and frame sampling at configurable FPS.
"""
import logging
import time
from pathlib import Path
from typing import Optional, Tuple
from collections import deque

import cv2
import numpy as np

from config import DEFAULT_FPS, VIDEO_SOURCE, REPLAY_MODE

logger = logging.getLogger(__name__)


class FrameSampler:
    """Samples frames from video at target FPS."""
    
    def __init__(self, target_fps: int = DEFAULT_FPS):
        """
        Initialize frame sampler.
        
        Args:
            target_fps: Target frames per second for sampling
        """
        self.target_fps = target_fps
        self.frame_interval_ms = 1000.0 / target_fps  # Milliseconds between frames
        self.last_frame_time = 0
        self.frames_sampled = 0
        self.frames_skipped = 0
    
    def should_sample(self, current_frame_ms: float) -> bool:
        """Check if current frame should be sampled based on FPS target."""
        time_since_last = current_frame_ms - self.last_frame_time
        
        if time_since_last >= self.frame_interval_ms:
            self.last_frame_time = current_frame_ms
            self.frames_sampled += 1
            return True
        
        self.frames_skipped += 1
        return False
    
    def get_stats(self) -> dict:
        """Get sampling statistics."""
        total_frames = self.frames_sampled + self.frames_skipped
        skip_rate = (self.frames_skipped / total_frames * 100) if total_frames > 0 else 0
        return {
            "sampled": self.frames_sampled,
            "skipped": self.frames_skipped,
            "total": total_frames,
            "skip_rate": f"{skip_rate:.1f}%",
            "target_fps": self.target_fps,
        }


class VideoIngestionService:
    """Handles video input from file or webcam with frame sampling."""
    
    def __init__(
        self,
        source: str = VIDEO_SOURCE,
        target_fps: int = DEFAULT_FPS,
        replay_mode: bool = REPLAY_MODE,
    ):
        """
        Initialize video ingestion service.
        
        Args:
            source: Video source ("0" for webcam, path to file, or RTSP URL)
            target_fps: Target frames per second for sampling
            replay_mode: If True, restart video when finished
        """
        self.source = source
        self.target_fps = target_fps
        self.replay_mode = replay_mode
        self.sampler = FrameSampler(target_fps)
        
        self.cap = None
        self.is_open = False
        self.total_frames = 0
        self.fps_actual = 0
        self.frame_width = 0
        self.frame_height = 0
        self.current_frame_idx = 0
        
        # Performance tracking
        self.frame_read_times = deque(maxlen=100)
    
    def open(self) -> bool:
        """
        Open video source (file or webcam).
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Determine if source is webcam or file
            source_id = self._parse_source()
            
            self.cap = cv2.VideoCapture(source_id)
            
            if not self.cap.isOpened():
                logger.error(f"Failed to open video source: {self.source}")
                return False
            
            # Get video properties
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps_actual = self.cap.get(cv2.CAP_PROP_FPS)
            self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            self.is_open = True
            logger.info(
                f"Video source opened: {self.source} "
                f"({self.frame_width}x{self.frame_height}, {self.fps_actual:.1f} FPS, "
                f"{self.total_frames} frames)"
            )
            
            return True
        except Exception as e:
            logger.error(f"Error opening video source: {e}")
            return False
    
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray], float]:
        """
        Read next frame from video, applying FPS sampling.
        
        Returns:
            Tuple of (success: bool, frame: np.ndarray, timestamp_ms: float)
        """
        if not self.is_open:
            return False, None, 0.0
        
        try:
            ret, frame = self.cap.read()
            
            if not ret:
                # End of video
                if self.replay_mode:
                    logger.info("End of video reached, replaying...")
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    self.current_frame_idx = 0
                    self.sampler.frames_sampled = 0
                    self.sampler.frames_skipped = 0
                    ret, frame = self.cap.read()
                
                if not ret:
                    return False, None, 0.0
            
            # Calculate frame timestamp
            self.current_frame_idx = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            timestamp_ms = (self.current_frame_idx / self.fps_actual * 1000) if self.fps_actual > 0 else 0
            
            # Check if frame should be sampled
            if self.sampler.should_sample(timestamp_ms):
                return True, frame, timestamp_ms
            
            return False, None, 0.0
        
        except Exception as e:
            logger.error(f"Error reading frame: {e}")
            return False, None, 0.0
    
    def get_frame_batch(self, batch_size: int = 1) -> list:
        """
        Read multiple frames, only returning sampled frames.
        
        Args:
            batch_size: Maximum number of sampled frames to return
        
        Returns:
            List of (frame, timestamp_ms) tuples
        """
        batch = []
        
        while len(batch) < batch_size:
            success, frame, timestamp_ms = self.read_frame()
            
            if not success:
                break
            
            batch.append((frame, timestamp_ms))
            
            # Track frame read time
            read_time = time.time()
            self.frame_read_times.append(read_time)
        
        return batch
    
    def get_stats(self) -> dict:
        """Get ingestion statistics."""
        avg_read_time = 0
        if self.frame_read_times:
            times = list(self.frame_read_times)
            avg_read_time = sum(times[i+1] - times[i] for i in range(len(times)-1)) / (len(times)-1) if len(times) > 1 else 0
        
        return {
            "source": self.source,
            "is_open": self.is_open,
            "resolution": f"{self.frame_width}x{self.frame_height}",
            "fps_actual": f"{self.fps_actual:.1f}",
            "total_frames": self.total_frames,
            "current_frame": self.current_frame_idx,
            "target_fps": self.target_fps,
            "avg_read_time_ms": f"{avg_read_time*1000:.2f}",
            "sampler": self.sampler.get_stats(),
        }
    
    def close(self):
        """Close video source."""
        if self.cap:
            self.cap.release()
            self.is_open = False
            logger.info(f"Video source closed. Stats: {self.get_stats()}")
    
    def _parse_source(self) -> int | str:
        """Parse video source (webcam index or file path)."""
        # Try to parse as webcam index
        try:
            return int(self.source)
        except ValueError:
            # It's a file path or RTSP URL
            if not Path(self.source).exists() and not self.source.startswith(("rtsp://", "http://")):
                raise FileNotFoundError(f"Video file not found: {self.source}")
            return self.source
