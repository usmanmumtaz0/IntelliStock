"""
Product schemas for request/response validation.
"""
from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional
from datetime import datetime


class ProductCreate(BaseModel):
    """Schema for creating a product."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    sku: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1024)
    brand: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    variant: Optional[str] = Field(None, max_length=100)
    package_size: Optional[str] = Field(None, max_length=64)
    barcode: Optional[str] = Field(None, max_length=64)
    reference_images: Optional[list[str]] = Field(None, max_length=20)
    low_stock_threshold: int = Field(10, ge=0, le=1_000_000)
    reorder_point: int = Field(50, ge=0, le=1_000_000)
    image_url: Optional[str] = Field(None, max_length=512)


class ProductUpdate(BaseModel):
    """Schema for updating a product."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1024)
    brand: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    variant: Optional[str] = Field(None, max_length=100)
    package_size: Optional[str] = Field(None, max_length=64)
    barcode: Optional[str] = Field(None, max_length=64)
    reference_images: Optional[list[str]] = Field(None, max_length=20)
    low_stock_threshold: Optional[int] = Field(None, ge=0, le=1_000_000)
    reorder_point: Optional[int] = Field(None, ge=0, le=1_000_000)

    @model_validator(mode="after")
    def reject_null_fields(self):
        for name in self.model_fields_set - {
            "description", "brand", "category", "variant", "package_size", "barcode",
            "reference_images",
        }:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class ProductResponse(BaseModel):
    """Schema for product response."""

    id: str
    sku: str
    name: str
    description: Optional[str]
    brand: Optional[str]
    category: Optional[str]
    variant: Optional[str]
    package_size: Optional[str]
    barcode: Optional[str]
    reference_images: Optional[list[str]]
    low_stock_threshold: int
    reorder_point: int
    image_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
