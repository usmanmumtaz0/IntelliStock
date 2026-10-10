"""Deterministic operational reports; no inferred sales or LLM arithmetic."""
import csv
import io
from datetime import datetime, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.inventory import Inventory
from app.models.inventory_history import InventoryHistory
from app.models.product import Product
from app.models.zone import ShelfZone
from app.models.alert import Alert, AlertStatus

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])
EXPORT_LIMIT = 10000


def csv_cell(value):
    """Neutralize spreadsheet formulas in untrusted text, not numeric quantities."""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


@router.get("/summary")
def summary(days: int = Query(7, ge=1, le=90), zone_id: str | None = None, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    stock = db.query(Inventory)
    history = db.query(InventoryHistory).filter(InventoryHistory.created_at >= now - timedelta(days=days), InventoryHistory.created_at <= now)
    alerts = db.query(Alert).filter(Alert.status.in_((AlertStatus.OPEN, AlertStatus.ESCALATED, AlertStatus.ACKNOWLEDGED, AlertStatus.IN_PROGRESS)))
    if zone_id:
        stock = stock.filter(Inventory.zone_id == zone_id)
        history = history.filter(InventoryHistory.zone_id == zone_id)
        alerts = alerts.filter(Alert.zone_id == zone_id)
    by_state = {state.value: count for state, count in stock.with_entities(Inventory.status, func.count()).group_by(Inventory.status).all()}
    by_change = {kind.value: count for kind, count in history.with_entities(InventoryHistory.change_type, func.count()).group_by(InventoryHistory.change_type).all()}
    return {"generated_at": now.isoformat() + "Z", "days": days,
            "inventory_records": sum(by_state.values()), "distinct_products": stock.with_entities(Inventory.product_id).distinct().count(),
            "committed_units": stock.with_entities(func.coalesce(func.sum(Inventory.quantity_estimate), 0)).scalar(),
            "states": by_state, "history_changes": sum(by_change.values()), "change_types": by_change,
            "active_alerts": alerts.count(),
            "note": "Counts include last committed quantities, even for offline/uncertain shelves. Quantity changes are not sales."}


@router.get("/export")
def export_report(kind: Literal["inventory", "history"] = "inventory", days: int = Query(7, ge=1, le=90),
                  zone_id: str | None = None, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    if kind == "inventory":
        query = db.query(Inventory, Product.sku, Product.name, ShelfZone.name).join(Product, Inventory.product_id == Product.id).join(ShelfZone, Inventory.zone_id == ShelfZone.id)
        if zone_id:
            query = query.filter(Inventory.zone_id == zone_id)
        rows = query.order_by(Inventory.zone_id, Inventory.product_id).limit(EXPORT_LIMIT + 1).all()
        header = ["inventory_id", "zone_id", "shelf", "product_id", "sku", "product", "committed_quantity", "status", "last_camera_confidence", "last_observation_utc", "updated_utc"]
        data = ([row.id, row.zone_id, zone, row.product_id, sku, name, row.quantity_estimate,
                 row.status.value, row.confidence, row.last_observation_time or "", row.updated_at.isoformat() + "Z"] for row,sku,name,zone in rows)
    else:
        query = db.query(InventoryHistory, Product.sku, ShelfZone.name).join(Product, InventoryHistory.product_id == Product.id).join(ShelfZone, InventoryHistory.zone_id == ShelfZone.id).filter(
            InventoryHistory.created_at >= now - timedelta(days=days), InventoryHistory.created_at <= now)
        if zone_id:
            query = query.filter(InventoryHistory.zone_id == zone_id)
        rows = query.order_by(InventoryHistory.created_at.desc(), InventoryHistory.id).limit(EXPORT_LIMIT + 1).all()
        header = ["history_id", "zone_id", "shelf", "product_id", "sku", "previous_quantity", "new_quantity", "delta", "change_type", "source", "reason", "actor_user_id", "created_utc"]
        data = ([row.id, row.zone_id, zone, row.product_id, sku, row.previous_quantity,
                 row.new_quantity, row.quantity_delta, row.change_type.value, row.source_system,
                 row.reason or "", row.actor_user_id or "", row.created_at.isoformat() + "Z"] for row,sku,zone in rows)
    if len(rows) > EXPORT_LIMIT:
        raise HTTPException(413, "Report exceeds 10,000 rows; narrow the shelf or history date range")
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(header)
    writer.writerows([csv_cell(value) for value in row] for row in data)
    return Response(content="\ufeff" + output.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="intellistock-{kind}-{now:%Y%m%d}.csv"',
                             "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
