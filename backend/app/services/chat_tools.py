"""Allowlisted SELECT-only tools; quantities and source links are never model output."""
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload
from app.models.inventory import Inventory, InventoryStatus
from app.models.inventory_history import InventoryHistory
from app.models.alert import Alert, AlertStatus
from app.models.product import Product
from app.services.chat_planner import ReadPlan

LIMIT = 20


def product_filter(query, text):
    if text:
        query = query.filter(or_(func.lower(Product.sku).contains(text.lower(), autoescape=True),
                                 func.lower(Product.name).contains(text.lower(), autoescape=True)))
    return query


def observed_label(value):
    if not value:
        return "no camera observation"
    try:
        observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if not observed.tzinfo:
            observed = observed.replace(tzinfo=timezone.utc)
        stale = (datetime.now(timezone.utc) - observed).total_seconds() > 60
        return f"last observation {observed.isoformat()}" + (" (STALE)" if stale else "")
    except ValueError:
        return "unknown camera observation time"


def execute_read(db, raw_plan: dict) -> dict:
    plan = ReadPlan.model_validate(raw_plan)
    sources = []
    now = datetime.utcnow()
    scope = f'Product filter: "{plan.product_query}".' if plan.product_query else "Scope: all products."
    if plan.intent == "help":
        return {"answer":"I can read inventory, active alerts, recorded history and inventory summaries. Try: Show low stock; Inventory for SKU ABC-123; History for \"Milk\" in the last 7 days. Follow up with: Show its history. I cannot change stock, send messages, forecast sales or read secrets.", "sources":[]}
    if plan.intent == "unsupported":
        return {"answer":"This read-only assistant cannot perform that request. Ask about committed inventory, active alerts or recorded history. Use the authorized management pages for changes. In local mode, quote a product name or specify SKU followed by its code.", "sources":[]}
    if plan.intent in ("inventory", "summary"):
        query = product_filter(db.query(Inventory).join(Product), plan.product_query)
        if plan.stock_filter != "all":
            query = query.filter(Inventory.status == InventoryStatus(plan.stock_filter))
        states = {state.value: count for state,count in query.with_entities(Inventory.status, func.count()).group_by(Inventory.status)}
        total = sum(states.values())
        if plan.intent == "summary":
            units = query.with_entities(func.coalesce(func.sum(Inventory.quantity_estimate),0)).scalar()
            answer = f"{scope}\nStock filter: {plan.stock_filter}.\n{total} shelf/product records; {units} committed units.\n" + "\n".join(f"{state}: {count} records" for state,count in sorted(states.items()))
            sources.append({"kind":"aggregate", "id":"inventory-summary", "label":"Inventory aggregate at query time", "href":"/reports"})
        else:
            rows = query.options(joinedload(Inventory.product), joinedload(Inventory.zone)).order_by(Inventory.zone_id,Inventory.product_id).limit(LIMIT).all()
            lines = []
            for i,row in enumerate(rows,1):
                lines.append(f"[{i}] {row.product.sku} — {row.product.name}; shelf {row.zone.name}: {row.quantity_estimate} committed; {row.status.value}; {observed_label(row.last_observation_time)}.")
                sources.append({"kind":"inventory", "id":row.id, "label":f"[{i}] {row.product.sku} / {row.zone.name}", "href":"/inventory?" + urlencode({"record":row.id})})
            answer = f"{scope}\nStock filter: {plan.stock_filter}. Showing {len(rows)} of {total} matching inventory records.\n" + "\n".join(lines)
        answer += "\nCommitted counts may be old when cameras are offline or evidence is uncertain. These are not sales figures."
    elif plan.intent == "alerts":
        query = product_filter(db.query(Alert).join(Product), plan.product_query).filter(Alert.status.in_((AlertStatus.OPEN,AlertStatus.ACKNOWLEDGED,AlertStatus.IN_PROGRESS,AlertStatus.ESCALATED)))
        total = query.count()
        rows = query.options(joinedload(Alert.product),joinedload(Alert.zone)).order_by(Alert.created_at.desc(),Alert.id).limit(LIMIT).all()
        lines = []
        for i,row in enumerate(rows,1):
            snooze = f"; snoozed until {row.snoozed_until.isoformat()}Z" if row.snoozed_until and row.snoozed_until > now else ""
            lines.append(f"[{i}] {row.product.sku} / {row.zone.name}: {row.alert_type.value}, {row.status.value}, {row.severity.value}{snooze}. Quantity at alert creation: {row.current_quantity}.")
            sources.append({"kind":"alert", "id":row.id, "label":f"[{i}] Alert {row.id}", "href":"/alerts"})
        answer = f"{scope}\nShowing {len(rows)} of {total} active alerts (all alert types).\n" + "\n".join(lines)
    else:
        query = product_filter(db.query(InventoryHistory).join(Product), plan.product_query).filter(
            InventoryHistory.created_at >= now-timedelta(days=plan.days), InventoryHistory.created_at <= now)
        total = query.count()
        rows = query.options(joinedload(InventoryHistory.product),joinedload(InventoryHistory.zone)).order_by(InventoryHistory.created_at.desc(),InventoryHistory.id).limit(LIMIT).all()
        lines = []
        for i,row in enumerate(rows,1):
            lines.append(f"[{i}] {row.created_at.isoformat()}Z — {row.product.sku} / {row.zone.name}: {row.previous_quantity} → {row.new_quantity} (delta {row.quantity_delta}); {row.change_type.value}.")
            sources.append({"kind":"history", "id":row.id, "label":f"[{i}] History {row.id}", "href":"/inventory?" + urlencode({"zone":row.zone_id,"sku":row.product.sku})})
        answer = f"{scope}\nShowing {len(rows)} of {total} recorded changes in the last {plan.days} days (UTC). Changes are not proof of sales.\n" + "\n".join(lines)
    return {"answer":f"As of {now.isoformat()}Z\n{answer}", "sources":sources}
