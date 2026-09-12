"""
CV Pipeline Orchestrator
Coordinates video ingestion, detection, tracking, and ROI assignment.
"""
import logging
from typing import List, Dict, Optional, Tuple

import numpy as np

from video_ingestion import VideoIngestionService, FrameSampler
from yolo_detector import YOLODetector, Detection, draw_detections
from byte_tracker import ByteTracker, Track
from roi_assignment import ROIAssigner, ShelfZone

logger = logging.getLogger(__name__)


class Observation:
    """Represents a reconciliation observation from CV pipeline."""
    
    def __init__(
        self,
        zone_id: str,
        product_id: str,
        quantity: int,
        confidence: float,
        camera_id: str,
        frame_idx: int,
        track_ids: List[int],
    ):
        """
        Initialize observation.
        
        Args:
            zone_id: Shelf zone UUID
            product_id: Product UUID
            quantity: Detected/tracked quantity in zone
            confidence: Average detection confidence
            camera_id: Camera UUID
            frame_idx: Frame number
            track_ids: List of track IDs contributing to quantity
        """
        self.zone_id = zone_id
        self.product_id = product_id
        self.quantity = quantity
        self.confidence = confidence
        self.camera_id = camera_id
        self.frame_idx = frame_idx
        self.track_ids = track_ids
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "zone_id": self.zone_id,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "confidence": float(self.confidence),
            "camera_id": self.camera_id,
            "frame_idx": self.frame_idx,
            "track_ids": self.track_ids,
        }


class CVPipeline:
    """Full CV pipeline: ingestion → detection → tracking → ROI assignment."""
    
    def __init__(
        self,
        camera_id: str,
        product_class_id: int = 0,
        video_source: str = "0",
        target_fps: int = 2,
    ):
        """
        Initialize CV pipeline.
        
        Args:
            camera_id: UUID of camera
            product_class_id: YOLO class ID to track (e.g., 0 for person)
            video_source: Video source (webcam index, file path, RTSP URL)
            target_fps: Target frame sampling rate
        """
        self.camera_id = camera_id
        self.product_class_id = product_class_id
        
        # Initialize components
        self.ingestion = VideoIngestionService(source=video_source, target_fps=target_fps)
        self.detector = YOLODetector()
        self.tracker = ByteTracker()
        self.roi_assigner = ROIAssigner()
        
        # State
        self.is_running = False
        self.frame_count = 0
        self.observations_generated = 0
    
    def add_zone(self, zone_id: str, name: str, roi_polygon_json: str):
        """Add a shelf zone to the pipeline."""
        self.roi_assigner.add_zone(zone_id, name, roi_polygon_json)
    
    def process_frame(self) -> Tuple[bool, Optional[List[Observation]], Optional[np.ndarray]]:
        """
        Process single frame through pipeline.
        
        Returns:
            Tuple of (success: bool, observations: List[Observation], debug_frame: np.ndarray)
        """
        # Step 1: Ingest frame
        success, frame, timestamp_ms = self.ingestion.read_frame()
        if not success or frame is None:
            return False, None, None
        
        self.frame_count += 1
        
        # Step 2: Detect objects
        detections = self.detector.detect(frame)
        
        # Filter by product class
        product_detections = [d for d in detections if d.class_id == self.product_class_id]
        
        if not product_detections:
            logger.debug(f"Frame {self.frame_count}: no detections for class {self.product_class_id}")
            return True, [], frame
        
        # Step 3: Track objects
        confirmed_tracks = self.tracker.update(product_detections, frame_idx=self.frame_count)
        
        # Step 4: Assign to zones
        zone_assignments = self.roi_assigner.get_assignments_by_zone(list(confirmed_tracks.values()))
        
        # Step 5: Generate observations
        observations = []
        
        for zone_id, zone_detections in zone_assignments.items():
            if not zone_detections:
                continue
            
            # Calculate quantity and average confidence
            quantity = len(zone_detections)
            avg_confidence = np.mean([d.confidence for d in zone_detections])
            track_ids = []  # TODO: track IDs from confirmed_tracks
            
            obs = Observation(
                zone_id=zone_id,
                product_id="generic-product",  # TODO: map class_id to product_id
                quantity=quantity,
                confidence=avg_confidence,
                camera_id=self.camera_id,
                frame_idx=self.frame_count,
                track_ids=track_ids,
            )
            observations.append(obs)
            self.observations_generated += 1
        
        # Debug frame with detections drawn
        debug_frame = draw_detections(frame, product_detections)
        
        return True, observations, debug_frame
    
    def start(self) -> bool:
        """Start the pipeline."""
        if self.ingestion.open():
            self.is_running = True
            logger.info("CV Pipeline started")
            return True
        
        logger.error("Failed to start CV Pipeline")
        return False
    
    def stop(self):
        """Stop the pipeline."""
        self.ingestion.close()
        self.is_running = False
        logger.info("CV Pipeline stopped")
    
    def run_batch(self, batch_size: int = 10) -> List[Observation]:
        """
        Process a batch of frames.
        
        Args:
            batch_size: Number of frames to process
        
        Returns:
            List of all observations generated
        """
        all_observations = []
        
        for _ in range(batch_size):
            success, observations, debug_frame = self.process_frame()
            
            if not success:
                break
            
            if observations:
                all_observations.extend(observations)
        
        return all_observations
    
    def get_stats(self) -> dict:
        """Get pipeline statistics."""
        return {
            "camera_id": self.camera_id,
            "is_running": self.is_running,
            "frame_count": self.frame_count,
            "observations_generated": self.observations_generated,
            "ingestion": self.ingestion.get_stats(),
            "detector": self.detector.get_stats(),
            "tracker": self.tracker.get_stats(),
            "roi_assigner": self.roi_assigner.get_stats(),
        }
