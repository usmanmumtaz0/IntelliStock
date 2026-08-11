"""
Zone model for shelf ROI definitions.
"""
from sqlalchemy import Column, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class ShelfZone(BaseModel):
    """Shelf zone model for ROI definitions."""

    __tablename__ = "shelf_zones"

    camera_id = Column(String(36), ForeignKey("cameras.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(512), nullable=True)
    
    # ROI polygon stored as JSON: [[x1,y1], [x2,y2], ...]
    roi_polygon = Column(Text, nullable=False)  # JSON array of coordinates
    
    # Confidence thresholds for this camera/zone pair
    detection_confidence_threshold = Column(Float, default=0.6, nullable=False)
    
    camera = relationship("Camera")

    def __repr__(self):
        return f"<ShelfZone {self.name}>"
