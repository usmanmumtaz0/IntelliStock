"""
Zones endpoints for shelf management and health status.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.database import get_db
from app.models.zone import ShelfZone
from app.models.inventory import Inventory
from app.models.camera import Camera

router = APIRouter(prefix="/api/v1/zones", tags=["zones"])


class ZoneResponse(BaseModel):
    id: str
    name: str
    description: str | None
    camera_id: str
    camera_name: str
    health: str  # "healthy" | "low" | "offline" | "pending"
    skus: int
    confidence: float
    aisle: str
    label: str

    class Config:
        from_attributes = True


@router.get("", response_model=List[ZoneResponse])
def list_zones(db: Session = Depends(get_db)):
    """
    List all shelf zones with computed health status.
    Health is computed from inventory and camera status.
    """
    zones = db.query(ShelfZone).all()
    result = []
    
    for zone in zones:
        # Get camera info
        camera = db.query(Camera).filter(Camera.id == zone.camera_id).first()
        
        # Count SKUs in this zone
        skus_count = db.query(Inventory).filter(Inventory.zone_id == zone.id).count()
        
        # Compute average confidence for the zone
        inv_records = db.query(Inventory).filter(Inventory.zone_id == zone.id).all()
        avg_confidence = sum(i.confidence for i in inv_records) / len(inv_records) if inv_records else 0.0
        
        # Determine zone health
        if camera and not camera.is_active:
            health = "offline"
        elif avg_confidence < 0.75:
            health = "pending"
        else:
            # Check for low stock items
            low_stock = db.query(Inventory).filter(
                Inventory.zone_id == zone.id,
                Inventory.status.in_(["low_stock", "out_of_stock"])
            ).count()
            health = "low" if low_stock > 0 else "healthy"
        
        # Parse aisle from zone name (e.g., "A-1" -> aisle="A")
        aisle = zone.name[0] if zone.name else "?"
        label = zone.description or zone.name
        
        result.append(ZoneResponse(
            id=zone.id,
            name=zone.name,
            description=zone.description,
            camera_id=zone.camera_id,
            camera_name=camera.name if camera else "Unknown",
            health=health,
            skus=skus_count,
            confidence=avg_confidence * 100,
            aisle=aisle,
            label=label,
        ))
    
    return result


@router.get("/{zone_id}", response_model=ZoneResponse)
def get_zone(zone_id: str, db: Session = Depends(get_db)):
    """Get a specific zone with health status."""
    zone = db.query(ShelfZone).filter(ShelfZone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    
    camera = db.query(Camera).filter(Camera.id == zone.camera_id).first()
    inv_records = db.query(Inventory).filter(Inventory.zone_id == zone.id).all()
    avg_confidence = sum(i.confidence for i in inv_records) / len(inv_records) if inv_records else 0.0
    
    if camera and not camera.is_active:
        health = "offline"
    elif avg_confidence < 0.75:
        health = "pending"
    else:
        low_stock = db.query(Inventory).filter(
            Inventory.zone_id == zone.id,
            Inventory.status.in_(["low_stock", "out_of_stock"])
        ).count()
        health = "low" if low_stock > 0 else "healthy"
    
    aisle = zone.name[0] if zone.name else "?"
    label = zone.description or zone.name
    
    return ZoneResponse(
        id=zone.id,
        name=zone.name,
        description=zone.description,
        camera_id=zone.camera_id,
        camera_name=camera.name if camera else "Unknown",
        health=health,
        skus=len(inv_records),
        confidence=avg_confidence * 100,
        aisle=aisle,
        label=label,
    )
