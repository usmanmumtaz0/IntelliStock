"""
Zones endpoints for shelf management and health status.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.database import get_db
from app.models.zone import ShelfZone
from app.models.inventory import Inventory, InventoryStatus
from app.models.camera import Camera
from app.models.product import Product
from app.models.delivery import ZoneProductMapping
from app.schemas.zone import ZoneInput
from app.core.security import require_roles
from app.services.operations import audit
from app.services.outbox import enqueue
import json
from datetime import datetime

router = APIRouter(prefix="/api/v1/zones", tags=["zones"])


def configuration(db, zone):
    return {"id": zone.id, "camera_id": zone.camera_id, "name": zone.name,
            "description": zone.description, "polygon": json.loads(zone.roi_polygon),
            "detection_confidence_threshold": zone.detection_confidence_threshold,
            "products": [{"class_id": m.class_id, "product_id": m.product_id,
                          "allow_empty": m.allow_empty} for m in
                         db.query(ZoneProductMapping).filter_by(zone_id=zone.id).order_by(ZoneProductMapping.class_id).all()],
            "restart_required": True}


@router.get("/{zone_id}/configuration")
def get_configuration(zone_id: str, db: Session = Depends(get_db)):
    zone = db.get(ShelfZone, zone_id)
    if not zone:
        raise HTTPException(404, "Zone not found")
    return configuration(db, zone)


def save_configuration(db, data, user, zone=None):
    camera = db.query(Camera).filter_by(id=data.camera_id).with_for_update().first()
    if not camera:
        raise HTTPException(404, "Camera not found")
    if camera.is_active:
        raise HTTPException(409, "Disable this camera and stop its vision worker before changing shelf configuration")
    if zone and zone.camera_id != camera.id:
        raise HTTPException(409, "An existing zone cannot be moved to another camera")
    duplicate = db.query(ShelfZone).filter_by(camera_id=camera.id, name=data.name).first()
    if duplicate and (zone is None or duplicate.id != zone.id):
        raise HTTPException(409, "Zone name already exists on this camera")
    for mapping in data.products:
        if not db.get(Product, mapping.product_id):
            raise HTTPException(422, "Mapped product does not exist")
    old = configuration(db, zone) if zone else None
    if zone is None:
        zone = ShelfZone(camera_id=camera.id)
        db.add(zone)
    else:
        existing_products = {m.product_id for m in db.query(ZoneProductMapping).filter_by(zone_id=zone.id).all()}
        removed = existing_products - {m.product_id for m in data.products}
        if removed and db.query(Inventory).filter(Inventory.zone_id == zone.id, Inventory.product_id.in_(removed)).first():
            raise HTTPException(409, "Cannot remove a product mapping with inventory; retain it to preserve monitoring")
        db.query(ZoneProductMapping).filter_by(zone_id=zone.id).delete(synchronize_session=False)
        db.flush()
    zone.name, zone.description = data.name, data.description
    zone.roi_polygon = json.dumps(data.polygon)
    zone.detection_confidence_threshold = data.detection_confidence_threshold
    # Invalidate already-running workers, even if an operator quickly re-enables the camera.
    camera.updated_at = datetime.utcnow()
    if zone.id:
        for inv in db.query(Inventory).filter_by(zone_id=zone.id).with_for_update().all():
            inv.status = InventoryStatus.CAMERA_OFFLINE
    db.flush()
    for mapping in data.products:
        db.add(ZoneProductMapping(zone_id=zone.id, **mapping.model_dump()))
    db.flush()
    result = configuration(db, zone)
    audit(db, user, "configure", "zone", zone.id, old, result)
    enqueue(db, "configuration_updated", {"resource": "zones", "camera_id": camera.id})
    db.commit()
    return result


@router.post("", status_code=201)
def create_zone(data: ZoneInput, db: Session = Depends(get_db), user=Depends(require_roles("admin", "manager"))):
    return save_configuration(db, data, user)


@router.put("/{zone_id}")
def update_zone(zone_id: str, data: ZoneInput, db: Session = Depends(get_db), user=Depends(require_roles("admin", "manager"))):
    # Camera lock precedes zone lock, consistent with configuration creation.
    db.query(Camera).filter_by(id=data.camera_id).with_for_update().first()
    zone = db.query(ShelfZone).filter_by(id=zone_id).with_for_update().first()
    if not zone:
        raise HTTPException(404, "Zone not found")
    return save_configuration(db, data, user, zone)


def zone_health(camera, inventories, confidence):
    states = {item.status for item in inventories}
    if not camera or not camera.is_active or InventoryStatus.CAMERA_OFFLINE in states:
        return "offline"
    if (not inventories or confidence < 0.6 or
            states.intersection({InventoryStatus.UNKNOWN, InventoryStatus.DETECTION_UNCERTAIN})):
        return "pending"
    return "low" if states.intersection({InventoryStatus.LOW_STOCK, InventoryStatus.OUT_OF_STOCK}) else "healthy"


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
        
        health = zone_health(camera, inv_records, avg_confidence)
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
    
    health = zone_health(camera, inv_records, avg_confidence)
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
