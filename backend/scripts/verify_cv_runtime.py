"""Dependency/codec smoke only: random weights, no downloads, no accuracy claims."""
import os
import json
import tempfile
from pathlib import Path


def main():
    with tempfile.TemporaryDirectory(prefix="intellistock-cv-smoke-") as directory:
        root = Path(directory)
        os.environ["YOLO_CONFIG_DIR"] = str(root / "yolo")
        os.environ["MPLCONFIGDIR"] = str(root / "matplotlib")
        os.environ["YOLO_AUTOINSTALL"] = "false"
        import cv2
        import numpy as np
        import torch
        from ultralytics import YOLO
        from app.cv.runtime import YOLOTracker
        from app.cv.model_artifact import file_sha256, verify_artifact, verify_model_metadata
        from app.cv.capture import FrameSource

        torch.set_num_threads(1)
        untrained = YOLO("yolov8n.yaml")
        weights = root / "random-smoke.pt"
        torch.save({"model": untrained.model}, weights)
        detector = YOLOTracker(str(weights))
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps({"schema_version": 1, "model_version": "untrained-smoke",
            "sha256": file_sha256(weights), "task": "detect", "classes": [
                {"class_id": key, "label": value, "sku": f"TEST-{key}"}
                for key, value in detector.model.names.items()]}), encoding="utf-8")
        verify_model_metadata(verify_artifact(weights, manifest_path), detector.model)
        video = root / "synthetic.avi"
        writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 2, (64, 64))
        if not writer.isOpened():
            raise RuntimeError("MJPG writer unavailable")
        for _ in range(3):
            writer.write(np.zeros((64, 64, 3), dtype=np.uint8))
        writer.release()
        source = FrameSource(str(video), replay=True)
        try:
            for _ in range(3):
                ok, frame, _ = source.read()
                assert ok
                assert isinstance(detector.detect(frame), list)
            assert not source.read()[0]
        finally:
            source.close()
        print("Local random-weight YOLO/ByteTrack and recorded-video codec smoke passed; not an accuracy test")


if __name__ == "__main__":
    main()
