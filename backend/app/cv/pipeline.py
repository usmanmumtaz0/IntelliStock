"""Canonical pipeline exports; run inference using app.workers.vision."""
from app.cv.runtime import Detection, ShelfPipeline, YOLOTracker, Zone

CVPipeline = ShelfPipeline
