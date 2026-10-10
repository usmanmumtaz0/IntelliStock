"""
Camera endpoints for CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.camera import Camera
from app.schemas.camera import CameraCreate, CameraUpdate, CameraResponse
from app.core.security import require_roles
from app.models.zone import ShelfZone
from app.models.inventory import Inventory, InventoryStatus
from app.models.event import InventoryEvent
from app.services.operations import audit
from app.services.outbox import enqueue
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/api/v1/cameras", tags=["cameras"])


@router.get("", response_model=List[CameraResponse])
def list_cameras(db: Session = Depends(get_db)):
    """List all cameras."""
    cameras = db.query(Camera).all()
    return cameras


@router.get("/{camera_id}", response_model=CameraResponse)
def get_camera(camera_id: str, db: Session = Depends(get_db)):
    """Get a specific camera by ID."""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    return camera


@router.post(
    "",
    response_model=CameraResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("admin", "manager"))],
)
def create_camera(camera: CameraCreate, db: Session = Depends(get_db), user=Depends(require_roles("admin", "manager"))):
    """Create a new camera."""
    db_camera = Camera(**camera.dict())
    db.add(db_camera)
    db.flush()
    audit(db, user, "create", "camera", db_camera.id, new={"name": camera.name, "location": camera.location})
    enqueue(db, "configuration_updated", {"resource": "cameras"})
    db.commit()
    db.refresh(db_camera)
    return db_camera


@router.put(
    "/{camera_id}",
    response_model=CameraResponse,
    dependencies=[Depends(require_roles("admin", "manager"))],
)
def update_camera(camera_id: str, camera: CameraUpdate, db: Session = Depends(get_db), user=Depends(require_roles("admin", "manager"))):
    """Update a camera."""
    db_camera = db.query(Camera).filter(Camera.id == camera_id).with_for_update().first()
    if not db_camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    
    update_data = camera.dict(exclude_unset=True)
    old = {key: ("[redacted]" if key == "source_url" else getattr(db_camera, key)) for key in update_data}
    for field, value in update_data.items():
        setattr(db_camera, field, value)
    
    if update_data.get("is_active") is False:
        for inv in db.query(Inventory).join(ShelfZone).filter(ShelfZone.camera_id == camera_id).with_for_update(of=Inventory).all():
            inv.status = InventoryStatus.CAMERA_OFFLINE
    audit(db, user, "update", "camera", camera_id, old,
          {key: ("[redacted]" if key == "source_url" else value) for key, value in update_data.items()})
    enqueue(db, "configuration_updated", {"resource": "cameras", "camera_id": camera_id})
    db.commit()
    db.refresh(db_camera)
    return db_camera


@router.delete(
    "/{camera_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("admin"))],
)
def delete_camera(camera_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    """Delete a camera."""
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    
    if db.query(ShelfZone).filter_by(camera_id=camera_id).first() or db.query(InventoryEvent).filter_by(camera_id=camera_id).first():
        raise HTTPException(409, "Camera has shelf zones or history. Disable it instead.")
    audit(db, user, "delete", "camera", camera_id, old={"name": db_camera.name})
    db.delete(db_camera)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Camera is still referenced")
    return None
