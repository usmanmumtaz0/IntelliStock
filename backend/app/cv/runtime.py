"""Canonical, testable shelf observation pipeline.

Inference failures and unqualified empty ROIs produce uncertainty, never zero.
The detector is injected so replay tests do not download models or require GPUs.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import math


@dataclass(frozen=True)
class Detection:
    class_id: int
    track_id: int | None
    confidence: float
    bbox: tuple[float, float, float, float]


@dataclass(frozen=True)
class Zone:
    id: str
    polygon: list
    products: dict[int, str]
    allow_empty: frozenset[int] = frozenset()
    confidence: float = 0.6


def contains(polygon, x, y):
    inside = False
    j = len(polygon) - 1
    for i, (xi, yi) in enumerate(polygon):
        xj, yj = polygon[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


class ShelfPipeline:
    def __init__(self, zones, min_hits=3, max_age_seconds=5):
        self.zones = zones
        self.min_hits = min_hits
        self.max_age_seconds = max_age_seconds
        self.hits = {}
        self.last_sequence = -1

    def reset(self):
        self.hits.clear()

    def observe(self, detections, sequence, captured_at, healthy=True):
        age = (datetime.now(timezone.utc) - captured_at).total_seconds()
        if sequence <= self.last_sequence or not -1 <= age <= self.max_age_seconds:
            return []
        self.last_sequence = sequence
        if not healthy:
            self.reset()
            return []
        current = {}
        for det in detections:
            if det.track_id is not None:
                key = (det.track_id, det.class_id)
                current[key] = self.hits.get(key, 0) + 1
        self.hits = current
        observations = []
        ambiguous_zones = set()
        for det in detections:
            owners = [z.id for z in self.zones if contains(z.polygon,
                (det.bbox[0] + det.bbox[2]) / 2, (det.bbox[1] + det.bbox[3]) / 2)]
            if len(owners) > 1:
                ambiguous_zones.update(owners)
        for zone in self.zones:
            if zone.id in ambiguous_zones:
                continue
            members = [d for d in detections if contains(zone.polygon,
                       (d.bbox[0] + d.bbox[2]) / 2, (d.bbox[1] + d.bbox[3]) / 2)]
            # Unknown objects or weak detections may be an occluder/misclassification.
            obstructed = any(d.class_id not in zone.products or
                not math.isfinite(d.confidence) or d.confidence < zone.confidence for d in members)
            for class_id, product_id in zone.products.items():
                matching = [d for d in members if d.class_id == class_id]
                stable = [d for d in matching if d.track_id is not None and
                          self.hits.get((d.track_id, d.class_id), 0) >= self.min_hits]
                if obstructed or len(stable) != len(matching):
                    continue
                if not matching and class_id not in zone.allow_empty:
                    continue
                confidence = min((d.confidence for d in stable), default=zone.confidence)
                observations.append((zone.id, product_id, len({d.track_id for d in stable}), confidence))
        return observations


class YOLOTracker:
    def __init__(self, model_path, device="cpu"):
        from pathlib import Path
        import os
        if not Path(model_path).is_file():
            raise ValueError("Supply an existing trusted model file; automatic downloads are disabled")
        os.environ["YOLO_AUTOINSTALL"] = "false"
        from ultralytics import YOLO
        self.model = YOLO(model_path)
        self.device = device

    def detect(self, frame):
        result = self.model.track(frame, persist=True, tracker="bytetrack.yaml",
                                  device=self.device, conf=0.1, verbose=False)[0]
        if result.boxes is None:
            return []
        boxes = result.boxes
        ids = boxes.id.cpu().tolist() if boxes.id is not None else [None] * len(boxes)
        return [Detection(int(cls), int(tid) if tid is not None else None, float(conf), tuple(box))
                for cls, tid, conf, box in zip(boxes.cls.cpu().tolist(), ids,
                    boxes.conf.cpu().tolist(), boxes.xyxyn.cpu().tolist())]


def frame_healthy(frame):
    """Shared coarse quality guard; not a guarantee against occlusion."""
    import cv2
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return 10 < float(gray.mean()) < 245 and float(gray.std()) > 5
