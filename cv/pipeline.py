"""Retired prototype entry point. From backend run python -m app.workers.vision."""
from app.cv.runtime import ShelfPipeline, YOLOTracker
from app.workers.vision import main

if __name__ == "__main__":
    main()
