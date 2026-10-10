"""Lightweight CV contracts; model libraries load only inside the CV worker."""
from app.cv.runtime import Detection, ShelfPipeline, YOLOTracker, Zone

__all__ = ["Detection", "ShelfPipeline", "YOLOTracker", "Zone"]
