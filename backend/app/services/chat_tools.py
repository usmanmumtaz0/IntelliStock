"""Allowlisted SELECT-only tools; quantities and source links are never model output."""
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload
from app.models.inventory import Inventory, InventoryStatus
from app.models.inventory_history import InventoryHistory
from app.models.alert import Alert, AlertStatus
from app.models.product import Product
from app.models.camera import Camera
from app.models.zone import ShelfZone
from app.models.operational_request import OperationalRequest
from app.models.agent_run import AgentRun, AgentRunStatus
from app.models.system_health import SystemHealthMetric
from app.models.user import User
from app.services.chat_planner import ReadPlan

LIMIT = 20


CAPABILITY_PERMISSIONS = {
    "inventory": "inventory.read",
    "alerts": "alerts.read",
    "history": "inventory.read",
    "summary": "reports.read",
    "operations": "requests.read_all",
    "cameras": "cameras.read",
    "requests": "requests.read_all",
    "activity": "activity.read",
    "accounts": "users.read",
    "system": "diagnostics.read",
}


def available_capabilities(user) -> list[str]:
    from app.core.permissions import permissions_for
    granted = permissions_for(user)
    return [name for name, permission in CAPABILITY_PERMISSIONS.items() if permission in granted]


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
        "operations": ("reports.read", "inventory.read", "alerts.read", "cameras.read",
                       "shelves.read", "requests.read_all"),
        "cameras": ("cameras.read", "shelves.read"),
        "requests": ("requests.read_all",),
        "activity": ("activity.read",),
        "accounts": ("users.read",),
        "system": ("diagnostics.read",),
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
        capabilities = available_capabilities(user)
        labels = {
            "inventory": "current inventory", "alerts": "active alerts",
            "history": "inventory history", "summary": "inventory summaries",
            "operations": "management briefs", "cameras": "camera and shelf status",
            "requests": "operational request queues", "activity": "agent activity",
            "accounts": "account status", "system": "system diagnostics",
        }
        role = getattr(getattr(user, "role", None), "value", getattr(user, "role", "user"))
        available = ", ".join(labels[item] for item in capabilities)
        return {"answer": (
            f"## Your {str(role).title()} assistant\n"
            f"I can securely read: {available}.\n\n"
            "### Try asking\n"
            "- Give me an operations brief\n"
            "- Show low-stock priorities\n"
            "- Show camera and shelf status\n"
            "- Show active alerts or recent inventory history\n\n"
            "I will only use capabilities granted to your account. I can explain and recommend "
            "next steps, while changes still require the appropriate product workflow."
        ), "sources": []}
    if plan.intent == "unsupported":
        return {"answer": (
            "## I cannot perform that action here\n"
            "The assistant protects operational data by remaining read-only. I can inspect the "
            "records your account is allowed to access, explain what needs attention, and direct "
            "you to the authorized workflow for any change.\n\n"
            "Try asking for help to see your available capabilities."
        ), "sources": []}
    if plan.intent == "operations":
        inventory_total = db.query(Inventory).count()
        units = db.query(func.coalesce(func.sum(Inventory.quantity_estimate), 0)).scalar()
        low = db.query(Inventory).filter(Inventory.status.in_((
            InventoryStatus.LOW_STOCK, InventoryStatus.OUT_OF_STOCK,
        ))).count()
        uncertain = db.query(Inventory).filter(Inventory.status.in_((
            InventoryStatus.CAMERA_OFFLINE, InventoryStatus.DETECTION_UNCERTAIN,
        ))).count()
        active_alerts = db.query(Alert).filter(Alert.status.in_((
            AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED, AlertStatus.IN_PROGRESS,
            AlertStatus.ESCALATED,
        ))).count()
        pending_requests = db.query(OperationalRequest).filter_by(status="pending").count()
        cameras_total = db.query(Camera).count()
        cameras_active = db.query(Camera).filter(Camera.is_active.is_(True)).count()
        confidence = float(db.query(func.coalesce(func.avg(Inventory.confidence), 0)).scalar())
        priorities = []
        if low:
            priorities.append(f"Review {low} low-stock or out-of-stock shelf entries.")
        if active_alerts:
            priorities.append(f"Triage {active_alerts} active alerts.")
        if pending_requests:
            priorities.append(f"Review {pending_requests} pending operational requests.")
        if uncertain:
            priorities.append(f"Check {uncertain} uncertain or camera-offline inventory entries.")
        if not priorities:
            priorities.append("No immediate inventory, alert, or request exceptions are recorded.")
        answer = (
            "## Operations brief\n"
            f"As of {now.isoformat()}Z\n\n"
            "### Current position\n"
            f"- {inventory_total} shelf inventory entries with {units} recorded units\n"
            f"- {confidence * 100:.1f}% average reconciliation confidence\n"
            f"- {cameras_active} of {cameras_total} cameras enabled\n"
            f"- {active_alerts} active alerts and {pending_requests} pending requests\n\n"
            "### Recommended priorities\n- " + "\n- ".join(priorities)
        )
        sources.extend([
            {"kind": "aggregate", "id": "operations-inventory", "label": "Inventory overview",
             "href": "/dashboard", "retrieved_at": now.isoformat() + "Z"},
            {"kind": "aggregate", "id": "operations-alerts", "label": "Active alert overview",
             "href": "/alerts", "retrieved_at": now.isoformat() + "Z"},
            {"kind": "aggregate", "id": "operations-requests", "label": "Operational request queue",
             "href": "/requests", "retrieved_at": now.isoformat() + "Z"},
        ])
        return {"answer": answer, "sources": sources, "plan": plan.model_dump()}
    if plan.intent == "cameras":
        zone_counts = dict(db.query(ShelfZone.camera_id, func.count(ShelfZone.id))
                           .group_by(ShelfZone.camera_id).all())
        cameras = db.query(Camera).order_by(Camera.name).limit(LIMIT).all()
        enabled = sum(1 for camera in cameras if camera.is_active)
        configured = sum(1 for camera in cameras if camera.source_url)
        lines = [
            f"- {camera.name} — {camera.location}; "
            f"{'enabled' if camera.is_active else 'disabled'}; "
            f"{'source configured' if camera.source_url else 'source missing'}; "
            f"{zone_counts.get(camera.id, 0)} shelf zones"
            for camera in cameras
        ]
        answer = (
            "## Camera and shelf status\n"
            f"{enabled} of {len(cameras)} cameras are enabled; {configured} have a configured source.\n\n"
            "### Camera coverage\n" + ("\n".join(lines) if lines else "- No cameras are configured.")
        )
        sources.append({"kind": "aggregate", "id": "camera-status", "label": "Camera and shelf configuration",
                        "href": "/shelves", "retrieved_at": now.isoformat() + "Z"})
        return {"answer": answer, "sources": sources, "plan": plan.model_dump()}
    if plan.intent == "requests":
        counts = dict(db.query(OperationalRequest.status, func.count(OperationalRequest.id))
                      .group_by(OperationalRequest.status).all())
        kinds = dict(db.query(OperationalRequest.kind, func.count(OperationalRequest.id))
                     .filter_by(status="pending").group_by(OperationalRequest.kind).all())
        pending = db.query(OperationalRequest).filter_by(status="pending").order_by(
            OperationalRequest.created_at.asc()).limit(LIMIT).all()
        oldest = pending[0].created_at.isoformat() + "Z" if pending else "none"
        answer = (
            "## Operational request queue\n"
            f"- Pending: {counts.get('pending', 0)}\n"
            f"- Approved: {counts.get('approved', 0)}\n"
            f"- Rejected: {counts.get('rejected', 0)}\n"
            f"- Oldest pending request: {oldest}\n\n"
            "### Pending request types\n" +
            ("\n".join(f"- {kind.replace('_', ' ').title()}: {count}" for kind, count in sorted(kinds.items()))
             if kinds else "- No requests are waiting for review.")
        )
        sources.append({"kind": "aggregate", "id": "request-queue", "label": "Operational requests",
                        "href": "/requests", "retrieved_at": now.isoformat() + "Z"})
        return {"answer": answer, "sources": sources, "plan": plan.model_dump()}
    if plan.intent == "activity":
        since = now - timedelta(days=plan.days)
        query = db.query(AgentRun).filter(AgentRun.created_at >= since)
        total = query.count()
        failed = query.filter(AgentRun.status == AgentRunStatus.FAILED).count()
        completed = query.filter(AgentRun.status == AgentRunStatus.COMPLETED).count()
        by_type = dict(query.with_entities(AgentRun.agent_type, func.count(AgentRun.id))
                       .group_by(AgentRun.agent_type).all())
        answer = (
            f"## Agent activity — last {plan.days} days\n"
            f"- Total runs: {total}\n- Completed: {completed}\n- Failed: {failed}\n"
            f"- Completion rate: {(completed / max(total, 1)) * 100:.1f}%\n\n"
            "### Runs by capability\n" +
            ("\n".join(f"- {kind.replace('_', ' ').title()}: {count}" for kind, count in sorted(by_type.items()))
             if by_type else "- No agent runs were recorded in this period.")
        )
        sources.append({"kind": "aggregate", "id": "agent-activity", "label": "Agent execution activity",
                        "href": "/agent-activity", "retrieved_at": now.isoformat() + "Z"})
        return {"answer": answer, "sources": sources, "plan": plan.model_dump()}
    if plan.intent == "accounts":
        role_counts = dict(db.query(User.role, func.count(User.id)).group_by(User.role).all())
        total = db.query(User).count()
        active = db.query(User).filter(User.is_active.is_(True), User.signup_pending.is_(False)).count()
        pending = db.query(User).filter(User.signup_pending.is_(True)).count()
        answer = (
            "## Account overview\n"
            f"- Total accounts: {total}\n- Active accounts: {active}\n"
            f"- Pending signup approvals: {pending}\n\n### Roles\n" +
            "\n".join(f"- {getattr(role, 'value', role).title()}: {count}"
                       for role, count in sorted(role_counts.items(), key=lambda item: str(item[0])))
        )
        sources.append({"kind": "aggregate", "id": "account-overview", "label": "Account administration",
                        "href": "/settings", "retrieved_at": now.isoformat() + "Z"})
        return {"answer": answer, "sources": sources, "plan": plan.model_dump()}
    if plan.intent == "system":
        rows = db.query(SystemHealthMetric).order_by(SystemHealthMetric.checked_at.desc()).limit(100).all()
        latest = {}
        for row in rows:
            latest.setdefault(row.component.value, row)
        lines = [
            f"- {component.replace('_', ' ').title()}: {row.status.value.lower()}"
            + (f"; {row.response_time_ms:.1f} ms" if row.response_time_ms is not None else "")
            + (f"; {row.message}" if row.message else "")
            for component, row in sorted(latest.items())
        ]
        answer = (
            "## System diagnostics\n"
            "Latest stored component checks are shown below. These records may lag the live service state.\n\n"
            "### Components\n" +
            ("\n".join(lines) if lines else "- No stored health checks are available yet.")
        )
        sources.append({"kind": "aggregate", "id": "system-diagnostics", "label": "System diagnostics",
                        "href": "/settings", "retrieved_at": now.isoformat() + "Z"})
        return {"answer": answer, "sources": sources, "plan": plan.model_dump()}
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
