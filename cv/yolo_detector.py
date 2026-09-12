"""
YOLO Detection Service (CV-002)
Performs object detection using YOLOv8 with confidence filtering.
"""
import logging
from typing import List, Tuple, Optional
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from config import YOLO_MODEL, YOLO_CONFIDENCE_THRESHOLD, YOLO_DEVICE, MODEL_DIR

logger = logging.getLogger(__name__)


class Detection:
    """Represents a single object detection."""
    
    def __init__(
        self,
        class_id: int,
        class_name: str,
        confidence: float,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ):
        """
        Initialize detection.
        
        Args:
            class_id: COCO class ID
            class_name: Class name
            confidence: Detection confidence (0-1)
            x1, y1, x2, y2: Bounding box coordinates (pixels)
        """
        self.class_id = class_id
        self.class_name = class_name
        self.confidence = confidence
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
    
    @property
    def bbox(self) -> Tuple[float, float, float, float]:
        """Get bounding box as (x1, y1, x2, y2)."""
        return (self.x1, self.y1, self.x2, self.y2)
    
    @property
    def center(self) -> Tuple[float, float]:
        """Get bounding box center (cx, cy)."""
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)
    
    @property
    def width(self) -> float:
        """Get bounding box width."""
        return self.x2 - self.x1
    
    @property
    def height(self) -> float:
        """Get bounding box height."""
        return self.y2 - self.y1
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": float(self.confidence),
            "bbox": self.bbox,
            "center": self.center,
            "width": float(self.width),
            "height": float(self.height),
        }
    
    def __repr__(self):
        return f"<Detection {self.class_name} conf={self.confidence:.2f} bbox=({self.x1:.0f},{self.y1:.0f},{self.x2:.0f},{self.y2:.0f})>"


class YOLODetector:
    """YOLO object detection service."""
    
    def __init__(
        self,
        model_name: str = YOLO_MODEL,
        confidence_threshold: float = YOLO_CONFIDENCE_THRESHOLD,
        device: str = YOLO_DEVICE,
    ):
        """
        Initialize YOLO detector.
        
        Args:
            model_name: YOLOv8 model name (n, s, m, l, x)
            confidence_threshold: Minimum confidence to keep detections
            device: Device to run on ('cpu', 'cuda', '0', etc.)
        """
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.device = device
        self.model = None
        self.detections_processed = 0
        
        self._load_model()
    
    def _load_model(self):
        """Load YOLO model."""
        try:
            logger.info(f"Loading YOLO model: {self.model_name} on device {self.device}...")
            self.model = YOLO(self.model_name)
            
            # Set device
            _ = self.model.predict(np.zeros((1, 640, 640, 3)), device=self.device, verbose=False)
            
            logger.info(f"YOLO model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise
    
    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Detect objects in frame.
        
        Args:
            frame: Input frame (BGR)
        
        Returns:
            List of Detection objects
        """
        if self.model is None:
            logger.error("Model not loaded")
            return []
        
        try:
            # Run detection (verbose=False to reduce logging)
            results = self.model.predict(frame, device=self.device, verbose=False, conf=self.confidence_threshold)
            
            detections = []
            
            for result in results:
                # Each result is a Results object
                for box in result.boxes:
                    # Extract box information
                    xyxy = box.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2]
                    confidence = box.conf[0].item()
                    class_id = int(box.cls[0].item())
                    
                    # Get class name from COCO names
                    class_name = result.names[class_id]
                    
                    # Filter by confidence
                    if confidence < self.confidence_threshold:
                        continue
                    
                    detection = Detection(
                        class_id=class_id,
                        class_name=class_name,
                        confidence=confidence,
                        x1=float(xyxy[0]),
                        y1=float(xyxy[1]),
                        x2=float(xyxy[2]),
                        y2=float(xyxy[3]),
                    )
                    detections.append(detection)
            
            self.detections_processed += len(detections)
            return detections
        
        except Exception as e:
            logger.error(f"Error during detection: {e}")
            return []
    
    def get_stats(self) -> dict:
        """Get detector statistics."""
        return {
            "model": self.model_name,
            "device": self.device,
            "confidence_threshold": self.confidence_threshold,
            "detections_processed": self.detections_processed,
        }


def draw_detections(frame: np.ndarray, detections: List[Detection]) -> np.ndarray:
    """
    Draw detections on frame for visualization.
    
    Args:
        frame: Input frame
        detections: List of detections
    
    Returns:
        Frame with drawn bounding boxes
    """
    output = frame.copy()
    
    for det in detections:
        # Draw bounding box
        color = (0, 255, 0)  # Green
        cv2.rectangle(
            output,
            (int(det.x1), int(det.y1)),
            (int(det.x2), int(det.y2)),
            color,
            2,
        )
        
        # Draw label
        label = f"{det.class_name} {det.confidence:.2f}"
        text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
        cv2.rectangle(
            output,
            (int(det.x1), int(det.y1) - text_size[1] - 4),
            (int(det.x1) + text_size[0], int(det.y1)),
            color,
            -1,
        )
        cv2.putText(
            output,
            label,
            (int(det.x1), int(det.y1) - 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            1,
        )
    
    return output
