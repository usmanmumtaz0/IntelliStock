"""
ROI Assignment Service (CV-004)
Assigns tracked objects to shelf zones using point-in-polygon testing.
"""
import logging
import json
from typing import List, Tuple, Optional, Dict

import numpy as np
from scipy.spatial import distance

from yolo_detector import Detection

logger = logging.getLogger(__name__)


def point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
    """
    Check if point is inside polygon using ray casting algorithm.
    
    Args:
        point: (x, y) coordinates (normalized 0-1 or pixel coordinates)
        polygon: List of (x, y) vertices
    
    Returns:
        True if point is inside polygon
    """
    x, y = point
    n = len(polygon)
    inside = False
    
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        
        j = i
    
    return inside


def bbox_center_in_polygon(detection: Detection, polygon: List[Tuple[float, float]]) -> bool:
    """
    Check if detection bbox center is inside polygon.
    
    Args:
        detection: Detection object
        polygon: List of (x, y) vertices
    
    Returns:
        True if center is inside polygon
    """
    cx, cy = detection.center
    return point_in_polygon((cx, cy), polygon)


def bbox_iou_overlap(detection: Detection, polygon: List[Tuple[float, float]]) -> float:
    """
    Estimate overlap between detection bbox and polygon (simplified).
    Uses center + bbox dimensions to estimate.
    
    Args:
        detection: Detection object
        polygon: List of (x, y) vertices
    
    Returns:
        Estimated overlap (0-1)
    """
    # For simplicity, check if center is in polygon (returns 0 or 1)
    if bbox_center_in_polygon(detection, polygon):
        return 1.0
    return 0.0


class ShelfZone:
    """Represents a shelf zone ROI."""
    
    def __init__(self, zone_id: str, name: str, roi_polygon: List[Tuple[float, float]]):
        """
        Initialize shelf zone.
        
        Args:
            zone_id: UUID of zone
            name: Name of zone
            roi_polygon: List of (x, y) vertices (normalized 0-1 or pixels)
        """
        self.zone_id = zone_id
        self.name = name
        self.roi_polygon = roi_polygon
        self.detections_assigned = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "zone_id": self.zone_id,
            "name": self.name,
            "roi_polygon": self.roi_polygon,
            "detections_assigned": self.detections_assigned,
        }


class ROIAssigner:
    """Assigns detections to shelf zones based on ROI polygons."""
    
    def __init__(self):
        """Initialize ROI assigner."""
        self.zones: Dict[str, ShelfZone] = {}
        self.assignments_made = 0
    
    def add_zone(self, zone_id: str, name: str, roi_polygon_json: str):
        """
        Add a shelf zone from JSON polygon.
        
        Args:
            zone_id: UUID of zone
            name: Name of zone
            roi_polygon_json: JSON string of [[x1,y1], [x2,y2], ...] vertices
        """
        try:
            polygon = json.loads(roi_polygon_json)
            # Ensure polygon is list of tuples
            polygon = [(float(x), float(y)) for x, y in polygon]
            
            zone = ShelfZone(zone_id, name, polygon)
            self.zones[zone_id] = zone
            
            logger.info(f"Added zone {name} (ID: {zone_id}) with {len(polygon)} vertices")
        except Exception as e:
            logger.error(f"Failed to add zone {zone_id}: {e}")
    
    def assign_detection(self, detection: Detection) -> Optional[str]:
        """
        Assign detection to a zone.
        
        Uses center-in-polygon test. If multiple zones contain the detection,
        returns the first one (priority-based assignment could be added).
        
        Args:
            detection: Detection to assign
        
        Returns:
            zone_id if assigned, None otherwise
        """
        for zone_id, zone in self.zones.items():
            if bbox_center_in_polygon(detection, zone.roi_polygon):
                zone.detections_assigned += 1
                self.assignments_made += 1
                return zone_id
        
        return None
    
    def assign_detections(self, detections: List[Detection]) -> Dict[Detection, Optional[str]]:
        """
        Assign multiple detections to zones.
        
        Args:
            detections: List of detections
        
        Returns:
            Dict mapping detection -> zone_id (or None if unassigned)
        """
        assignments = {}
        for detection in detections:
            zone_id = self.assign_detection(detection)
            assignments[detection] = zone_id
        
        return assignments
    
    def get_assignments_by_zone(self, detections: List[Detection]) -> Dict[str, List[Detection]]:
        """
        Get detections grouped by zone.
        
        Args:
            detections: List of detections
        
        Returns:
            Dict mapping zone_id -> list of detections in that zone
        """
        assignments = {}
        
        for detection in detections:
            zone_id = self.assign_detection(detection)
            
            if zone_id:
                if zone_id not in assignments:
                    assignments[zone_id] = []
                assignments[zone_id].append(detection)
        
        return assignments
    
    def get_stats(self) -> dict:
        """Get assigner statistics."""
        return {
            "zones_defined": len(self.zones),
            "assignments_made": self.assignments_made,
            "zones": {zone_id: zone.to_dict() for zone_id, zone in self.zones.items()},
        }


def parse_polygon_from_frame(frame_height: int, frame_width: int, normalized_polygon: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    Convert normalized polygon coordinates (0-1) to pixel coordinates.
    
    Args:
        frame_height: Height of frame in pixels
        frame_width: Width of frame in pixels
        normalized_polygon: List of (x, y) in range [0, 1]
    
    Returns:
        List of (x, y) in pixel coordinates
    """
    return [
        (x * frame_width, y * frame_height)
        for x, y in normalized_polygon
    ]


def visualize_roi_polygons(frame, zones: Dict[str, ShelfZone], thickness: int = 2, color: Tuple = (0, 255, 0)):
    """
    Draw ROI polygons on frame.
    
    Args:
        frame: Input frame (BGR)
        zones: Dict of zone_id -> ShelfZone
        thickness: Line thickness
        color: RGB color for lines
    
    Returns:
        Frame with drawn polygons
    """
    import cv2
    
    output = frame.copy()
    frame_height, frame_width = frame.shape[:2]
    
    for zone_id, zone in zones.items():
        # Convert normalized to pixel coordinates if needed
        polygon = zone.roi_polygon
        
        # Assume polygon is already in pixel coordinates
        polygon_pts = np.array(polygon, dtype=np.int32)
        
        # Draw polygon outline
        cv2.polylines(output, [polygon_pts], True, color, thickness)
        
        # Draw zone name
        if len(polygon) > 0:
            # Put text at first vertex
            cv2.putText(
                output,
                zone.name,
                tuple(polygon_pts[0]),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
            )
    
    return output
