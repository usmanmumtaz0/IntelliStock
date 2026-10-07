"""
Observation Builder (CV-005)
Builds inventory observations from CV pipeline results.
Produces output ready for reconciliation engine.
"""
import logging
from dataclasses import dataclass
from typing import List, Optional

from app.cv.detection import Detection
from app.cv.tracking import TrackedObject
from app.cv.roi_assignment import ZoneAssignment

logger = logging.getLogger(__name__)


@dataclass
class RawObservation:
    """Raw observation from CV pipeline before reconciliation."""

    frame_id: int
    camera_id: str
    zone_id: str
    timestamp: str
    tracked_objects: List[TrackedObject]
    object_count: int  # Objects detected in this zone
    average_confidence: float


class ObservationBuilder:
    """Builds reconciliation observations from CV pipeline output."""

    def __init__(self):
        self.observation_count = 0

    def build_observation(
        self,
        frame_id: int,
        camera_id: str,
        timestamp: str,
        assignments: List[ZoneAssignment],
        tracked_objects: List[TrackedObject],
    ) -> List[RawObservation]:
        """
        Build raw observations from zone assignments.

        Args:
            frame_id: Frame number
            camera_id: Source camera ID
            timestamp: Frame timestamp (ISO format)
            assignments: List of ZoneAssignment from ROI assigner
            tracked_objects: List of all TrackedObject instances

        Returns:
            List of RawObservation (one per zone with objects)
        """
        observations = []

        # Group assignments by zone
        zones_with_objects = {}
        for assignment in assignments:
            if assignment.zone_id not in zones_with_objects:
                zones_with_objects[assignment.zone_id] = {
                    "name": assignment.zone_name,
                    "objects": [],
                }
            zones_with_objects[assignment.zone_id]["objects"].append(assignment)

        # Build observation for each zone
        for zone_id, zone_data in zones_with_objects.items():
            objects = zone_data["objects"]
            count = len(objects)
            confidences = [obj.confidence for obj in objects]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            observation = RawObservation(
                frame_id=frame_id,
                camera_id=camera_id,
                zone_id=zone_id,
                timestamp=timestamp,
                tracked_objects=[
                    t for t in tracked_objects if t.track_id in [o.track_id for o in objects]
                ],
                object_count=count,
                average_confidence=avg_confidence,
            )
            observations.append(observation)
            self.observation_count += 1

            logger.debug(
                f"Observation built: frame={frame_id}, zone={zone_id}, "
                f"count={count}, avg_conf={avg_confidence:.2f}"
            )

        return observations

    def get_stats(self) -> dict:
        """Get observation builder statistics."""
        return {"total_observations": self.observation_count}
