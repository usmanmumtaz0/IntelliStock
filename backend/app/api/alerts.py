"""
Alerts endpoints for monitoring and event notifications.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

from app.database import get_db
from app.models.event import InventoryEvent
from app.models.inventory import Inventory, InventoryStatus
from app.models.camera import Camera
from app.models.zone import ShelfZone

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


class AlertResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    type: str  # "low_stock" | "camera_offline" | "anomaly"
    severity: str  # "critical" | "warning" | "info"
    title: str
    detail: str
    zone: str
    sku: str | None
    min_ago: int = Field(alias="minAgo")
    acknowledged: bool

@router.get("", response_model=List[AlertResponse])
def list_alerts(
    acknowledged: Optional[bool] = Query(None),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    List all alerts with optional filters.
    Alerts are derived from inventory status, camera heartbeats, and events.
    """
    alerts = []
    now = datetime.utcnow()
    
    # 1. Camera offline alerts
    cameras = db.query(Camera).filter(Camera.is_active == False).all()
    for camera in cameras:
        zones = db.query(ShelfZone).filter(ShelfZone.camera_id == camera.id).all()
        for zone in zones:
            alert = AlertResponse(
                id=f"cam-offline-{camera.id}",
                type="camera_offline",
                severity="critical",
                title=f"{camera.name} offline",
                detail=f"No heartbeat received. Zone {zone.name} counts frozen.",
                zone=zone.name,
                sku=None,
                min_ago=0,  # TODO: compute from last heartbeat
                acknowledged=False,
            )
            alerts.append(alert)
    
    # 2. Low stock / out of stock alerts
    low_stock_items = db.query(Inventory).filter(
        Inventory.status.in_([InventoryStatus.LOW_STOCK, InventoryStatus.OUT_OF_STOCK])
    ).all()
    for item in low_stock_items:
        product = item.product
        zone = item.zone
        
        severity = "critical" if item.status == InventoryStatus.OUT_OF_STOCK else "warning"
        status_str = "Out of stock" if item.status == InventoryStatus.OUT_OF_STOCK else "Low stock"
        
        last_obs = item.last_observation_time
        min_ago = 0
        if last_obs:
            try:
                obs_time = datetime.fromisoformat(last_obs)
                min_ago = int((now - obs_time).total_seconds() / 60)
            except:
                pass
        
        alert = AlertResponse(
            id=f"low-stock-{item.id}",
            type="low_stock",
            severity=severity,
            title=f"{status_str}: {product.name}",
            detail=f"Verified count {item.quantity_estimate} (threshold TBD).",
            zone=zone.name,
            sku=product.sku if hasattr(product, 'sku') else None,
            min_ago=min_ago,
            acknowledged=False,
        )
        alerts.append(alert)
    
    # Apply filters
    if acknowledged is not None:
        alerts = [a for a in alerts if a.acknowledged == acknowledged]
    if severity:
        alerts = [a for a in alerts if a.severity == severity]
    
    return alerts


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: str, db: Session = Depends(get_db)):
    """Get a specific alert."""
    # TODO: Implement alert storage in DB for retrieval
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Alert retrieval not yet implemented")


@router.post("/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, db: Session = Depends(get_db)):
    """Mark an alert as acknowledged."""
    # TODO: Implement alert acknowledgment storage
    return {"acknowledged": True, "alert_id": alert_id}


@router.post("/acknowledge-all")
def acknowledge_all_alerts(db: Session = Depends(get_db)):
    """Acknowledge all unacknowledged alerts."""
    # TODO: Implement bulk acknowledgment
    return {"acknowledged_count": 0}
