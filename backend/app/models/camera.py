"""
Camera model for video source configuration.
"""
from sqlalchemy import Column, String, Float, Boolean, Integer
from app.models.base import BaseModel


class Camera(BaseModel):
    """Camera model for monitoring sources."""

    __tablename__ = "cameras"

    name = Column(String(255), nullable=False, index=True)
    location = Column(String(255), nullable=False)
    source_url = Column(String(512), nullable=True)  # RTSP, HTTP, or file path
    fps = Column(Integer, default=2, nullable=False)  # Frames per second sampling rate
    offline_timeout_seconds = Column(Integer, default=30, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    calibration_notes = Column(String(1024), nullable=True)

    def __repr__(self):
        return f"<Camera {self.name}>"
