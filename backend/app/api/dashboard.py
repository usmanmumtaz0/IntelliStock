"""
Dashboard endpoints for overview metrics and KPIs.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.inventory import Inventory, InventoryStatus
from app.models.camera import Camera
from app.models.product import Product
from app.models.zone import ShelfZone

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


class DashboardMetrics(BaseModel):
    total_skus: int
    active_cameras: int
    total_cameras: int
    low_stock_alerts: int
    reconciliation_confidence: float


@router.get("/metrics", response_model=DashboardMetrics)
def get_dashboard_metrics(db: Session = Depends(get_db)):
    """
    Get key performance indicators for the dashboard.
    """
    # Count unique products across all zones
    total_skus = db.query(Product).count()
    
    # Count active and total cameras
    total_cameras = db.query(Camera).count()
    active_cameras = db.query(Camera).filter(Camera.is_active == True).count()
    
    # Count low stock alerts
    low_stock_count = db.query(Inventory).filter(
        Inventory.status.in_([InventoryStatus.LOW_STOCK, InventoryStatus.OUT_OF_STOCK])
    ).count()
    
    # Calculate average reconciliation confidence (last 15 min)
    # For now, use overall average; can be enhanced to use time windows
    inv_records = db.query(Inventory).all()
    avg_confidence = 0.0
    if inv_records:
        avg_confidence = (sum(i.confidence for i in inv_records) / len(inv_records)) * 100
    
    return DashboardMetrics(
        total_skus=total_skus,
        active_cameras=active_cameras,
        total_cameras=total_cameras,
        low_stock_alerts=low_stock_count,
        reconciliation_confidence=round(avg_confidence, 1),
    )


class StoreLocationMetadata(BaseModel):
    name: str
    location: str
    floor: str


@router.get("/store-info", response_model=StoreLocationMetadata)
def get_store_info():
    """Get store/location metadata for the dashboard."""
    return StoreLocationMetadata(
        name="IntelliStock",
        location="Downtown Flagship",
        floor="Floor 1",
    )
