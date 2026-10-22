"""Bounded frame sampling, YOLO inference, annotation, and durable evidence writes."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import math
from pathlib import Path
from threading import RLock
from time import perf_counter

from sqlalchemy.orm import Session

from app.core.config import settings
from app.cv.detectors import build_detector
from app.cv.identity_evidence import (
    EnrichedIdentityEvidence,
    IdentityEvidenceRuntime,
    crop_detection,
    image_sharpness,
)
from app.models import AgentRun, Product
from app.models.agent_run import AgentRunStatus
from app.models.video_job import (
    VideoDetection,
    VideoFrame,
    VideoJobStatus,
    VideoProcessingJob,
    VideoSourceKind,
)
from app.services.video_storage import new_annotated_key, resolve_storage_key, storage_root
from app.services.product_identity import IdentityEvidence, ProductIdentityService
from app.services.outbox import enqueue

logger = logging.getLogger(__name__)


def utc_text() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class FrameSample:
    sequence: int
    source_frame_index: int
    timestamp_ms: int
    frame: object


class VideoFrameSampler:
    """Sequential OpenCV reader with timestamp-based sampling and hard bounds."""

    def __init__(self, source: str, interval_seconds: float, max_frames: int,
                 max_duration_seconds: float | None):
        self.source = source
        self.interval_ms = interval_seconds * 1000.0
        self.max_frames = max_frames
        self.max_duration_ms = (max_duration_seconds * 1000.0
                                if max_duration_seconds is not None else None)
        self.fps: float | None = None
        self.total_frames: int | None = None
        self.duration_ms: int | None = None

    def __iter__(self):
        import cv2

        if isinstance(self.source, str) and Path(self.source).suffix.lower() in {
            ".jpg", ".jpeg", ".png", ".webp"
        }:
            frame = cv2.imread(self.source, cv2.IMREAD_COLOR)
            if frame is None or frame.size == 0:
                raise ValueError("Image could not be decoded by the installed OpenCV build")
            self.total_frames = 1
            self.duration_ms = 0
            yield FrameSample(0, 0, 0, frame)
            return

        capture_source = int(self.source) if str(self.source).isdecimal() else self.source
        capture = cv2.VideoCapture(capture_source)
        if not capture.isOpened():
            capture.release()
            raise ValueError("Video could not be opened by the installed OpenCV/FFmpeg build")
        try:
            raw_fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
            self.fps = raw_fps if math.isfinite(raw_fps) and raw_fps > 0 else None
            raw_total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            self.total_frames = raw_total if raw_total > 0 else None
            if self.fps and self.total_frames:
                self.duration_ms = int(self.total_frames / self.fps * 1000)
            next_sample_ms = 0.0
            previous_timestamp = -1.0
            source_index = 0
            sequence = 0
            readable = False
            while sequence < self.max_frames:
                ok, frame = capture.read()
                if not ok:
                    break
                readable = True
                timestamp = float(capture.get(cv2.CAP_PROP_POS_MSEC) or 0)
                if not math.isfinite(timestamp) or timestamp <= previous_timestamp:
                    # Some containers expose neither timestamps nor FPS. A stable
                    # 30 FPS fallback still enforces the requested sampling bounds.
                    effective_fps = self.fps or 30.0
                    timestamp = source_index / effective_fps * 1000.0
                previous_timestamp = timestamp
                if self.max_duration_ms is not None and timestamp > self.max_duration_ms:
                    break
                if source_index == 0 or timestamp + 0.5 >= next_sample_ms:
                    yield FrameSample(sequence, source_index, max(0, int(round(timestamp))), frame)
                    sequence += 1
                    next_sample_ms = timestamp + self.interval_ms
                source_index += 1
            if not readable:
                raise ValueError("Video contains no readable frames")
        finally:
            capture.release()


class VideoModelService:
    """One lazily loaded model per worker process, protected from concurrent use."""

    def __init__(self):
        self._lock = RLock()
        self._detector = None
        self._model = None
        self._manifest = None

    def _load(self):
        if self._model is not None:
            return
        if not settings.CV_MODEL_MANIFEST:
            logger.warning("CV_MODEL_MANIFEST is not configured; product mapping remains review-only")
        import os
        runtime_dir = storage_root() / ".runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        os.environ["YOLO_AUTOINSTALL"] = "false"
        os.environ.setdefault("YOLO_CONFIG_DIR", str(runtime_dir / "ultralytics"))
        os.environ.setdefault("MPLCONFIGDIR", str(runtime_dir / "matplotlib"))
        detector = build_detector(settings)
        detector.load_model()
        self._detector = detector
        self._model = detector.model
        self._manifest = detector.manifest
        logger.info("Loaded trained model path=%s device=%s classes=%s",
                    settings.CV_MODEL_PATH, detector.actual_device, dict(detector.model.names))

    def reset_tracking(self):
        if self._detector is not None:
            self._detector.reset_tracking()
        elif self._model is not None:
            self._model.predictor = None

    def infer(self, frame, confidence: float, image_size: int, tracking: bool):
        with self._lock:
            self._load()
            result = self._detector.predict_frame(
                frame,
                confidence=confidence,
                image_size=image_size,
                tracking=tracking,
            )
            return result, result.plot()

    @property
    def manifest(self):
        return self._manifest

    def health(self):
        detector = self._detector or build_detector(settings)
        health = detector.health_check().model_dump()
        health["identity_evidence"] = identity_evidence_runtime.health()
        return health


model_service = VideoModelService()
identity_evidence_runtime = IdentityEvidenceRuntime(settings)


def _product_map(db: Session) -> dict[int, str]:
    manifest = model_service.manifest
    if manifest is None:
        return {}
    by_sku = {product.sku: product.id for product in db.query(Product).all()}
    return {item.class_id: by_sku[item.sku]
            for item in manifest.classes if item.sku in by_sku}


def _job_source(db: Session, job: VideoProcessingJob) -> str:
    if job.source_kind == VideoSourceKind.UPLOAD:
        path = resolve_storage_key(job.storage_key or "")
        if not path.is_file():
            media_kind = "image" if (job.content_type or "").startswith("image/") else "video"
            raise ValueError(
                f"Uploaded {media_kind} source is unavailable to the processing worker. "
                "Verify that the API and worker share VIDEO_STORAGE_ROOT, then retry the job."
            )
        return str(path)
    from app.models.camera import Camera
    camera = db.get(Camera, job.camera_id)
    if not camera or not camera.is_active or not camera.source_url:
        raise ValueError("Camera is missing, disabled, or has no configured source")
    if camera.source_url.lower().startswith("webcam://"):
        return camera.source_url.split("://", 1)[1].rstrip("/")
    return camera.source_url


def _save_annotated(job_id: str, sequence: int, image) -> str:
    import cv2
    key = new_annotated_key(job_id, sequence)
    path = resolve_storage_key(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), image, [int(cv2.IMWRITE_JPEG_QUALITY), 88]):
        raise RuntimeError("Annotated frame could not be written")
    return key


def _controlled_error(exc: Exception) -> str:
    if isinstance(exc, ValueError):
        return str(exc)[:500]
    return "Video processing failed; inspect the worker log for details"


def _enqueue_job_state(db: Session, job: VideoProcessingJob) -> None:
    enqueue(db, "vision_job_updated", {
        "job_id": job.id,
        "status": job.status.value,
        "stage": job.stage,
        "frames_processed": job.frames_processed,
        "detection_instances": job.detection_instances,
    })


def process_video_job(db: Session, job_id: str) -> None:
    job = db.get(VideoProcessingJob, job_id)
    if not job:
        return
    run = AgentRun(agent_type="vision", status=AgentRunStatus.RUNNING,
                   trigger_event="video_processing_job",
                   trigger_data={"job_id": job.id, "source_kind": job.source_kind.value,
                                 "media_kind": "image" if (job.content_type or "").startswith("image/")
                                 else "video"})
    db.add(run)
    db.flush()
    job.agent_run_id = run.id
    job.status = VideoJobStatus.PROCESSING
    job.stage = "opening_source"
    job.started_at = utc_text()
    _enqueue_job_state(db, job)
    db.commit()
    started = perf_counter()
    try:
        source = _job_source(db, job)
        model_service.reset_tracking()
        # Force model initialization before deriving manifest-based product mappings.
        model_service._load()
        product_map = _product_map(db)
        identity_service = ProductIdentityService(
            db,
            settings.CV_IDENTITY_MIN_CONFIDENCE,
            ocr_minimum_confidence=settings.CV_OCR_MATCH_MIN_CONFIDENCE,
            ocr_minimum_margin=settings.CV_OCR_MATCH_MIN_MARGIN,
            retrieval_minimum_confidence=settings.CV_RETRIEVAL_MIN_CONFIDENCE,
            retrieval_minimum_margin=settings.CV_RETRIEVAL_MIN_MARGIN,
        )
        catalog_products = tuple(db.query(Product).all())
        manifest_skus = {
            item.class_id: item.sku
            for item in (model_service.manifest.classes if model_service.manifest else [])
        }
        sampler = VideoFrameSampler(source, job.sample_interval_seconds, job.max_frames,
                                    job.max_duration_seconds)
        job.stage = "extracting_and_detecting"
        db.commit()
        class_counts: Counter[str] = Counter()
        identity_counts: Counter[str] = Counter()
        unique_tracks: set[tuple[int, int]] = set()
        track_evidence: dict[tuple[int, int], tuple[float, EnrichedIdentityEvidence]] = {}
        evidence_counts: Counter[str] = Counter()
        for sample in sampler:
            db.refresh(job)
            if job.cancel_requested:
                job.status = VideoJobStatus.CANCELLED
                job.stage = "cancelled"
                job.completed_at = utc_text()
                run.status = AgentRunStatus.COMPLETED
                run.output_action = "video_job_cancelled"
                _enqueue_job_state(db, job)
                db.commit()
                return
            inference_started = perf_counter()
            result, annotated = model_service.infer(
                sample.frame, job.confidence_threshold, job.image_size,
                job.tracking_enabled,
            )
            inference_ms = (perf_counter() - inference_started) * 1000.0
            height, width = sample.frame.shape[:2]
            boxes = result.boxes
            count = len(boxes) if boxes is not None else 0
            key = _save_annotated(job.id, sample.sequence, annotated)
            frame_row = VideoFrame(
                job_id=job.id, sequence=sample.sequence,
                source_frame_index=sample.source_frame_index,
                timestamp_ms=sample.timestamp_ms, width=width, height=height,
                inference_ms=inference_ms, annotated_storage_key=key,
                detection_count=count,
            )
            db.add(frame_row)
            db.flush()
            if boxes is not None:
                track_ids = (boxes.id.cpu().tolist() if boxes.id is not None
                             else [None] * len(boxes))
                for cls, conf, xyxy, xyxyn, track_id in zip(
                    boxes.cls.cpu().tolist(), boxes.conf.cpu().tolist(),
                    boxes.xyxy.cpu().tolist(), boxes.xyxyn.cpu().tolist(), track_ids,
                ):
                    class_id = int(cls)
                    class_name = str(result.names[class_id])
                    enriched = EnrichedIdentityEvidence()
                    if identity_evidence_runtime.enabled:
                        crop = crop_detection(sample.frame, xyxy)
                        cache_key = ((class_id, int(track_id))
                                     if track_id is not None else None)
                        sharpness = image_sharpness(crop)
                        cached = track_evidence.get(cache_key) if cache_key else None
                        if (cached is None or sharpness >= cached[0]
                                * settings.CV_EVIDENCE_REFRESH_SHARPNESS_RATIO):
                            enriched = identity_evidence_runtime.extract(crop, catalog_products)
                            if cache_key:
                                track_evidence[cache_key] = (sharpness, enriched)
                        else:
                            enriched = cached[1]
                    identity = identity_service.identify(IdentityEvidence(
                        detector_label=class_name,
                        detector_confidence=float(conf),
                        manifest_sku=manifest_skus.get(class_id),
                        ocr_tokens=enriched.ocr.tokens,
                        ocr_confidence=enriched.ocr.confidence,
                        retrieval_scores=enriched.retrieval.scores,
                        provider_errors=enriched.errors,
                    ))
                    if enriched.ocr.tokens:
                        evidence_counts["ocr"] += 1
                    if enriched.retrieval.scores:
                        evidence_counts["visual_retrieval"] += 1
                    for provider_error in enriched.errors:
                        evidence_counts[provider_error] += 1
                    normalized = {name: float(value) for name, value in
                                  zip(("x1", "y1", "x2", "y2"), xyxyn)}
                    db.add(VideoDetection(
                        job_id=job.id, frame_id=frame_row.id,
                        product_id=identity.product_id or product_map.get(class_id),
                        class_id=class_id,
                        class_name=class_name, confidence=float(conf),
                        track_id=int(track_id) if track_id is not None else None,
                        x1=float(xyxy[0]), y1=float(xyxy[1]),
                        x2=float(xyxy[2]), y2=float(xyxy[3]),
                        normalized_bbox=normalized,
                        identity_status=identity.status.value,
                        identity_confidence=identity.confidence,
                        category=identity.category,
                        brand=identity.brand,
                        variant=identity.variant,
                        package_size=identity.package_size,
                        barcode=identity.barcode,
                        identity_evidence=identity.evidence,
                    ))
                    class_counts[class_name] += 1
                    identity_counts[identity.status.value] += 1
                    if track_id is not None:
                        unique_tracks.add((class_id, int(track_id)))
            job.frames_processed += 1
            job.detection_instances += count
            if count:
                job.frames_with_detections += 1
            job.source_fps = sampler.fps
            job.total_frames = sampler.total_frames
            job.source_duration_ms = sampler.duration_ms
            if job.frames_processed == 1 or job.frames_processed % 10 == 0:
                _enqueue_job_state(db, job)
            db.commit()
        if job.frames_processed == 0:
            raise ValueError("Video contains no sampled frames")
        job.status = VideoJobStatus.COMPLETED
        job.stage = "completed"
        job.completed_at = utc_text()
        job.unique_tracked_objects = len(unique_tracks) if job.tracking_enabled else None
        job.summary = {**(job.summary or {}),
            "detections_by_class": dict(sorted(class_counts.items())),
            "identity_states": dict(sorted(identity_counts.items())),
            "mapped_detection_classes": len(product_map),
            "identity_evidence": dict(sorted(evidence_counts.items())),
            "inventory_effect": "review_only",
            "counting_note": "Detection instances are observations, not authoritative inventory.",
        }
        run.status = AgentRunStatus.COMPLETED
        run.output_action = "video_detection_completed"
        run.output_data = {
            "job_id": job.id, "frames": job.frames_processed,
            "detections": job.detection_instances,
            "unique_tracks": job.unique_tracked_objects,
        }
        run.execution_time_ms = int((perf_counter() - started) * 1000)
        _enqueue_job_state(db, job)
        db.commit()
    except Exception as exc:
        logger.exception("Video job failed job_id=%s", job_id)
        db.rollback()
        job = db.get(VideoProcessingJob, job_id)
        if job:
            job.status = VideoJobStatus.FAILED
            job.stage = "failed"
            job.error_message = _controlled_error(exc)
            job.completed_at = utc_text()
            if job.agent_run_id:
                run = db.get(AgentRun, job.agent_run_id)
                if run:
                    run.status = AgentRunStatus.FAILED
                    run.error_message = job.error_message
                    run.execution_time_ms = int((perf_counter() - started) * 1000)
            _enqueue_job_state(db, job)
            db.commit()
