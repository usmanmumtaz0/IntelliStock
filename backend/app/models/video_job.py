"""Persistent video processing jobs and frame-level detection evidence."""
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class VideoJobStatus(str, PyEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VideoSourceKind(str, PyEnum):
    UPLOAD = "upload"
    CAMERA = "camera"


class VideoProcessingJob(BaseModel):
    __tablename__ = "video_processing_jobs"

    owner_user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    camera_id = Column(String(36), ForeignKey("cameras.id"), nullable=True, index=True)
    source_kind = Column(SQLEnum(VideoSourceKind), nullable=False, index=True)
    idempotency_key = Column(String(128), nullable=True)
    status = Column(SQLEnum(VideoJobStatus), default=VideoJobStatus.QUEUED,
                    nullable=False, index=True)
    original_filename = Column(String(255), nullable=True)
    storage_key = Column(String(512), nullable=True)
    content_type = Column(String(100), nullable=True)
    source_size_bytes = Column(Integer, nullable=True)
    sample_interval_seconds = Column(Float, nullable=False, default=1.0)
    max_frames = Column(Integer, nullable=False, default=300)
    max_duration_seconds = Column(Float, nullable=True)
    confidence_threshold = Column(Float, nullable=False, default=0.4)
    image_size = Column(Integer, nullable=False, default=640)
    tracking_enabled = Column(Boolean, nullable=False, default=True)
    preview_only = Column(Boolean, nullable=False, default=False)
    cancel_requested = Column(Boolean, nullable=False, default=False)
    stage = Column(String(64), nullable=False, default="queued")
    frames_processed = Column(Integer, nullable=False, default=0)
    total_frames = Column(Integer, nullable=True)
    source_fps = Column(Float, nullable=True)
    source_duration_ms = Column(Integer, nullable=True)
    detection_instances = Column(Integer, nullable=False, default=0)
    frames_with_detections = Column(Integer, nullable=False, default=0)
    unique_tracked_objects = Column(Integer, nullable=True)
    summary = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(String(40), nullable=True)
    completed_at = Column(String(40), nullable=True)
    agent_run_id = Column(String(36), ForeignKey("agent_runs.id"), nullable=True)

    frames = relationship("VideoFrame", cascade="all, delete-orphan",
                          back_populates="job", order_by="VideoFrame.sequence")


Index("uq_video_jobs_owner_idempotency", VideoProcessingJob.owner_user_id,
      VideoProcessingJob.idempotency_key, unique=True)


class VideoFrame(BaseModel):
    __tablename__ = "video_frames"
    __table_args__ = (
        Index("uq_video_frames_job_sequence", "job_id", "sequence", unique=True),
        Index("ix_video_frames_job_timestamp", "job_id", "timestamp_ms"),
    )

    job_id = Column(String(36), ForeignKey("video_processing_jobs.id", ondelete="CASCADE"),
                    nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    source_frame_index = Column(Integer, nullable=False)
    timestamp_ms = Column(Integer, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    inference_ms = Column(Float, nullable=False, default=0.0)
    annotated_storage_key = Column(String(512), nullable=True)
    detection_count = Column(Integer, nullable=False, default=0)

    job = relationship("VideoProcessingJob", back_populates="frames")
    detections = relationship("VideoDetection", cascade="all, delete-orphan",
                              back_populates="frame")


class VideoDetection(BaseModel):
    __tablename__ = "video_detections"
    __table_args__ = (
        Index("ix_video_detections_job_class", "job_id", "class_id"),
        Index("ix_video_detections_job_track", "job_id", "track_id"),
    )

    job_id = Column(String(36), ForeignKey("video_processing_jobs.id", ondelete="CASCADE"),
                    nullable=False, index=True)
    frame_id = Column(String(36), ForeignKey("video_frames.id", ondelete="CASCADE"),
                      nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=True, index=True)
    class_id = Column(Integer, nullable=False)
    class_name = Column(String(255), nullable=False)
    confidence = Column(Float, nullable=False)
    track_id = Column(Integer, nullable=True)
    x1 = Column(Float, nullable=False)
    y1 = Column(Float, nullable=False)
    x2 = Column(Float, nullable=False)
    y2 = Column(Float, nullable=False)
    normalized_bbox = Column(JSON, nullable=False)
    identity_status = Column(String(32), nullable=False, default="unknown", index=True)
    identity_confidence = Column(Float, nullable=False, default=0.0)
    category = Column(String(100), nullable=True, index=True)
    brand = Column(String(100), nullable=True)
    variant = Column(String(100), nullable=True)
    package_size = Column(String(64), nullable=True)
    barcode = Column(String(64), nullable=True)
    identity_evidence = Column(JSON, nullable=True)

    frame = relationship("VideoFrame", back_populates="detections")
