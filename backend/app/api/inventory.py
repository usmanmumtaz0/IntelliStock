"""
Inventory endpoints for querying state and reconciliation testing.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.inventory import Inventory, InventoryStatus
from app.schemas.inventory import InventoryResponse, InventoryListResponse
from app.services.reconciliation import ReconciliationEngine

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


class ReconcileRequest(BaseModel):
    """Request to reconcile an observation."""
    camera_id: str
    zone_id: str
    product_id: str
    observed_quantity: int
    confidence: float


@router.get("", response_model=List[InventoryListResponse])
def list_inventory(
    zone_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    status: Optional[InventoryStatus] = Query(None),
    db: Session = Depends(get_db),
):
    """List inventory with optional filters."""
    query = db.query(Inventory)
    
    if zone_id:
        query = query.filter(Inventory.zone_id == zone_id)
    if product_id:
        query = query.filter(Inventory.product_id == product_id)
    if status:
        query = query.filter(Inventory.status == status)
    
    inventory = query.all()
    return inventory


@router.get("/{inventory_id}", response_model=InventoryResponse)
def get_inventory(inventory_id: str, db: Session = Depends(get_db)):
    """Get a specific inventory record."""
    inv = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory not found")
    return inv


@router.get("/zone/{zone_id}", response_model=List[InventoryListResponse])
def list_inventory_by_zone(zone_id: str, db: Session = Depends(get_db)):
    """Get all inventory for a specific zone."""
    inventory = db.query(Inventory).filter(Inventory.zone_id == zone_id).all()
    return inventory


@router.get("/product/{product_id}", response_model=List[InventoryListResponse])
def list_inventory_by_product(product_id: str, db: Session = Depends(get_db)):
    """Get all inventory for a specific product across all zones."""
    inventory = db.query(Inventory).filter(Inventory.product_id == product_id).all()
    return inventory


@router.get("/status/low-stock", response_model=List[InventoryListResponse])
def get_low_stock_items(db: Session = Depends(get_db)):
    """Get all items with low stock status."""
    inventory = db.query(Inventory).filter(
        Inventory.status.in_([InventoryStatus.LOW_STOCK, InventoryStatus.OUT_OF_STOCK])
    ).all()
    return inventory


@router.post("/reconcile")
def reconcile_observation(
    request: ReconcileRequest,
    db: Session = Depends(get_db),
):
    """
    Test endpoint: reconcile an observation and update inventory state.
    Used for Phase 4 testing and CV pipeline integration.
    """
    engine = ReconciliationEngine(db)
    accepted, reason = engine.reconcile_observation(
        camera_id=request.camera_id,
        zone_id=request.zone_id,
        product_id=request.product_id,
        observed_quantity=request.observed_quantity,
        confidence=request.confidence,
    )
    
    return {
        "accepted": accepted,
        "reason": reason,
        "request": request.dict(),
    }

