"""
ByteTrack Integration Service (CV-003)
Tracks detected objects across frames using ByteTrack.
"""
import logging
from typing import List, Tuple, Dict, Optional

import numpy as np
from bytetrack import BYTETracker

from config import BYTETRACK_MIN_TRACK_LENGTH, BYTETRACK_TRACK_BUFFER, BYTETRACK_MATCH_THRESHOLD
from yolo_detector import Detection

logger = logging.getLogger(__name__)


class Track:
    """Represents a tracked object across frames."""
    
    def __init__(self, track_id: int, detections: List[Detection]):
        """
        Initialize track.
        
        Args:
            track_id: Unique track ID
            detections: Initial list of detections for this track
        """
        self.track_id = track_id
        self.detections = detections
        self.first_frame_idx = 0
        self.last_frame_idx = 0
        self.is_confirmed = False
    
    @property
    def length(self) -> int:
        """Number of detections in this track."""
        return len(self.detections)
    
    @property
    def latest_detection(self) -> Optional[Detection]:
        """Most recent detection in this track."""
        return self.detections[-1] if self.detections else None
    
    def add_detection(self, detection: Detection):
        """Add a detection to this track."""
        self.detections.append(detection)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        latest = self.latest_detection
        return {
            "track_id": self.track_id,
            "length": self.length,
            "is_confirmed": self.is_confirmed,
            "latest_detection": latest.to_dict() if latest else None,
            "detections_count": len(self.detections),
        }


class ByteTracker:
    """ByteTrack-based object tracking."""
    
    def __init__(
        self,
        min_track_length: int = BYTETRACK_MIN_TRACK_LENGTH,
        track_buffer: int = BYTETRACK_TRACK_BUFFER,
        match_threshold: float = BYTETRACK_MATCH_THRESHOLD,
    ):
        """
        Initialize ByteTracker.
        
        Args:
            min_track_length: Minimum detections to confirm a track
            track_buffer: Buffer size for unmatched tracks (frames)
            match_threshold: IoU threshold for matching
        """
        self.min_track_length = min_track_length
        self.track_buffer = track_buffer
        self.match_threshold = match_threshold
        
        # ByteTrack tracker
        self.tracker = BYTETracker(
            track_thresh=match_threshold,
            track_buffer=track_buffer,
            match_thresh=match_threshold,
            frame_rate=2,  # FPS for ByteTrack (not critical)
        )
        
        # Track management
        self.active_tracks: Dict[int, Track] = {}
        self.finished_tracks: List[Track] = []
        self.frame_count = 0
        self.total_detections = 0
        self.total_tracks = 0
    
    def update(self, detections: List[Detection], frame_idx: int) -> Dict[int, Detection]:
        """
        Update tracker with new detections.
        
        Args:
            detections: List of Detection objects from YOLO
            frame_idx: Current frame index
        
        Returns:
            Dict mapping track_id -> Detection for confirmed tracks
        """
        self.frame_count += 1
        self.total_detections += len(detections)
        
        # Convert detections to ByteTrack format
        # ByteTrack expects [[x1, y1, x2, y2, confidence], ...]
        dets = np.array([
            [det.x1, det.y1, det.x2, det.y2, det.confidence]
            for det in detections
        ], dtype=np.float32)
        
        if len(dets) == 0:
            dets = np.empty((0, 5), dtype=np.float32)
        
        # Get tracked objects from ByteTrack
        online_targets = self.tracker.update(dets, img_info=(720, 1280), img_size=(720, 1280))
        
        # Update tracks
        confirmed_tracks = {}
        
        for target in online_targets:
            track_id = int(target.track_id)
            
            # Create Detection from ByteTrack output
            x1, y1, x2, y2 = target.tlbr
            det = detections[0]  # Use first detection's class info (simplified)
            
            # Find matching detection for class/confidence info
            for d in detections:
                if (d.x1 <= x1 <= d.x2 and d.y1 <= y1 <= d.y2):
                    det = d
                    break
            
            # Track or create
            if track_id not in self.active_tracks:
                track = Track(track_id, [det])
                track.first_frame_idx = frame_idx
                self.active_tracks[track_id] = track
                self.total_tracks += 1
            else:
                track = self.active_tracks[track_id]
                track.add_detection(det)
            
            track.last_frame_idx = frame_idx
            
            # Check if track is confirmed (enough detections)
            if track.length >= self.min_track_length and not track.is_confirmed:
                track.is_confirmed = True
                logger.debug(f"Track {track_id} confirmed after {track.length} frames")
            
            # Add to confirmed output if confirmed
            if track.is_confirmed:
                confirmed_tracks[track_id] = det
        
        # Move inactive tracks to finished
        frame_threshold = frame_idx - self.track_buffer
        for track_id in list(self.active_tracks.keys()):
            track = self.active_tracks[track_id]
            if track.last_frame_idx < frame_threshold:
                self.finished_tracks.append(track)
                del self.active_tracks[track_id]
        
        return confirmed_tracks
    
    def get_active_tracks(self) -> Dict[int, Track]:
        """Get all active tracks."""
        return self.active_tracks.copy()
    
    def get_finished_tracks(self) -> List[Track]:
        """Get all finished tracks."""
        return self.finished_tracks.copy()
    
    def get_stats(self) -> dict:
        """Get tracker statistics."""
        return {
            "frame_count": self.frame_count,
            "active_tracks": len(self.active_tracks),
            "finished_tracks": len(self.finished_tracks),
            "total_tracks": self.total_tracks,
            "total_detections": self.total_detections,
            "min_track_length": self.min_track_length,
            "track_buffer": self.track_buffer,
        }


def calculate_iou(box1: Tuple, box2: Tuple) -> float:
    """
    Calculate Intersection over Union between two boxes.
    
    Args:
        box1, box2: (x1, y1, x2, y2)
    
    Returns:
        IoU value (0-1)
    """
    x1_min, y1_min, x1_max, y1_max = box1
    x2_min, y2_min, x2_max, y2_max = box2
    
    # Calculate intersection
    inter_x_min = max(x1_min, x2_min)
    inter_y_min = max(y1_min, y2_min)
    inter_x_max = min(x1_max, x2_max)
    inter_y_max = min(y1_max, y2_max)
    
    if inter_x_max < inter_x_min or inter_y_max < inter_y_min:
        return 0.0
    
    inter_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)
    
    # Calculate union
    box1_area = (x1_max - x1_min) * (y1_max - y1_min)
    box2_area = (x2_max - x2_min) * (y2_max - y2_min)
    union_area = box1_area + box2_area - inter_area
    
    return inter_area / union_area if union_area > 0 else 0.0
