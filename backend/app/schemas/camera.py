"""
Camera schemas for request/response validation.
"""
from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional
from datetime import datetime


class CameraCreate(BaseModel):
    """Schema for creating a camera."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=255)
    location: str = Field(..., min_length=1, max_length=255)
    source_url: Optional[str] = Field(None, max_length=512)
    fps: int = Field(2, ge=1, le=30)
    offline_timeout_seconds: int = Field(30, ge=10, le=300)


class CameraUpdate(BaseModel):
    """Schema for updating a camera."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    location: Optional[str] = Field(None, min_length=1, max_length=255)
    source_url: Optional[str] = Field(None, max_length=512)
    fps: Optional[int] = Field(None, ge=1, le=30)
    is_active: Optional[bool] = None
    offline_timeout_seconds: Optional[int] = Field(None, ge=10, le=300)

    @model_validator(mode="after")
    def reject_null_fields(self):
        for name in self.model_fields_set - {"source_url"}:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class CameraResponse(BaseModel):
    """Schema for camera response."""

    id: str
    name: str
    location: str
    source_url: Optional[str]
    fps: int
    offline_timeout_seconds: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
