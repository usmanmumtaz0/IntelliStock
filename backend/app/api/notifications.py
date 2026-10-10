"""Administrator-only notification readiness and delivery history; no send button."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.security import require_roles
from app.database import get_db
from app.models.notification import NotificationDelivery
from app.services.notifications import configuration_status

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"],
                   dependencies=[Depends(require_roles("admin"))])


@router.get("/configuration")
def configuration():
    return configuration_status()


@router.get("/deliveries")
def deliveries(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    query = db.query(NotificationDelivery)
    rows = query.order_by(NotificationDelivery.created_at.desc(), NotificationDelivery.id).offset(offset).limit(limit).all()
    return {"total": query.count(), "data": [{
        "id": row.id, "alert_id": row.alert_id, "alert_stage": row.alert_stage,
        "recipient": row.recipient, "status": row.status, "attempts": row.attempts,
        "last_error": row.last_error, "created_at": row.created_at.isoformat() + "Z",
        "available_at": row.available_at.isoformat() + "Z",
        "accepted_at": row.accepted_at.isoformat() + "Z" if row.accepted_at else None,
    } for row in rows]}
