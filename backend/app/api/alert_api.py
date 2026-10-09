"""
Alert API endpoints — query and manage alerts.
Phase 9 Week 2.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.orm import Session
from typing import List

from app.core.security import require_roles
from app.database import get_db
from app.models.alert import AlertSeverity, AlertStatus, AlertType
from app.models.user import User
from app.services.alert_service import AlertService
from app.schemas.alert import (
    AlertActionResponse,
    AlertResponse,
    AlertPaginationResponse,
    AlertStatsResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["alerts"])


def _paginated(records, total: int, limit: int, offset: int) -> AlertPaginationResponse:
    pages = (total + limit - 1) // limit if total > 0 else 0
    return AlertPaginationResponse(
        data=[AlertResponse.model_validate(record) for record in records],
        pagination={"total": total, "limit": limit, "offset": offset, "pages": pages},
    )


@router.get("/alerts", response_model=AlertPaginationResponse)
def list_alerts(
    status: AlertStatus | None = Query(None),
    severity: AlertSeverity | None = Query(None),
    alert_type: AlertType | None = Query(None),
    zone_id: str | None = Query(None),
    product_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List persistent alerts with lifecycle filters and stable pagination."""
    records, total = AlertService(db).list_alerts(
        status=status,
        severity=severity,
        alert_type=alert_type,
        zone_id=zone_id,
        product_id=product_id,
        limit=limit,
        offset=offset,
    )
    return _paginated(records, total, limit, offset)


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
    
    return _paginated(records, total, limit, offset)


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
    
    return _paginated(records, total, limit, offset)


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
    
    return _paginated(records, total, limit, offset)


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


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertActionResponse)
def acknowledge_alert(
    alert_id: str,
    current_user: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    """Acknowledge an alert as the authenticated manager or administrator."""
    service = AlertService(db)
    alert = service.acknowledge_alert(alert_id, current_user.id)
    if not alert:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return AlertActionResponse(status="acknowledged", alert_id=alert_id, message="Alert acknowledged")


@router.post("/alerts/acknowledge-all", response_model=AlertActionResponse)
def acknowledge_all_alerts(
    current_user: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    """Acknowledge all open alerts as the authenticated actor."""
    affected = AlertService(db).acknowledge_all(current_user.id)
    return AlertActionResponse(
        status="acknowledged",
        affected=affected,
        message=f"Acknowledged {affected} alert(s)",
    )


@router.post("/alerts/{alert_id}/resolve", response_model=AlertActionResponse)
def resolve_alert(
    alert_id: str,
    current_user: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    """Resolve an alert."""
    service = AlertService(db)
    alert = service.resolve_alert(alert_id, current_user.id)
    if not alert:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return AlertActionResponse(status="resolved", alert_id=alert_id, message="Alert resolved")


@router.post("/alerts/{alert_id}/dismiss", response_model=AlertActionResponse)
def dismiss_alert(
    alert_id: str,
    _current_user: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    """Dismiss an alert."""
    service = AlertService(db)
    alert = service.dismiss_alert(alert_id)
    
    if not alert:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return AlertActionResponse(status="dismissed", alert_id=alert_id, message="Alert dismissed")
