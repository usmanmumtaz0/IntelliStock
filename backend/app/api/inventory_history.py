"""
Inventory history endpoints — query historical inventory changes.
"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.services.inventory_history_service import InventoryHistoryService
from app.schemas.inventory_history import (
    InventoryHistoryResponse,
    InventoryHistoryPaginationResponse,
    DepletionMetric,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["inventory_history"])


@router.get("/inventory/{zone_id}/{product_id}/history", response_model=InventoryHistoryPaginationResponse)
def get_zone_product_history(
    zone_id: str,
    product_id: str,
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Get all inventory changes for a zone/product combination.

    Args:
        zone_id: Zone ID
        product_id: Product ID
        days: Historical period in days (default 30, max 90)
        limit: Page size
        offset: Page offset

    Returns:
        Paginated list of inventory history records
    """
    history_service = InventoryHistoryService(db)
    records, total = history_service.get_history_by_zone_product(
        zone_id=zone_id,
        product_id=product_id,
        days=days,
        limit=limit,
        offset=offset,
    )

    pages = (total + limit - 1) // limit if total > 0 else 0

    return InventoryHistoryPaginationResponse(
        data=[InventoryHistoryResponse.model_validate(r) for r in records],
        pagination={
            "total": total,
            "limit": limit,
            "offset": offset,
            "pages": pages,
        },
    )


@router.get("/inventory/history/recent", response_model=InventoryHistoryPaginationResponse)
def get_recent_history(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """
    Get most recent inventory changes across all products.

    Args:
        limit: Page size
        offset: Page offset
        days: Historical period in days

    Returns:
        Paginated list of recent changes
    """
    history_service = InventoryHistoryService(db)
    records, total = history_service.get_recent_changes(
        limit=limit,
        offset=offset,
        days=days,
    )

    pages = (total + limit - 1) // limit if total > 0 else 0

    return InventoryHistoryPaginationResponse(
        data=[InventoryHistoryResponse.model_validate(r) for r in records],
        pagination={
            "total": total,
            "limit": limit,
            "offset": offset,
            "pages": pages,
        },
    )


@router.get("/inventory/history/by-type/{change_type}", response_model=InventoryHistoryPaginationResponse)
def get_changes_by_type(
    change_type: str,
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Get all changes of a specific type.

    Args:
        change_type: Type of change (DETECTION, RECONCILIATION, MANUAL_UPDATE, RESTOCK, etc.)
        days: Historical period
        limit: Page size
        offset: Page offset

    Returns:
        Paginated list of changes of specified type
    """
    history_service = InventoryHistoryService(db)
    records, total = history_service.get_changes_by_type(
        change_type=change_type,
        days=days,
        limit=limit,
        offset=offset,
    )

    pages = (total + limit - 1) // limit if total > 0 else 0

    return InventoryHistoryPaginationResponse(
        data=[InventoryHistoryResponse.model_validate(r) for r in records],
        pagination={
            "total": total,
            "limit": limit,
            "offset": offset,
            "pages": pages,
        },
    )


@router.get("/zones/{zone_id}/inventory/history", response_model=InventoryHistoryPaginationResponse)
def get_zone_history(
    zone_id: str,
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Get all inventory changes in a specific zone.

    Args:
        zone_id: Zone ID
        days: Historical period
        limit: Page size
        offset: Page offset

    Returns:
        Paginated list of all zone changes
    """
    history_service = InventoryHistoryService(db)
    records, total = history_service.get_zone_history(
        zone_id=zone_id,
        days=days,
    )

    # Manual pagination
    paginated = records[offset : offset + limit]
    pages = (total + limit - 1) // limit if total > 0 else 0

    return InventoryHistoryPaginationResponse(
        data=[InventoryHistoryResponse.model_validate(r) for r in paginated],
        pagination={
            "total": total,
            "limit": limit,
            "offset": offset,
            "pages": pages,
        },
    )


@router.get("/inventory/depletion-rate", response_model=DepletionMetric)
def get_depletion_rate(
    zone_id: str,
    product_id: str,
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """
    Get depletion rate (units per day) for a product in a zone.

    Args:
        zone_id: Zone ID
        product_id: Product ID
        days: Historical period

    Returns:
        Depletion metric with rate per day
    """
    history_service = InventoryHistoryService(db)
    metric = history_service.get_depletion_rate(
        zone_id=zone_id,
        product_id=product_id,
        days=days,
    )

    return DepletionMetric(
        zone_id=zone_id,
        product_id=product_id,
        **metric,
    )
