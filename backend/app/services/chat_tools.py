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


def authorize_plan(user, raw_plan):
    from app.core.permissions import authorize
    authorize(user, "chatbot.use")
    from pydantic import ValidationError
    from fastapi import HTTPException
    try:
        plan = ReadPlan.model_validate(raw_plan)
    except ValidationError:
        raise HTTPException(403, "Invalid assistant access plan") from None
    permissions = {
        "inventory": ("chatbot.inventory.read", "inventory.read", "products.read", "shelves.read"),
        "history": ("chatbot.inventory.read", "inventory.read", "products.read", "shelves.read"),
        "alerts": ("chatbot.alerts.read", "alerts.read", "products.read", "shelves.read"),
        "summary": ("chatbot.analytics.read", "reports.read", "inventory.read", "products.read"),
    }.get(plan.intent, ())
    for permission in permissions:
        authorize(user, permission)


def execute_read(db, raw_plan: dict, user=None) -> dict:
    authorize_plan(user, raw_plan)
    plan = ReadPlan.model_validate(raw_plan)
    sources = []
    now = datetime.utcnow()
    resolved_id = None
    if plan.product_query and plan.intent not in ("help", "unsupported"):
        base = db.query(Product)
        matches = base.filter(func.lower(Product.sku) == plan.product_query.lower()).limit(2).all()
        if not matches:
            matches = base.filter(func.lower(Product.name) == plan.product_query.lower()).limit(6).all()
        if not matches:
            matches = product_filter(base, plan.product_query).order_by(Product.sku).limit(6).all()
        if len(matches) > 1:
            choices = "\n".join(f"- {item.sku}: {item.name}" for item in matches[:5])
            return {"answer": "Which product do you mean? Please reply with its product code.\n" + choices
                    + ("\nMore matches exist; please narrow the product name." if len(matches) > 5 else ""),
                    "sources": [], "plan": plan.model_dump()}
        if len(matches) == 1:
            resolved_id = matches[0].id
            plan.product_query = matches[0].sku
    def scoped(query):
        return query.filter(Product.id == resolved_id) if resolved_id else product_filter(query, plan.product_query)
    def evidence(kind, row, label, href):
        return {"kind": kind, "id": row.id, "label": label, "href": href,
                "sku": row.product.sku, "shelf": row.zone.name,
                "recorded_at": row.created_at.isoformat() + "Z",
                "updated_at": row.updated_at.isoformat() + "Z",
                "retrieved_at": now.isoformat() + "Z"}
    scope = f'Product code: "{plan.product_query}".' if plan.product_query else "All products."
    if plan.intent == "help":
        return {"answer":"I can help you check inventory, active alerts and inventory history. Try: Show low stock; Inventory for product code ABC-123; History for \"Milk\" in the last 7 days. You can follow up with: Which shelf? I cannot change inventory, send messages or forecast sales.", "sources":[]}
    if plan.intent == "unsupported":
        return {"answer":"This read-only assistant cannot perform that request. Ask about inventory, active alerts or inventory history. Use the management pages for changes. To find a product, put its name in quotation marks or enter its product code.", "sources":[]}
    if plan.intent in ("inventory", "summary"):
        query = scoped(db.query(Inventory).join(Product))
        if plan.stock_filter != "all":
            query = query.filter(Inventory.status == InventoryStatus(plan.stock_filter))
        states = {state.value: count for state,count in query.with_entities(Inventory.status, func.count()).group_by(Inventory.status)}
        total = sum(states.values())
        if plan.intent == "summary":
            units = query.with_entities(func.coalesce(func.sum(Inventory.quantity_estimate),0)).scalar()
            answer = f"{scope}\nInventory status: {plan.stock_filter.replace('_', ' ')}.\n{total} products across shelves; {units} recorded units.\n" + "\n".join(f"{state.replace('_', ' ')}: {count} entries" for state,count in sorted(states.items()))
            sources.append({"kind":"aggregate", "id":"inventory-summary", "label":"Inventory aggregate at query time", "href":"/reports", "retrieved_at":now.isoformat()+"Z"})
        else:
            rows = query.options(joinedload(Inventory.product), joinedload(Inventory.zone)).order_by(Inventory.zone_id,Inventory.product_id).limit(LIMIT).all()
            lines = []
            for i,row in enumerate(rows,1):
                lines.append(f"[{i}] {row.product.name} (product code {row.product.sku}); shelf {row.zone.name}: {row.quantity_estimate} recorded units; {row.status.value.replace('_', ' ')}; {observed_label(row.last_observation_time)}.")
                lines[-1] += f" Record updated {row.updated_at.isoformat()}Z."
                sources.append(evidence("inventory", row, f"[{i}] {row.product.sku} / {row.zone.name}", "/inventory?" + urlencode({"record":row.id})))
            answer = f"{scope}\nInventory status: {plan.stock_filter.replace('_', ' ')}. Showing {len(rows)} of {total} matching inventory entries.\n" + "\n".join(lines)
        answer += "\nInventory counts may be outdated when cameras are offline or observations are uncertain. These are not sales figures."
    elif plan.intent == "alerts":
        query = scoped(db.query(Alert).join(Product)).filter(Alert.status.in_((AlertStatus.OPEN,AlertStatus.ACKNOWLEDGED,AlertStatus.IN_PROGRESS,AlertStatus.ESCALATED)))
        total = query.count()
        rows = query.options(joinedload(Alert.product),joinedload(Alert.zone)).order_by(Alert.created_at.desc(),Alert.id).limit(LIMIT).all()
        lines = []
        for i,row in enumerate(rows,1):
            snooze = f"; snoozed until {row.snoozed_until.isoformat()}Z" if row.snoozed_until and row.snoozed_until > now else ""
            lines.append(f"[{i}] {row.product.sku} / {row.zone.name}: {row.alert_type.value}, {row.status.value}, {row.severity.value}{snooze}. Quantity at alert creation: {row.current_quantity}.")
            lines[-1] += f" Created {row.created_at.isoformat()}Z; updated {row.updated_at.isoformat()}Z."
            sources.append(evidence("alert", row, f"[{i}] {row.product.sku} / {row.zone.name} / alert", "/alerts"))
        answer = f"{scope}\nShowing {len(rows)} of {total} active alerts (all alert types).\n" + "\n".join(lines)
    else:
        start, end = now-timedelta(days=plan.days), now
        window = f"the last {plan.days} days (UTC)"
        if plan.period in ("today", "yesterday"):
            midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
            start = midnight-timedelta(days=1) if plan.period == "yesterday" else midnight
            end = midnight if plan.period == "yesterday" else now
            window = f"{plan.period} (UTC calendar day: {start.isoformat()}Z to {end.isoformat()}Z, end exclusive)"
        query = scoped(db.query(InventoryHistory).join(Product)).filter(
            InventoryHistory.created_at >= start, InventoryHistory.created_at < end)
        total = query.count()
        rows = query.options(joinedload(InventoryHistory.product),joinedload(InventoryHistory.zone)).order_by(InventoryHistory.created_at.desc(),InventoryHistory.id).limit(LIMIT).all()
        lines = []
        for i,row in enumerate(rows,1):
            lines.append(f"[{i}] {row.created_at.isoformat()}Z — {row.product.sku} / {row.zone.name}: {row.previous_quantity} → {row.new_quantity} (delta {row.quantity_delta}); {row.change_type.value}.")
            sources.append(evidence("history", row, f"[{i}] {row.product.sku} / {row.zone.name} / history", "/inventory?" + urlencode({"zone":row.zone_id,"sku":row.product.sku})))
        answer = f"{scope}\nShowing {len(rows)} of {total} recorded changes in {window}. Changes are not proof of sales or a complete historical stock snapshot.\n" + "\n".join(lines)
    if plan.product_query and not resolved_id:
        answer += "\nNo product matched that name or product code. Check the code or try a shorter product name in quotation marks."
    return {"answer":f"As of {now.isoformat()}Z\n{answer}", "sources":sources, "plan":plan.model_dump()}
