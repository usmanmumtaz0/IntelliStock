"""
Alert API endpoints — query and manage alerts.
Phase 9 Week 2.
"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.services.alert_service import AlertService
from app.schemas.alert import (
    AlertResponse,
    AlertPaginationResponse,
    AlertStatsResponse,
    AlertAcknowledgeRequest,
    AlertResolveRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["alerts"])


@router.get("/alerts/open", response_model=AlertPaginationResponse)
def get_open_alerts(
    zone_id: str = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Get all open alerts, optionally filtered by zone."""
    service = AlertService(db)
    records, total = service.get_open_alerts(
        zone_id=zone_id,
        limit=limit,
        offset=offset,
    )
    
    pages = (total + limit - 1) // limit if total > 0 else 0
    
    return AlertPaginationResponse(
        data=[AlertResponse.model_validate(r) for r in records],
        pagination={
            "total": total,
            "limit": limit,
            "offset": offset,
            "pages": pages,
        },
    )


@router.get("/zones/{zone_id}/alerts", response_model=AlertPaginationResponse)
def get_zone_alerts(
    zone_id: str,
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Get all alerts in a zone."""
    service = AlertService(db)
    records, total = service.get_alerts_by_zone(
        zone_id=zone_id,
        days=days,
        limit=limit,
        offset=offset,
    )
    
    pages = (total + limit - 1) // limit if total > 0 else 0
    
    return AlertPaginationResponse(
        data=[AlertResponse.model_validate(r) for r in records],
        pagination={
            "total": total,
            "limit": limit,
            "offset": offset,
            "pages": pages,
        },
    )


@router.get("/products/{product_id}/alerts", response_model=AlertPaginationResponse)
def get_product_alerts(
    product_id: str,
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Get all alerts for a product."""
    service = AlertService(db)
    records, total = service.get_alerts_by_product(
        product_id=product_id,
        days=days,
        limit=limit,
        offset=offset,
    )
    
    pages = (total + limit - 1) // limit if total > 0 else 0
    
    return AlertPaginationResponse(
        data=[AlertResponse.model_validate(r) for r in records],
        pagination={
            "total": total,
            "limit": limit,
            "offset": offset,
            "pages": pages,
        },
    )


@router.get("/alerts/critical", response_model=List[AlertResponse])
def get_critical_alerts(db: Session = Depends(get_db)):
    """Get all critical and high severity open alerts."""
    service = AlertService(db)
    records = service.get_critical_alerts()
    return [AlertResponse.model_validate(r) for r in records]


@router.get("/alerts/stats", response_model=AlertStatsResponse)
def get_alert_stats(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """Get alert statistics."""
    service = AlertService(db)
    stats = service.get_alert_stats(days=days)
    return AlertStatsResponse(**stats)


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: str,
    request: AlertAcknowledgeRequest,
    db: Session = Depends(get_db),
):
    """Acknowledge an alert."""
    service = AlertService(db)
    alert = service.acknowledge_alert(alert_id, request.user_id)
    
    if alert:
        return {
            "status": "acknowledged",
            "alert_id": alert_id,
            "message": "Alert acknowledged",
        }
    else:
        return {
            "status": "error",
            "message": "Alert not found",
        }


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: str,
    request: AlertResolveRequest,
    db: Session = Depends(get_db),
):
    """Resolve an alert."""
    service = AlertService(db)
    alert = service.resolve_alert(alert_id, request.user_id)
    
    if alert:
        return {
            "status": "resolved",
            "alert_id": alert_id,
            "message": "Alert resolved",
        }
    else:
        return {
            "status": "error",
            "message": "Alert not found",
        }


@router.post("/alerts/{alert_id}/dismiss")
def dismiss_alert(alert_id: str, db: Session = Depends(get_db)):
    """Dismiss an alert."""
    service = AlertService(db)
    alert = service.dismiss_alert(alert_id)
    
    if alert:
        return {
            "status": "dismissed",
            "alert_id": alert_id,
            "message": "Alert dismissed",
        }
    else:
        return {
            "status": "error",
            "message": "Alert not found",
        }
