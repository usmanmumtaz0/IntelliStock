"""
ByteTrack Integration (CV-003)
Assigns persistent track IDs to detections across frames.
Handles object tracking for inventory counting.
"""
import logging
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Try to import ByteTrack, fallback to simple tracker if not available
try:
    from yolo_tracking import YOLO
    HAS_BYTETRACK = True
except ImportError:
    HAS_BYTETRACK = False
    logger.warning("ByteTrack not available, will use simple centroid tracker")


@dataclass
class TrackedObject:
    """Represents a tracked object across frames."""

    track_id: int
    class_id: int
    class_name: str
    confidence: float
    bbox: tuple  # (x1, y1, x2, y2) normalized
    age: int  # Number of frames this track has existed
    hits: int  # Number of consecutive frames detected


class SimpleCentroidTracker:
    """
    Simple centroid-based tracker as fallback when ByteTrack unavailable.
    Suitable for shelf inventory MVP where speed > accuracy.
    """

    def __init__(self, max_distance: float = 0.1, max_disappeared: int = 5):
        """
        Initialize tracker.

        Args:
            max_distance: Max normalized distance to match centroids
            max_disappeared: Frames to keep track alive without detection
        """
        self.max_distance = max_distance
        self.max_disappeared = max_disappeared
        self.next_track_id = 0
        self.tracks = {}  # track_id -> TrackedObject
        self.disappeared = {}  # track_id -> frames_since_seen

    def update(
        self,
        detections: List,  # List of Detection objects
        frame_id: int,
    ) -> List[TrackedObject]:
        """
        Update tracks with new detections.

        Args:
            detections: List of Detection objects from YOLO
            frame_id: Current frame number

        Returns:
            List of TrackedObject with track IDs
        """
        if len(detections) == 0:
            # No detections, age existing tracks
            tracked = []
            for track_id, track in list(self.tracks.items()):
                self.disappeared[track_id] += 1
                if self.disappeared[track_id] > self.max_disappeared:
                    del self.tracks[track_id]
                    del self.disappeared[track_id]
                else:
                    tracked.append(track)
            return tracked

        # Match detections to existing tracks by centroid distance
        detection_centroids = [d.center() for d in detections]
        track_ids = list(self.tracks.keys())
        track_centroids = [self.tracks[tid].bbox for tid in track_ids]

        matched_track_ids = set()
        matched_detection_ids = set()

        for det_idx, det_centroid in enumerate(detection_centroids):
            best_track_id = None
            best_distance = self.max_distance

            for track_idx, track_id in enumerate(track_ids):
                track_bbox = track_centroids[track_idx]
                track_centroid = (
                    (track_bbox[0] + track_bbox[2]) / 2,
                    (track_bbox[1] + track_bbox[3]) / 2,
                )

                # Euclidean distance in normalized space
                distance = np.sqrt(
                    (det_centroid[0] - track_centroid[0]) ** 2
                    + (det_centroid[1] - track_centroid[1]) ** 2
                )

                if distance < best_distance:
                    best_distance = distance
                    best_track_id = track_id

            if best_track_id is not None:
                # Match found
                matched_track_ids.add(best_track_id)
                matched_detection_ids.add(det_idx)

                det = detections[det_idx]
                track = self.tracks[best_track_id]
                track.bbox = det.bbox
                track.confidence = det.confidence
                track.hits += 1
                track.age += 1
                self.disappeared[best_track_id] = 0

        # Create new tracks for unmatched detections
        for det_idx, detection in enumerate(detections):
            if det_idx not in matched_detection_ids:
                track = TrackedObject(
                    track_id=self.next_track_id,
                    class_id=detection.class_id,
                    class_name=detection.class_name,
                    confidence=detection.confidence,
                    bbox=detection.bbox,
                    age=1,
                    hits=1,
                )
                self.tracks[self.next_track_id] = track
                self.disappeared[self.next_track_id] = 0
                self.next_track_id += 1

        # Remove disappeared tracks
        for track_id in list(self.tracks.keys()):
            if track_id not in matched_track_ids:
                self.disappeared[track_id] += 1
                if self.disappeared[track_id] > self.max_disappeared:
                    del self.tracks[track_id]
                    del self.disappeared[track_id]

        # Return all active tracks
        return list(self.tracks.values())

    def reset(self):
        """Reset tracker state."""
        self.tracks.clear()
        self.disappeared.clear()
        self.next_track_id = 0


class ByteTrackWrapper:
    """
    Wrapper for ByteTrack tracker.
    Uses YOLOv8 with ByteTrack integration from ultralytics.
    """

    def __init__(self, model_name: str = "yolov8n.pt", device: str = "cpu"):
        """
        Initialize ByteTrack wrapper.

        Args:
            model_name: YOLO model name
            device: Device for inference
        """
        if not HAS_BYTETRACK:
            logger.warning(
                "ByteTrack not installed, falling back to centroid tracker. "
                "Install with: pip install ultralytics-yolo-tracking"
            )
            self.tracker = SimpleCentroidTracker()
            self.use_centroid = True
        else:
            self.model_name = model_name
            self.device = device
            self.model = YOLO(model_name)
            self.model.to(device)
            self.use_centroid = False
            logger.info("ByteTrack initialized")

    def update(self, detections: List, frame_id: int) -> List[TrackedObject]:
        """
        Update tracks with detections.

        Args:
            detections: List of Detection objects
            frame_id: Current frame number

        Returns:
            List of TrackedObject with track IDs
        """
        if self.use_centroid:
            return self.tracker.update(detections, frame_id)

        # ByteTrack update logic (future implementation)
        # For now, fallback to centroid
        return self.tracker.update(detections, frame_id)

    def reset(self):
        """Reset tracker."""
        if self.use_centroid:
            self.tracker.reset()
