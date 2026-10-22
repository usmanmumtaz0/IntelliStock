"""Authenticated video upload, bounded camera jobs, status, evidence, and cancellation."""
from __future__ import annotations

from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.permissions import permissions_for
from app.core.security import get_current_user
from app.database import get_db
from app.models.camera import Camera
from app.models.video_job import (
    VideoFrame,
    VideoDetection,
    VideoJobStatus,
    VideoProcessingJob,
    VideoSourceKind,
)
from app.models.product import Product
from app.schemas.video_job import (
    BoundingBox,
    CameraVideoJobCreate,
    VideoDetectionResponse,
    VideoFrameListResponse,
    VideoFrameResponse,
    VideoJobCancelResponse,
    VideoJobListResponse,
    VideoJobResponse,
    DetectionReviewListResponse,
    DetectionReviewResponse,
    DetectionIdentityUpdate,
    DetectorHealthResponse,
)
from app.services.operations import audit
from app.services.video_storage import (
    SUPPORTED_IMAGE_CONTENT_TYPES,
    SUPPORTED_CONTENT_TYPES,
    new_image_key,
    new_upload_key,
    remove_job_media,
    resolve_storage_key,
    safe_extension,
    safe_image_extension,
    storage_node_id,
    storage_queue_stage,
)

router = APIRouter(prefix="/api/v1/video-jobs", tags=["video processing"])


def _owns_or_can_read_all(job, user) -> bool:
    return job.owner_user_id == user.id or "video_jobs.read_all" in permissions_for(user)


def _get_job(db: Session, job_id: str, user) -> VideoProcessingJob:
    job = db.get(VideoProcessingJob, job_id)
    if not job or not _owns_or_can_read_all(job, user):
        raise HTTPException(404, "Video job not found")
    return job


def _job_response(job: VideoProcessingJob) -> VideoJobResponse:
    response = VideoJobResponse.model_validate(job)
    if job.status == VideoJobStatus.CANCELLED and job.stage.startswith("storage_queued:"):
        response.status = VideoJobStatus.QUEUED
        response.stage = "queued"
    if response.summary and "_storage_node_id" in response.summary:
        response.summary = {
            key: value for key, value in response.summary.items()
            if key != "_storage_node_id"
        }
    return response


def _frame_response(job_id: str, frame: VideoFrame) -> VideoFrameResponse:
    detections = [VideoDetectionResponse(
        id=item.id, class_id=item.class_id, class_name=item.class_name,
        confidence=item.confidence, track_id=item.track_id, product_id=item.product_id,
        identity_status=item.identity_status,
        identity_confidence=item.identity_confidence,
        category=item.category, brand=item.brand, variant=item.variant,
        package_size=item.package_size, barcode=item.barcode,
        identity_evidence=item.identity_evidence,
        bbox=BoundingBox(x1=item.x1, y1=item.y1, x2=item.x2, y2=item.y2),
        normalized_bbox=BoundingBox(**item.normalized_bbox),
    ) for item in frame.detections]
    return VideoFrameResponse(
        id=frame.id, sequence=frame.sequence,
        source_frame_index=frame.source_frame_index, timestamp_ms=frame.timestamp_ms,
        width=frame.width, height=frame.height, inference_ms=frame.inference_ms,
        detection_count=frame.detection_count,
        annotated_image_url=(f"/video-jobs/{job_id}/frames/{frame.id}/image"
                             if frame.annotated_storage_key else None),
        detections=detections,
    )


def _bounded_options(sample_interval_seconds, max_frames, max_duration_seconds,
                     confidence_threshold, image_size, preview_only):
    effective_frames = max_frames or settings.VIDEO_MAX_FRAMES
    if preview_only:
        effective_frames = min(effective_frames, settings.VIDEO_PREVIEW_FRAMES)
    return {
        "sample_interval_seconds": sample_interval_seconds,
        "max_frames": min(effective_frames, settings.VIDEO_MAX_FRAMES),
        "max_duration_seconds": min(max_duration_seconds, settings.VIDEO_MAX_DURATION_SECONDS)
                                if max_duration_seconds else None,
        "confidence_threshold": confidence_threshold or settings.CV_CONFIDENCE_THRESHOLD,
        "image_size": image_size or settings.CV_IMAGE_SIZE,
    }


def _validate_camera_source(source_url: str) -> None:
    parsed = urlparse(source_url)
    if parsed.scheme.lower() == "webcam":
        if (not parsed.hostname or not parsed.hostname.isdecimal()
                or not 0 <= int(parsed.hostname) <= 9
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in {"", "/"}):
            raise HTTPException(422, "Webcam source must use webcam://0 through webcam://9")
        return
    if parsed.scheme.lower() not in {"rtsp", "rtsps", "http", "https"} or not parsed.hostname:
        raise HTTPException(422, "Camera source must be an approved webcam, RTSP, or HTTP URL")
    allowed = {item.strip().lower() for item in settings.VIDEO_ALLOWED_CAMERA_HOSTS.split(",")
               if item.strip()}
    host = parsed.hostname.lower()
    if host in allowed:
        return
    try:
        address = ip_address(host)
    except ValueError:
        raise HTTPException(422, "Camera host is not in VIDEO_ALLOWED_CAMERA_HOSTS")
    if not (address.is_private or address.is_loopback):
        raise HTTPException(422, "Public camera hosts must be explicitly allowlisted")


def _inspect_video(path: Path) -> tuple[float | None, int | None, int | None]:
    import cv2
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise HTTPException(422, "Uploaded file is not a readable video")
        ok, _frame = capture.read()
        if not ok:
            raise HTTPException(422, "Uploaded video contains no readable frames")
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0) or None
        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0) or None
        duration = int(total / fps * 1000) if fps and total else None
        return fps, total, duration
    finally:
        capture.release()


def _inspect_image(path: Path) -> tuple[int, int]:
    import cv2
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        raise HTTPException(422, "Uploaded file is not a readable image")
    height, width = image.shape[:2]
    return width, height


@router.post("", response_model=VideoJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_video(
    video: UploadFile = File(...),
    sample_interval_seconds: float = Form(1.0, gt=0, le=60),
    max_frames: int | None = Form(None, ge=1, le=10000),
    max_duration_seconds: float | None = Form(None, gt=0, le=86400),
    confidence_threshold: float | None = Form(None, ge=0.01, le=1.0),
    image_size: int | None = Form(None, ge=320, le=1920),
    tracking_enabled: bool = Form(True),
    preview_only: bool = Form(False),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key", max_length=128),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        safe_extension(video.filename)
    except ValueError as exc:
        raise HTTPException(415, str(exc)) from exc
    if video.content_type and video.content_type.lower() not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(415, "Unsupported video content type")
    if idempotency_key:
        existing = db.query(VideoProcessingJob).filter_by(
            owner_user_id=user.id, idempotency_key=idempotency_key).first()
        if existing:
            return _job_response(existing)
    options = _bounded_options(sample_interval_seconds, max_frames, max_duration_seconds,
                               confidence_threshold, image_size, preview_only)
    job = VideoProcessingJob(
        owner_user_id=user.id, source_kind=VideoSourceKind.UPLOAD,
        status=VideoJobStatus.CANCELLED, stage=storage_queue_stage(),
        original_filename=Path(video.filename or "video").name[:255],
        content_type=(video.content_type or "application/octet-stream")[:100],
        tracking_enabled=tracking_enabled, preview_only=preview_only,
        idempotency_key=idempotency_key, **options,
    )
    db.add(job)
    db.flush()
    key = new_upload_key(job.id, video.filename)
    path = resolve_storage_key(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    try:
        with path.open("xb") as stream:
            while chunk := await video.read(1024 * 1024):
                size += len(chunk)
                if size > settings.VIDEO_MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "Video exceeds the configured upload limit")
                stream.write(chunk)
        if size == 0:
            raise HTTPException(422, "Uploaded video is empty")
        fps, total, duration = _inspect_video(path)
        job.storage_key = key
        job.source_size_bytes = size
        job.source_fps = fps
        job.total_frames = total
        job.source_duration_ms = duration
        job.summary = {"_storage_node_id": storage_node_id()}
        audit(db, user, "create", "video_processing_job", job.id,
              new={"source_kind": "upload", "preview_only": preview_only})
        db.commit()
        db.refresh(job)
        return _job_response(job)
    except Exception:
        db.rollback()
        remove_job_media(job.id)
        raise
    finally:
        await video.close()


@router.post("/images", response_model=VideoJobResponse,
             status_code=status.HTTP_202_ACCEPTED)
async def upload_image(
    image: UploadFile = File(...),
    confidence_threshold: float | None = Form(None, ge=0.01, le=1.0),
    image_size: int | None = Form(None, ge=320, le=1920),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key", max_length=128),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        safe_image_extension(image.filename)
    except ValueError as exc:
        raise HTTPException(415, str(exc)) from exc
    if image.content_type and image.content_type.lower() not in SUPPORTED_IMAGE_CONTENT_TYPES:
        raise HTTPException(415, "Unsupported image content type")
    if idempotency_key:
        existing = db.query(VideoProcessingJob).filter_by(
            owner_user_id=user.id, idempotency_key=idempotency_key).first()
        if existing:
            return _job_response(existing)
    options = _bounded_options(
        1.0, 1, None, confidence_threshold, image_size, False,
    )
    job = VideoProcessingJob(
        owner_user_id=user.id, source_kind=VideoSourceKind.UPLOAD,
        status=VideoJobStatus.CANCELLED, stage=storage_queue_stage(),
        original_filename=Path(image.filename or "image").name[:255],
        content_type=(image.content_type or "application/octet-stream")[:100],
        tracking_enabled=False, preview_only=False,
        idempotency_key=idempotency_key, **options,
    )
    db.add(job)
    db.flush()
    key = new_image_key(job.id, image.filename)
    path = resolve_storage_key(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    try:
        with path.open("xb") as stream:
            while chunk := await image.read(1024 * 1024):
                size += len(chunk)
                if size > settings.IMAGE_MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "Image exceeds the configured upload limit")
                stream.write(chunk)
        if size == 0:
            raise HTTPException(422, "Uploaded image is empty")
        width, height = _inspect_image(path)
        job.storage_key = key
        job.source_size_bytes = size
        job.total_frames = 1
        job.source_duration_ms = 0
        job.summary = {"source_width": width, "source_height": height,
                       "_storage_node_id": storage_node_id(),
                       "inventory_effect": "review_only"}
        audit(db, user, "create", "video_processing_job", job.id,
              new={"source_kind": "image", "width": width, "height": height})
        db.commit()
        db.refresh(job)
        return _job_response(job)
    except Exception:
        db.rollback()
        remove_job_media(job.id)
        raise
    finally:
        await image.close()


@router.post("/cameras/{camera_id}", response_model=VideoJobResponse,
             status_code=status.HTTP_202_ACCEPTED)
def create_camera_job(camera_id: str, options: CameraVideoJobCreate,
                      idempotency_key: str | None = Header(None, alias="Idempotency-Key",
                                                          max_length=128),
                      db: Session = Depends(get_db), user=Depends(get_current_user)):
    camera = db.get(Camera, camera_id)
    if not camera or not camera.is_active or not camera.source_url:
        raise HTTPException(404, "Active camera source not found")
    _validate_camera_source(camera.source_url)
    if idempotency_key:
        existing = db.query(VideoProcessingJob).filter_by(
            owner_user_id=user.id, idempotency_key=idempotency_key).first()
        if existing:
            return _job_response(existing)
    bounded = _bounded_options(
        options.sample_interval_seconds, options.max_frames,
        options.max_duration_seconds or min(60, settings.VIDEO_MAX_DURATION_SECONDS),
        options.confidence_threshold, options.image_size, options.preview_only,
    )
    job = VideoProcessingJob(
        owner_user_id=user.id, camera_id=camera.id,
        status=VideoJobStatus.CANCELLED, stage=storage_queue_stage(),
        source_kind=VideoSourceKind.CAMERA, tracking_enabled=options.tracking_enabled,
        preview_only=options.preview_only, idempotency_key=idempotency_key,
        summary={"_storage_node_id": storage_node_id()}, **bounded,
    )
    db.add(job)
    db.flush()
    audit(db, user, "create", "video_processing_job", job.id,
          new={"source_kind": "camera", "camera_id": camera.id})
    db.commit()
    db.refresh(job)
    return _job_response(job)


@router.get("", response_model=VideoJobListResponse)
def list_jobs(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
              db: Session = Depends(get_db), user=Depends(get_current_user)):
    query = db.query(VideoProcessingJob)
    if "video_jobs.read_all" not in permissions_for(user):
        query = query.filter(VideoProcessingJob.owner_user_id == user.id)
    total = query.count()
    jobs = query.order_by(VideoProcessingJob.created_at.desc()).offset(offset).limit(limit).all()
    return VideoJobListResponse(data=[_job_response(job) for job in jobs], total=total,
                                limit=limit, offset=offset)


@router.get("/model-health", response_model=DetectorHealthResponse)
def model_health():
    """Read-only model/device preflight; does not download or deserialize weights."""
    from app.services.video_processing import model_service
    return DetectorHealthResponse(**model_service.health())


@router.get("/review-queue", response_model=DetectionReviewListResponse)
def review_queue(
    identity_status: str | None = Query(None, pattern="^(unknown|ambiguous|category_only)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Return unresolved evidence without exposing source URLs or filesystem keys."""
    query = (
        db.query(VideoDetection, VideoFrame, VideoProcessingJob)
        .join(VideoFrame, VideoDetection.frame_id == VideoFrame.id)
        .join(VideoProcessingJob, VideoDetection.job_id == VideoProcessingJob.id)
    )
    if "video_jobs.read_all" not in permissions_for(user):
        query = query.filter(VideoProcessingJob.owner_user_id == user.id)
    if identity_status:
        query = query.filter(VideoDetection.identity_status == identity_status)
    else:
        query = query.filter(VideoDetection.identity_status.in_(
            ("unknown", "ambiguous", "category_only")
        ))
    total = query.count()
    rows = (
        query.order_by(VideoDetection.created_at.desc()).offset(offset).limit(limit).all()
    )
    return DetectionReviewListResponse(
        data=[DetectionReviewResponse(
            id=detection.id,
            job_id=job.id,
            frame_id=frame.id,
            timestamp_ms=frame.timestamp_ms,
            class_name=detection.class_name,
            confidence=detection.confidence,
            track_id=detection.track_id,
            identity_status=detection.identity_status,
            identity_confidence=detection.identity_confidence,
            category=detection.category,
            product_id=detection.product_id,
            annotated_image_url=(
                f"/video-jobs/{job.id}/frames/{frame.id}/image"
                if frame.annotated_storage_key else None
            ),
        ) for detection, frame, job in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/detections/{detection_id}/identify", response_model=VideoDetectionResponse)
def identify_detection(
    detection_id: str,
    update: DetectionIdentityUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Resolve evidence to a catalog product without changing inventory quantity."""
    detection = db.get(VideoDetection, detection_id)
    if not detection:
        raise HTTPException(404, "Detection not found")
    job = db.get(VideoProcessingJob, detection.job_id)
    if not job or not _owns_or_can_read_all(job, user):
        raise HTTPException(404, "Detection not found")
    product = db.get(Product, update.product_id)
    if not product:
        raise HTTPException(422, "Catalog product not found")
    detection.product_id = product.id
    detection.identity_status = "identified"
    detection.identity_confidence = 1.0
    detection.category = product.category
    detection.brand = product.brand
    detection.variant = product.variant
    detection.package_size = product.package_size
    detection.barcode = product.barcode
    detection.identity_evidence = {
        "method": "manual_catalog_review",
        "reviewer_user_id": user.id,
        "catalog_sku": product.sku,
    }
    audit(db, user, "identify", "video_detection", detection.id,
          new={"product_id": product.id, "inventory_effect": "none"})
    db.commit()
    db.refresh(detection)
    return VideoDetectionResponse(
        id=detection.id, class_id=detection.class_id, class_name=detection.class_name,
        confidence=detection.confidence, track_id=detection.track_id,
        product_id=detection.product_id, identity_status=detection.identity_status,
        identity_confidence=detection.identity_confidence, category=detection.category,
        brand=detection.brand, variant=detection.variant,
        package_size=detection.package_size, barcode=detection.barcode,
        identity_evidence=detection.identity_evidence,
        bbox=BoundingBox(x1=detection.x1, y1=detection.y1,
                         x2=detection.x2, y2=detection.y2),
        normalized_bbox=BoundingBox(**detection.normalized_bbox),
    )


@router.get("/{job_id}", response_model=VideoJobResponse)
def get_job(job_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return _job_response(_get_job(db, job_id, user))


@router.get("/{job_id}/frames", response_model=VideoFrameListResponse)
def list_frames(job_id: str, limit: int = Query(50, ge=1, le=200),
                offset: int = Query(0, ge=0), db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    _get_job(db, job_id, user)
    query = (db.query(VideoFrame).options(selectinload(VideoFrame.detections))
             .filter(VideoFrame.job_id == job_id))
    total = query.count()
    frames = query.order_by(VideoFrame.sequence).offset(offset).limit(limit).all()
    return VideoFrameListResponse(data=[_frame_response(job_id, frame) for frame in frames],
                                  total=total, limit=limit, offset=offset)


@router.get("/{job_id}/frames/{frame_id}/image")
def annotated_frame(job_id: str, frame_id: str, db: Session = Depends(get_db),
                    user=Depends(get_current_user)):
    _get_job(db, job_id, user)
    frame = db.query(VideoFrame).filter_by(id=frame_id, job_id=job_id).first()
    if not frame or not frame.annotated_storage_key:
        raise HTTPException(404, "Annotated frame not found")
    path = resolve_storage_key(frame.annotated_storage_key)
    if not path.is_file():
        raise HTTPException(404, "Annotated frame not found")
    return FileResponse(path, media_type="image/jpeg",
                        headers={"Cache-Control": "private, no-store",
                                 "X-Content-Type-Options": "nosniff"})


@router.post("/{job_id}/cancel", response_model=VideoJobCancelResponse)
def cancel_job(job_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    job = _get_job(db, job_id, user)
    storage_queued = (
        job.status == VideoJobStatus.CANCELLED
        and job.stage.startswith("storage_queued:")
    )
    if job.status in {VideoJobStatus.COMPLETED, VideoJobStatus.FAILED,
                      VideoJobStatus.CANCELLED} and not storage_queued:
        raise HTTPException(409, "Video job is already in a terminal state")
    job.cancel_requested = True
    if job.status == VideoJobStatus.QUEUED or storage_queued:
        job.status = VideoJobStatus.CANCELLED
        job.stage = "cancelled"
    audit(db, user, "cancel", "video_processing_job", job.id)
    db.commit()
    return VideoJobCancelResponse(id=job.id, status=job.status,
                                  cancel_requested=job.cancel_requested)


@router.post("/{job_id}/retry", response_model=VideoJobResponse,
             status_code=status.HTTP_202_ACCEPTED)
def retry_job(job_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Safely requeue a failed job without duplicating persisted evidence."""
    job = _get_job(db, job_id, user)
    if job.status != VideoJobStatus.FAILED:
        raise HTTPException(409, "Only failed video-processing jobs can be retried")
    if job.source_kind == VideoSourceKind.UPLOAD:
        try:
            source = resolve_storage_key(job.storage_key or "")
        except ValueError as exc:
            raise HTTPException(409, "The uploaded source reference is invalid; upload the file again") from exc
        if not source.is_file():
            raise HTTPException(
                409,
                "The uploaded source is no longer available; upload the file again",
            )

    # A failed run may have committed partial frames. Remove database evidence
    # before requeueing; annotated files use deterministic names and are safely
    # overwritten by the next run without touching the uploaded source.
    db.query(VideoDetection).filter(VideoDetection.job_id == job.id).delete(
        synchronize_session=False
    )
    db.query(VideoFrame).filter(VideoFrame.job_id == job.id).delete(
        synchronize_session=False
    )
    job.status = VideoJobStatus.CANCELLED
    job.stage = storage_queue_stage()
    job.cancel_requested = False
    job.frames_processed = 0
    job.detection_instances = 0
    job.frames_with_detections = 0
    job.unique_tracked_objects = None
    job.error_message = None
    job.started_at = None
    job.completed_at = None
    job.summary = {**(job.summary or {}), "_storage_node_id": storage_node_id()}
    audit(db, user, "retry", "video_processing_job", job.id,
          new={"source_kind": job.source_kind.value})
    db.commit()
    db.refresh(job)
    return _job_response(job)
