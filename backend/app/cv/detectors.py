"""Detector-neutral contracts and the trusted Ultralytics baseline adapter.

Optional detectors must implement this contract. They are never downloaded or
activated implicitly, which keeps the reviewed YOLOv8 checkpoint usable when
experimental dependencies are unavailable.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from app.cv.model_artifact import (
    load_trusted_yolo_checkpoint,
    verify_artifact,
    verify_model_metadata,
)


@dataclass(frozen=True)
class DetectorHealth:
    detector: str
    configured: bool
    loaded: bool
    model_path: str | None
    manifest_path: str | None
    manifest_verified: bool
    requested_device: str
    actual_device: str
    cuda_available: bool
    class_count: int
    input_size: int
    error: str | None = None

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


@runtime_checkable
class Detector(Protocol):
    """Common interface for required and experimental object detectors."""

    def load_model(self) -> None: ...

    def predict_image(self, image: Any, *, confidence: float, image_size: int) -> Any: ...

    def predict_frame(
        self,
        frame: Any,
        *,
        confidence: float,
        image_size: int,
        tracking: bool,
    ) -> Any: ...

    def get_supported_classes(self) -> dict[int, str]: ...

    def health_check(self) -> DetectorHealth: ...

    def reset_tracking(self) -> None: ...


def resolve_device(requested: str) -> tuple[str, bool]:
    """Resolve ``auto``/CUDA without claiming a GPU that PyTorch cannot use."""
    import torch

    cuda_available = bool(torch.cuda.is_available())
    normalized = requested.strip().lower()
    if normalized == "auto":
        return ("cuda:0" if cuda_available else "cpu"), cuda_available
    if normalized.startswith("cuda") and not cuda_available:
        raise ValueError(
            "CUDA was requested but this PyTorch runtime cannot access an NVIDIA GPU"
        )
    return requested, cuda_available


class UltralyticsYOLODetector:
    """Lazily loaded, reusable YOLOv8 detector with optional ByteTrack state."""

    detector_id = "ultralytics-yolov8"

    def __init__(
        self,
        model_path: str,
        manifest_path: str,
        requested_device: str,
        *,
        iou_threshold: float,
        max_detections: int,
        default_image_size: int,
    ):
        self.model_path = str(Path(model_path).expanduser()) if model_path else ""
        self.manifest_path = str(Path(manifest_path).expanduser()) if manifest_path else ""
        self.requested_device = requested_device
        self.iou_threshold = iou_threshold
        self.max_detections = max_detections
        self.default_image_size = default_image_size
        self.model = None
        self.manifest = None
        self.actual_device = "unresolved"
        self.cuda_available = False
        self.error: str | None = None

    def load_model(self) -> None:
        if self.model is not None:
            return
        model = Path(self.model_path)
        if not model.is_file():
            raise ValueError("Configured trained model weights are missing")
        self.actual_device, self.cuda_available = resolve_device(self.requested_device)
        if self.manifest_path:
            self.manifest = verify_artifact(model, self.manifest_path)
        loaded = load_trusted_yolo_checkpoint(model)
        if self.manifest is not None:
            verify_model_metadata(self.manifest, loaded)
        self.model = loaded
        self.error = None

    def predict_image(self, image: Any, *, confidence: float, image_size: int) -> Any:
        return self.predict_frame(
            image,
            confidence=confidence,
            image_size=image_size,
            tracking=False,
        )

    def predict_frame(
        self,
        frame: Any,
        *,
        confidence: float,
        image_size: int,
        tracking: bool,
    ) -> Any:
        self.load_model()
        kwargs = {
            "device": self.actual_device,
            "conf": confidence,
            "iou": self.iou_threshold,
            "max_det": self.max_detections,
            "imgsz": image_size,
            "verbose": False,
        }
        if tracking:
            return self.model.track(
                frame,
                persist=True,
                tracker="bytetrack.yaml",
                **kwargs,
            )[0]
        return self.model.predict(frame, **kwargs)[0]

    def get_supported_classes(self) -> dict[int, str]:
        if self.model is not None:
            return dict(self.model.names)
        if self.manifest_path and Path(self.manifest_path).is_file():
            try:
                manifest = verify_artifact(self.model_path, self.manifest_path)
                return {item.class_id: item.label for item in manifest.classes}
            except (OSError, ValueError):
                return {}
        return {}

    def health_check(self) -> DetectorHealth:
        error = self.error
        configured = bool(self.model_path and Path(self.model_path).is_file())
        manifest_verified = False
        classes = self.get_supported_classes() if configured else {}
        if configured and self.manifest_path:
            try:
                verify_artifact(self.model_path, self.manifest_path)
                manifest_verified = True
            except (OSError, ValueError) as exc:
                error = str(exc)
        try:
            actual_device, cuda_available = resolve_device(self.requested_device)
        except ValueError as exc:
            actual_device, cuda_available, error = "unavailable", False, str(exc)
        return DetectorHealth(
            detector=self.detector_id,
            configured=configured,
            loaded=self.model is not None,
            model_path=Path(self.model_path).name if self.model_path else None,
            manifest_path=Path(self.manifest_path).name if self.manifest_path else None,
            manifest_verified=manifest_verified,
            requested_device=self.requested_device,
            actual_device=self.actual_device if self.model is not None else actual_device,
            cuda_available=cuda_available,
            class_count=len(classes),
            input_size=self.default_image_size,
            error=error,
        )

    def reset_tracking(self) -> None:
        if self.model is not None:
            self.model.predictor = None


def build_detector(settings) -> Detector:
    if settings.CV_DETECTOR != "yolov8":
        raise ValueError(
            f"Detector '{settings.CV_DETECTOR}' is not installed; configured baseline is yolov8"
        )
    return UltralyticsYOLODetector(
        settings.CV_MODEL_PATH,
        settings.CV_MODEL_MANIFEST,
        settings.CV_DEVICE,
        iou_threshold=settings.CV_NMS_IOU_THRESHOLD,
        max_detections=settings.CV_MAX_DETECTIONS,
        default_image_size=settings.CV_IMAGE_SIZE,
    )
