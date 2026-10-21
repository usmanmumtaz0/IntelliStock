"""Public contracts for video processing without filesystem or camera secrets."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.video_job import VideoJobStatus, VideoSourceKind


class VideoJobOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sample_interval_seconds: float = Field(default=1.0, gt=0, le=60)
    max_frames: int | None = Field(default=None, ge=1, le=10000)
    max_duration_seconds: float | None = Field(default=None, gt=0, le=86400)
    confidence_threshold: float | None = Field(default=None, ge=0.01, le=1.0)
    image_size: int | None = Field(default=None, ge=320, le=1920)
    tracking_enabled: bool = True
    preview_only: bool = False


class CameraVideoJobCreate(VideoJobOptions):
    pass


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class VideoDetectionResponse(BaseModel):
    id: str
    class_id: int
    class_name: str
    confidence: float
    track_id: int | None
    product_id: str | None
    identity_status: str
    identity_confidence: float
    category: str | None
    brand: str | None
    variant: str | None
    package_size: str | None
    barcode: str | None
    identity_evidence: dict | None
    bbox: BoundingBox
    normalized_bbox: BoundingBox


class VideoFrameResponse(BaseModel):
    id: str
    sequence: int
    source_frame_index: int
    timestamp_ms: int
    width: int
    height: int
    inference_ms: float
    detection_count: int
    annotated_image_url: str | None
    detections: list[VideoDetectionResponse] = Field(default_factory=list)


class VideoJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    owner_user_id: str
    camera_id: str | None
    source_kind: VideoSourceKind
    status: VideoJobStatus
    original_filename: str | None
    content_type: str | None
    source_size_bytes: int | None
    sample_interval_seconds: float
    max_frames: int
    max_duration_seconds: float | None
    confidence_threshold: float
    image_size: int
    tracking_enabled: bool
    preview_only: bool
    cancel_requested: bool
    stage: str
    frames_processed: int
    total_frames: int | None
    source_fps: float | None
    source_duration_ms: int | None
    detection_instances: int
    frames_with_detections: int
    unique_tracked_objects: int | None
    summary: dict | None
    error_message: str | None
    started_at: str | None
    completed_at: str | None
    created_at: datetime
    updated_at: datetime


class VideoJobListResponse(BaseModel):
    data: list[VideoJobResponse]
    total: int
    limit: int
    offset: int


class VideoFrameListResponse(BaseModel):
    data: list[VideoFrameResponse]
    total: int
    limit: int
    offset: int


class VideoJobCancelResponse(BaseModel):
    id: str
    status: VideoJobStatus
    cancel_requested: bool


class DetectionReviewResponse(BaseModel):
    id: str
    job_id: str
    frame_id: str
    timestamp_ms: int
    class_name: str
    confidence: float
    track_id: int | None
    identity_status: str
    identity_confidence: float
    category: str | None
    product_id: str | None
    annotated_image_url: str | None


class DetectionReviewListResponse(BaseModel):
    data: list[DetectionReviewResponse]
    total: int
    limit: int
    offset: int


class DetectionIdentityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: str


class DetectorHealthResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
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
    error: str | None
    identity_evidence: dict = Field(default_factory=dict)
