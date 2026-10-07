"""
ROI Assignment Service (CV-004)
Assigns tracked objects to shelf zones using point-in-polygon detection.
"""
import json
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ZoneAssignment:
    """Assignment of a tracked object to a zone."""

    track_id: int
    zone_id: str
    zone_name: str
    confidence: float


def point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
    """
    Check if point is inside polygon using ray casting algorithm.

    Args:
        point: (x, y) normalized coordinates [0, 1]
        polygon: List of (x, y) vertices of polygon

    Returns:
        True if point is inside polygon
    """
    x, y = point
    n = len(polygon)
    inside = False

    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside


class ROIAssigner:
    """
    Assigns tracked objects to shelf zones using ROI polygons.
    """

    def __init__(self):
        self.zones = {}  # zone_id -> (name, polygon)
        self.assignment_count = 0

    def add_zone(self, zone_id: str, zone_name: str, roi_polygon_json: str):
        """
        Add a shelf zone ROI.

        Args:
            zone_id: Zone identifier
            zone_name: Human-readable name
            roi_polygon_json: JSON string of polygon vertices [[x1,y1], [x2,y2], ...]
        """
        try:
            polygon = json.loads(roi_polygon_json)
            # Validate polygon format
            if not isinstance(polygon, list) or len(polygon) < 3:
                logger.error(f"Invalid polygon for zone {zone_id}: must have ≥3 vertices")
                return False

            # Convert to tuples
            polygon_tuples = [tuple(p) for p in polygon]
            self.zones[zone_id] = (zone_name, polygon_tuples)
            logger.info(f"Zone {zone_id} registered with {len(polygon_tuples)} vertices")
            return True

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ROI polygon for zone {zone_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error adding zone {zone_id}: {e}")
            return False

    def assign_tracked_objects(self, tracked_objects: List) -> List[ZoneAssignment]:
        """
        Assign tracked objects to zones based on center point.

        Args:
            tracked_objects: List of TrackedObject instances

        Returns:
            List of ZoneAssignment
        """
        assignments = []

        for obj in tracked_objects:
            # Get object center
            obj_center = (
                (obj.bbox[0] + obj.bbox[2]) / 2,
                (obj.bbox[1] + obj.bbox[3]) / 2,
            )

            # Try to assign to a zone
            for zone_id, (zone_name, polygon) in self.zones.items():
                if point_in_polygon(obj_center, polygon):
                    assignment = ZoneAssignment(
                        track_id=obj.track_id,
                        zone_id=zone_id,
                        zone_name=zone_name,
                        confidence=obj.confidence,
                    )
                    assignments.append(assignment)
                    self.assignment_count += 1
                    break  # Assume non-overlapping zones

        logger.debug(f"Assigned {len(assignments)} objects to zones")
        return assignments

    def get_zone_object_count(
        self,
        tracked_objects: List,
        zone_id: str,
    ) -> int:
        """
        Count objects in a specific zone.

        Args:
            tracked_objects: List of TrackedObject instances
            zone_id: Zone to count objects in

        Returns:
            Number of objects in zone
        """
        if zone_id not in self.zones:
            return 0

        _, polygon = self.zones[zone_id]
        count = 0

        for obj in tracked_objects:
            obj_center = (
                (obj.bbox[0] + obj.bbox[2]) / 2,
                (obj.bbox[1] + obj.bbox[3]) / 2,
            )
            if point_in_polygon(obj_center, polygon):
                count += 1

        return count

    def list_zones(self) -> dict:
        """Get list of registered zones."""
        return {
            zone_id: {"name": name, "vertices": len(polygon)}
            for zone_id, (name, polygon) in self.zones.items()
        }
