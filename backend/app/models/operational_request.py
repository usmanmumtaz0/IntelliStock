"""Human submissions never change inventory until an authorized review."""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, CheckConstraint
from app.models.base import BaseModel


class OperationalRequest(BaseModel):
    __tablename__ = "operational_requests"
    __table_args__ = (
        CheckConstraint("kind IN ('physical_count','discrepancy','restock')", name="ck_request_kind"),
        CheckConstraint("status IN ('pending','approved','rejected')", name="ck_request_status"),
        CheckConstraint("review_tier IN ('manager','admin')", name="ck_request_review_tier"),
        CheckConstraint("quantity IS NULL OR quantity >= 0", name="ck_request_quantity"),
    )
    inventory_id = Column(String(36), ForeignKey("inventory.id"), nullable=False, index=True)
    submitter_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    kind = Column(String(24), nullable=False)
    reason = Column(String(500), nullable=False)
    quantity = Column(Integer, nullable=True)
    inventory_version = Column(DateTime, nullable=False)
    status = Column(String(16), nullable=False, default="pending", index=True)
    review_tier = Column(String(16), nullable=False, default="manager", index=True)
    reviewer_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    review_reason = Column(String(500), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
