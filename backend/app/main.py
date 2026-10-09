"""
IntelliStock Agent — FastAPI main application.
"""
import logging
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import agents, alert_api, audit_api, auth, cameras, dashboard, events, health_api, inventory, inventory_history, products, zones
from app.api.websocket import router as ws_router
from app.core.config import settings
from app.core.health import check_database, check_redis
from app.core.rate_limiter import check_rate_limit
from app.core.security import get_current_user, require_roles
from app.database import init_db
from app.events import event_consumer
from app.services.camera_heartbeat import get_heartbeat_service

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

PUBLIC_PATHS = {"/health", "/api/v1/health", "/api/v1/auth/login", "/docs", "/openapi.json", "/redoc"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    logger.info("Application startup")
    try:
        if settings.APP_ENV == "production":
            logger.info("Production schema creation skipped; run Alembic migrations before startup")
        else:
            init_db()
            logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    try:
        event_consumer.start()
        logger.info("Event consumer started")
    except Exception as e:
        logger.error(f"Failed to start event consumer: {e}")

    try:
        heartbeat_service = get_heartbeat_service()
        heartbeat_service.start()
        logger.info("Camera heartbeat service started")
    except Exception as e:
        logger.error(f"Failed to start camera heartbeat service: {e}")

    yield

    try:
        heartbeat_service = get_heartbeat_service()
        heartbeat_service.stop()
        logger.info("Camera heartbeat service stopped")
    except Exception as e:
        logger.error(f"Failed to stop camera heartbeat service: {e}")

    try:
        event_consumer.stop()
        logger.info("Event consumer stopped")
    except Exception as e:
        logger.error(f"Failed to stop event consumer: {e}")

    logger.info("Application shutdown")


app = FastAPI(
    title="IntelliStock Agent API",
    description="AI-powered inventory intelligence platform",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next: Callable):
    """Rate limiting middleware for public and protected routes."""
    path = request.url.path.rstrip("/") or "/"
    if path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/openapi") or path.startswith("/redoc"):
        return await call_next(request)

    try:
        await check_rate_limit(request)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers or {})

    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
protected = [Depends(get_current_user)]
app.include_router(cameras.router, dependencies=protected)
app.include_router(products.router, dependencies=protected)
app.include_router(inventory.router, dependencies=protected)
app.include_router(inventory_history.router, dependencies=protected)
app.include_router(alert_api.router, dependencies=protected)
app.include_router(audit_api.router, dependencies=[Depends(require_roles("admin"))])
app.include_router(health_api.router, dependencies=[Depends(require_roles("admin"))])
app.include_router(zones.router, dependencies=protected)
app.include_router(events.router, dependencies=protected)
app.include_router(dashboard.router, dependencies=protected)
app.include_router(agents.router, dependencies=protected)
app.include_router(ws_router)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    db_status = check_database()
    redis_status = check_redis()

    return {
        "status": "ok" if (db_status and redis_status) else "degraded",
        "database": "connected" if db_status else "disconnected",
        "redis": "connected" if redis_status else "disconnected",
    }


@app.get("/api/v1/health")
def api_health_check():
    """API health check endpoint (versioned)."""
    return health_check()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
    )
