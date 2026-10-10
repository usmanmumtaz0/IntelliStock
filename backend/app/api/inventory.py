"""
Inventory endpoints for querying state and reconciliation testing.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.inventory import Inventory, InventoryStatus
from app.schemas.inventory import InventoryListResponse, InventoryResponse
from app.services.reconciliation import ReconciliationEngine
from app.core.security import require_roles
from app.repositories.inventory_repository import InventoryRepository
from app.services.inventory_contract import serialize_inventory

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


class CorrectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    quantity: int = Field(ge=0, le=1000000, strict=True)
    reason: str = Field(min_length=5, max_length=255)
    expected_updated_at: datetime


@router.post("/{inventory_id}/corrections", response_model=InventoryResponse)
def correct_inventory(inventory_id: str, data: CorrectionRequest,
                      db: Session = Depends(get_db), user=Depends(require_roles("admin", "manager"))):
    from app.services.operations import correct_inventory as apply_correction
    from app.services.observation_window import get_observation_window
    inv = apply_correction(db, inventory_id, data, user)
    db.commit()
    get_observation_window(inv.zone.camera_id, inv.zone_id, inv.product_id).clear()
    return serialize_inventory(inv)


class ReconcileRequest(BaseModel):
    """Request to reconcile an observation."""

    camera_id: str
    zone_id: str
    product_id: str
    observed_quantity: int
    confidence: float


@router.get("", response_model=List[InventoryListResponse])
def list_inventory(
    response: Response,
    zone_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    status: Optional[InventoryStatus] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List authoritative inventory with validated filters and pagination headers."""
    records, total = InventoryRepository(db).list(
        zone_id=zone_id,
        product_id=product_id,
        inventory_status=status,
        limit=limit,
        offset=offset,
    )
    response.headers["X-Total-Count"] = str(total)
    response.headers["Content-Range"] = (
        f"items {offset}-{offset + len(records) - 1}/{total}" if records else f"items */{total}"
    )
    return [serialize_inventory(item) for item in records]


@router.get("/{inventory_id}", response_model=InventoryResponse)
def get_inventory(inventory_id: str, db: Session = Depends(get_db)):
    """Get a specific inventory record."""
    inv = InventoryRepository(db).get(inventory_id)
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory not found")
    return serialize_inventory(inv)


@router.get("/zone/{zone_id}", response_model=List[InventoryListResponse])
def list_inventory_by_zone(zone_id: str, db: Session = Depends(get_db)):
    """Get all inventory for a specific zone."""
    inventory = InventoryRepository(db).by_zone(zone_id)
    return [serialize_inventory(item) for item in inventory]


@router.get("/product/{product_id}", response_model=List[InventoryListResponse])
def list_inventory_by_product(product_id: str, db: Session = Depends(get_db)):
    """Get all inventory for a specific product across all zones."""
    inventory = InventoryRepository(db).by_product(product_id)
    return [serialize_inventory(item) for item in inventory]


@router.get("/status/low-stock", response_model=List[InventoryListResponse])
def get_low_stock_items(db: Session = Depends(get_db)):
    """Get all items with low stock status."""
    inventory = InventoryRepository(db).low_stock()
    return [serialize_inventory(item) for item in inventory]


@router.post(
    "/reconcile",
    dependencies=[Depends(require_roles("admin", "manager"))],
)
def reconcile_observation(
    request: ReconcileRequest,
    db: Session = Depends(get_db),
):
    """Test endpoint: reconcile an observation and update inventory state."""
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
        "request": request.model_dump(),
    }

