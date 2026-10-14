"""Single-store submission workflow with owner-scoped reads and atomic approval."""
from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import get_current_user
from app.core.permissions import authorize, permissions_for
from app.models import Inventory, OperationalRequest, User
from app.models.audit_log import AuditLog
from app.services.operations import audit, correct_inventory
from app.api.inventory import CorrectionRequest

router = APIRouter(prefix="/api/v1", tags=["operational requests"])


class Submission(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    inventory_id: str = Field(min_length=1, max_length=36)
    kind: Literal["physical_count", "discrepancy", "restock"]
    reason: str = Field(min_length=5, max_length=500)
    quantity: int | None = Field(default=None, ge=0, le=1000000, strict=True)

    @model_validator(mode="after")
    def validate_count(self):
        if (self.kind == "physical_count") != (self.quantity is not None):
            raise ValueError("Only physical counts require a quantity")
        return self


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    decision: Literal["approved", "rejected"]
    reason: str = Field(min_length=5, max_length=255)


def scoped(db, user):
    query = db.query(OperationalRequest)
    if "requests.read_all" not in permissions_for(user):
        query = query.filter(OperationalRequest.submitter_id == user.id)
    return query


def serialize(row):
    return {key: getattr(row, key) for key in ("id", "inventory_id", "submitter_id", "kind", "reason",
        "quantity", "status", "reviewer_id", "review_reason", "reviewed_at", "created_at", "updated_at")}


@router.get("/requests")
def list_requests(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                  db: Session = Depends(get_db), user=Depends(get_current_user)):
    return [serialize(r) for r in scoped(db, user).order_by(OperationalRequest.created_at.desc(),
        OperationalRequest.id).offset(offset).limit(limit).all()]


@router.get("/requests/{request_id}")
def get_request(request_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = scoped(db, user).filter(OperationalRequest.id == request_id).first()
    if not row:
        raise HTTPException(404, "Request not found")
    return serialize(row)


@router.post("/requests", status_code=201)
def submit_request(data: Submission, db: Session = Depends(get_db), user=Depends(get_current_user)):
    inventory = db.get(Inventory, data.inventory_id)
    if not inventory:
        raise HTTPException(404, "Inventory not found")
    row = OperationalRequest(**data.model_dump(), submitter_id=user.id, inventory_version=inventory.updated_at)
    db.add(row)
    db.flush()
    audit(db, user, "submit", "request", row.id, new={"kind": row.kind, "inventory_id": row.inventory_id})
    db.commit()
    return serialize(row)


@router.post("/requests/{request_id}/review")
def review_request(request_id: str, data: Review, db: Session = Depends(get_db), user=Depends(get_current_user)):
    current = db.query(User).filter_by(id=user.id).populate_existing().with_for_update().one()
    authorize(current, "requests.review")
    row = db.query(OperationalRequest).filter_by(id=request_id).with_for_update().first()
    if not row:
        raise HTTPException(404, "Request not found")
    if row.status != "pending":
        raise HTTPException(409, "This request was already reviewed")
    if data.decision == "approved" and row.kind == "physical_count":
        authorize(current, "inventory.adjust_stock")
        inv = correct_inventory(db, row.inventory_id, CorrectionRequest(quantity=row.quantity,
            reason=data.reason, expected_updated_at=row.inventory_version), current)
        zone_id, product_id, camera_id = inv.zone_id, inv.product_id, inv.zone.camera_id
    row.status, row.reviewer_id = data.decision, current.id
    row.review_reason, row.reviewed_at = data.reason, datetime.utcnow()
    audit(db, current, "review", "request", row.id, old={"status": "pending"},
          new={"status": row.status, "reason": data.reason})
    db.commit()
    if data.decision == "approved" and row.kind == "physical_count":
        from app.services.observation_window import get_observation_window
        get_observation_window(camera_id, zone_id, product_id).clear()
    return serialize(row)


@router.get("/operational-audit")
def operational_audit(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                      db: Session = Depends(get_db), user=Depends(get_current_user)):
    query = db.query(AuditLog).filter(AuditLog.resource_type.in_(("inventory", "alert", "request")))
    if "audit.read_operational" not in permissions_for(user):
        query = query.filter(AuditLog.user_id == user.id, AuditLog.resource_type == "request")
    return [{"id": str(r.id), "action": r.action, "resource_type": r.resource_type,
             "resource_id": r.resource_id, "timestamp": r.timestamp, "outcome": r.status}
            for r in query.order_by(AuditLog.timestamp.desc(), AuditLog.id).offset(offset).limit(limit).all()]
