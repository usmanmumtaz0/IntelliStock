"""
YOLO Detection Service (CV-002)
Performs object detection on frames using YOLOv8.
Filters detections by confidence threshold.
"""
import logging
from typing import List, Optional, Tuple

import numpy as np
from ultralytics import YOLO

logger = logging.getLogger(__name__)


class Detection:
    """Represents a single object detection."""

    def __init__(
        self,
        class_id: int,
        class_name: str,
        confidence: float,
        bbox: Tuple[float, float, float, float],  # (x1, y1, x2, y2) normalized [0, 1]
    ):
        self.class_id = class_id
        self.class_name = class_name
        self.confidence = confidence
        self.bbox = bbox
        self.x1, self.y1, self.x2, self.y2 = bbox

    def area(self) -> float:
        """Bounding box area (normalized)."""
        return (self.x2 - self.x1) * (self.y2 - self.y1)

    def center(self) -> Tuple[float, float]:
        """Bounding box center (normalized)."""
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    def __repr__(self):
        return (
            f"<Detection {self.class_name} conf={self.confidence:.2f} "
            f"bbox=({self.x1:.2f}, {self.y1:.2f}, {self.x2:.2f}, {self.y2:.2f})>"
        )


class YOLODetector:
    """
    YOLO object detector wrapper.
    Performs detection on frames and returns filtered detections.
    """

    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        confidence_threshold: float = 0.5,
        device: str = "cpu",
    ):
        """
        Initialize YOLO detector.

        Args:
            model_name: Model to load (e.g., 'yolov8n.pt', 'yolov8s.pt')
            confidence_threshold: Minimum confidence to include detection
            device: Device to run inference on ('cpu', 'cuda:0', etc.)
        """
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.device = device

        logger.info(f"Loading YOLO model: {model_name} on {device}")
        self.model = YOLO(model_name)
        self.model.to(device)
        logger.info(f"YOLO model loaded successfully")

        self.inference_count = 0
        self.total_detections = 0

    def detect(self, image: np.ndarray) -> List[Detection]:
        """
        Detect objects in frame.

        Args:
            image: Input image (BGR numpy array)

        Returns:
            List of Detection objects (normalized coordinates)
        """
        try:
            # Run inference
            results = self.model(image, verbose=False, conf=self.confidence_threshold)
            self.inference_count += 1

            detections = []

            # Extract detections from results
            if len(results) > 0 and results[0].boxes is not None:
                boxes = results[0].boxes
                img_h, img_w = image.shape[:2]

                for box in boxes:
                    # Get bounding box coordinates (in pixels)
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0].cpu().numpy())
                    cls_id = int(box.cls[0].cpu().numpy())

                    # Skip if confidence below threshold
                    if conf < self.confidence_threshold:
                        continue

                    # Normalize coordinates to [0, 1]
                    norm_x1 = x1 / img_w
                    norm_y1 = y1 / img_h
                    norm_x2 = x2 / img_w
                    norm_y2 = y2 / img_h

                    # Get class name
                    class_name = self.model.names.get(cls_id, f"class_{cls_id}")

                    detection = Detection(
                        class_id=cls_id,
                        class_name=class_name,
                        confidence=conf,
                        bbox=(norm_x1, norm_y1, norm_x2, norm_y2),
                    )
                    detections.append(detection)

            self.total_detections += len(detections)

            logger.debug(
                f"Inference #{self.inference_count}: {len(detections)} detections "
                f"(threshold={self.confidence_threshold})"
            )

            return detections

        except Exception as e:
            logger.error(f"YOLO detection error: {e}")
            return []

    def get_stats(self) -> dict:
        """Get detector statistics."""
        avg_detections = (
            self.total_detections / self.inference_count
            if self.inference_count > 0
            else 0
        )
        return {
            "inference_count": self.inference_count,
            "total_detections": self.total_detections,
            "avg_detections_per_frame": avg_detections,
        }
