"""
Product schemas for request/response validation.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProductCreate(BaseModel):
    """Schema for creating a product."""

    sku: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1024)
    low_stock_threshold: int = Field(10, ge=0)
    reorder_point: int = Field(50, ge=0)
    image_url: Optional[str] = Field(None, max_length=512)


class ProductUpdate(BaseModel):
    """Schema for updating a product."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1024)
    low_stock_threshold: Optional[int] = Field(None, ge=0)
    reorder_point: Optional[int] = Field(None, ge=0)


class ProductResponse(BaseModel):
    """Schema for product response."""

    id: str
    sku: str
    name: str
    description: Optional[str]
    low_stock_threshold: int
    reorder_point: int
    image_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
