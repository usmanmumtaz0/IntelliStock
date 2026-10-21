"""
Product model for inventory items.
"""
from sqlalchemy import Column, String, Integer, JSON
from app.models.base import BaseModel


class Product(BaseModel):
    """Product model for inventory items."""

    __tablename__ = "products"

    sku = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1024), nullable=True)
    brand = Column(String(100), nullable=True, index=True)
    category = Column(String(100), nullable=True, index=True)
    variant = Column(String(100), nullable=True)
    package_size = Column(String(64), nullable=True)
    barcode = Column(String(64), unique=True, nullable=True, index=True)
    reference_images = Column(JSON, nullable=True)
    
    # Thresholds for this product across all zones
    low_stock_threshold = Column(Integer, default=10, nullable=False)
    reorder_point = Column(Integer, default=50, nullable=False)
    
    # Optional image URL for visual identification
    image_url = Column(String(512), nullable=True)

    def __repr__(self):
        return f"<Product {self.sku}>"
