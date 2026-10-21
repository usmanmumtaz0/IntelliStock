"""Explicit single-store policy. Unknown permissions/routes fail closed."""
from fastapi import Depends, HTTPException, Request
from app.core.security import get_current_user
import logging

READ = frozenset({"inventory.read", "products.read", "alerts.read", "shelves.read",
    "cameras.read", "reports.read", "activity.read", "requests.read_own",
    "audit.read_own", "chatbot.use", "chatbot.inventory.read", "chatbot.alerts.read",
    "chatbot.analytics.read", "realtime.read", "video_jobs.read", "video_jobs.create"})
STAFF_REQUESTS = frozenset({"requests.create", "requests.submit"})
OPERATIONS = frozenset({"inventory.adjust_stock", "products.create", "products.update",
    "alerts.acknowledge", "alerts.resolve", "alerts.snooze", "alerts.dismiss", "reports.export",
    "requests.review", "requests.read_all", "audit.read_operational", "video_jobs.review"})
MANAGER_REQUESTS = frozenset({"requests.create", "requests.escalate"})
ADMIN = frozenset({"products.delete", "thresholds.manage", "cameras.manage", "shelves.manage",
    "users.read", "users.create", "users.update", "roles.manage", "audit.read_all",
    "settings.read", "diagnostics.read", "diagnostics.observe", "video_jobs.camera",
    "video_jobs.read_all"})
ROLE_PERMISSIONS = {
    "staff": READ | STAFF_REQUESTS,
    "manager": READ | OPERATIONS | MANAGER_REQUESTS,
    "admin": READ | OPERATIONS | ADMIN,
}

def permissions_for(user):
    if not user or not user.is_active or user.signup_pending:
        return frozenset()
    role = getattr(user.role, "value", user.role)
    return ROLE_PERMISSIONS.get(role, frozenset())


def authorize(user, permission):
    if permission not in permissions_for(user):
        logging.getLogger(__name__).warning("Permission denied actor=%s permission=%s", getattr(user, "id", None), permission)
        raise HTTPException(403, "Insufficient permissions")


def require_permission(permission):
    def dependency(user=Depends(get_current_user)):
        authorize(user, permission)
        return user
    return dependency


# Exact registered path templates: adding a route never implicitly grants access.
ROUTE_PERMISSIONS = {}
def register(method, permission, *paths):
    for path in paths:
        ROUTE_PERMISSIONS[(method, "/api/v1" + path)] = permission

register("GET", "inventory.read", "/inventory", "/inventory/{inventory_id}",
    "/inventory/zone/{zone_id}", "/inventory/product/{product_id}", "/inventory/status/low-stock",
    "/inventory/{zone_id}/{product_id}/history", "/inventory/history/recent",
    "/inventory/history/by-type/{change_type}", "/zones/{zone_id}/inventory/history",
    "/inventory/depletion-rate", "/events", "/events/zone/{zone_id}", "/events/product/{product_id}")
register("POST", "inventory.adjust_stock", "/inventory/{inventory_id}/corrections")
register("POST", "diagnostics.observe", "/inventory/reconcile")
register("GET", "products.read", "/products", "/products/{product_id}")
register("POST", "products.create", "/products")
register("PUT", "products.update", "/products/{product_id}")
register("DELETE", "products.delete", "/products/{product_id}")
register("GET", "cameras.read", "/cameras", "/cameras/{camera_id}")
register("POST", "cameras.manage", "/cameras")
register("PUT", "cameras.manage", "/cameras/{camera_id}")
register("DELETE", "cameras.manage", "/cameras/{camera_id}")
register("GET", "shelves.read", "/zones", "/zones/{zone_id}")
register("GET", "shelves.manage", "/zones/{zone_id}/configuration")
register("POST", "shelves.manage", "/zones")
register("PUT", "shelves.manage", "/zones/{zone_id}")
register("GET", "alerts.read", "/alerts", "/alerts/open", "/alerts/critical", "/alerts/stats",
    "/zones/{zone_id}/alerts", "/products/{product_id}/alerts")
register("POST", "alerts.acknowledge", "/alerts/{alert_id}/acknowledge", "/alerts/acknowledge-all")
for action in ("resolve", "dismiss", "snooze"):
    register("POST", "alerts." + action, "/alerts/{alert_id}/" + action)
register("GET", "reports.read", "/reports/summary", "/dashboard/metrics", "/dashboard/store-info")
register("GET", "reports.export", "/reports/export")
register("GET", "activity.read", "/agents/runs", "/agents/runs/{run_id}", "/agents/stats")
register("GET", "diagnostics.read", "/agents/runs/{run_id}/trace", "/health/system", "/health/database",
    "/health/redis", "/health/performance/{component}/{operation}", "/health/performance/issues", "/health/failures")
register("GET", "audit.read_all", "/audit/resource/{resource_type}/{resource_id}", "/audit/user/{user_id}",
    "/audit/action/{action}", "/audit/failures")
register("GET", "audit.read_own", "/operational-audit")
register("GET", "settings.read", "/notifications/configuration", "/notifications/deliveries")
register("GET", "users.read", "/users")
register("POST", "users.create", "/users", "/users/{user_id}/approve")
register("PUT", "users.update", "/users/{user_id}")
register("GET", "chatbot.use", "/chat/status", "/chat/conversations", "/chat/conversations/{conversation_id}")
register("POST", "chatbot.use", "/chat/conversations", "/chat/conversations/{conversation_id}/turns")
register("DELETE", "chatbot.use", "/chat/conversations/{conversation_id}")
register("GET", "requests.read_own", "/requests", "/requests/{request_id}")
register("POST", "requests.create", "/requests")
register("POST", "requests.review", "/requests/{request_id}/review")
register("GET", "video_jobs.read", "/video-jobs", "/video-jobs/{job_id}",
    "/video-jobs/{job_id}/frames", "/video-jobs/{job_id}/frames/{frame_id}/image",
    "/video-jobs/model-health", "/video-jobs/review-queue")
register("POST", "video_jobs.create", "/video-jobs", "/video-jobs/images",
    "/video-jobs/{job_id}/cancel")
register("POST", "video_jobs.camera", "/video-jobs/cameras/{camera_id}")
register("POST", "video_jobs.review", "/video-jobs/detections/{detection_id}/identify")


def enforce_route_permission(request: Request, user=Depends(get_current_user)):
    permission = ROUTE_PERMISSIONS.get((request.method, request.scope["route"].path))
    if permission is None:
        raise HTTPException(403, "No access policy for this operation")
    authorize(user, permission)
    return user
