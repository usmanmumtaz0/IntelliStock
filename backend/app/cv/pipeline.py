"""
Computer Vision Pipeline
Orchestrates video ingestion, detection, tracking, ROI assignment, and observation building.
"""
import logging
from typing import List, Optional, Dict

from app.cv.ingestion import VideoIngestionService, Frame
from app.cv.detection import YOLODetector
from app.cv.tracking import ByteTrackWrapper
from app.cv.roi_assignment import ROIAssigner, ZoneAssignment
from app.cv.observation_builder import ObservationBuilder, RawObservation

logger = logging.getLogger(__name__)


class CVPipeline:
    """
    Complete CV pipeline: Ingestion → Detection → Tracking → ROI Assignment → Observations
    """

    def __init__(
        self,
        video_source: str,
        camera_id: str,
        target_fps: int = 2,
        yolo_model: str = "yolov8n.pt",
        confidence_threshold: float = 0.5,
        device: str = "cpu",
    ):
        """
        Initialize CV pipeline.

        Args:
            video_source: File path, URL, or webcam number
            camera_id: Camera identifier (UUID)
            target_fps: Target sampling rate
            yolo_model: YOLO model name
            confidence_threshold: Detection confidence threshold
            device: Inference device ('cpu' or 'cuda:0')
        """
        self.video_source = video_source
        self.camera_id = camera_id
        self.device = device

        # Initialize pipeline stages
        self.ingestion = VideoIngestionService(
            source=video_source,
            target_fps=target_fps,
            source_name=f"camera_{camera_id[:8]}",
        )

        self.detector = YOLODetector(
            model_name=yolo_model,
            confidence_threshold=confidence_threshold,
            device=device,
        )

        self.tracker = ByteTrackWrapper(model_name=yolo_model, device=device)

        self.roi_assigner = ROIAssigner()

        self.observation_builder = ObservationBuilder()

        self.running = False
        self.frame_count = 0

        logger.info(f"CV Pipeline initialized: {camera_id} @ {target_fps} FPS")

    def register_zone(self, zone_id: str, zone_name: str, roi_polygon_json: str):
        """Register a shelf zone with ROI polygon."""
        return self.roi_assigner.add_zone(zone_id, zone_name, roi_polygon_json)

    def start(self):
        """Start the pipeline."""
        self.ingestion.start()
        self.running = True
        logger.info("CV Pipeline started")

    def stop(self):
        """Stop the pipeline."""
        self.running = False
        self.ingestion.stop()
        logger.info("CV Pipeline stopped")

    def process_frame(self) -> Optional[List[RawObservation]]:
        """
        Process next frame through entire pipeline.

        Returns:
            List of RawObservation, or None if no frame available
        """
        # Get frame from ingestion
        frame: Optional[Frame] = self.ingestion.get_frame(timeout=1.0)
        if frame is None:
            return None

        try:
            # Detect objects
            detections = self.detector.detect(frame.image)

            # Track objects
            tracked_objects = self.tracker.update(detections, self.frame_count)

            # Assign to zones
            assignments = self.roi_assigner.assign_tracked_objects(tracked_objects)

            # Build observations
            observations = self.observation_builder.build_observation(
                frame_id=frame.frame_id,
                camera_id=self.camera_id,
                timestamp=frame.timestamp,
                assignments=assignments,
                tracked_objects=tracked_objects,
            )

            self.frame_count += 1
            return observations

        except Exception as e:
            logger.error(f"Error processing frame {frame.frame_id}: {e}")
            return None

    def get_statistics(self) -> Dict:
        """Get pipeline statistics."""
        return {
            "camera_id": self.camera_id,
            "frames_processed": self.frame_count,
            "detector": self.detector.get_stats(),
            "observer": self.observation_builder.get_stats(),
        }
