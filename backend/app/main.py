"""
IntelliStock Agent — FastAPI main application.
"""
import logging
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.health import check_database, check_redis
from app.core.rate_limiter import check_rate_limit
from app.core.security import decode_access_token
from app.database import init_db
from app.api import cameras, products, inventory, zones, alerts, events, dashboard, agents, auth
from app.api.websocket import router as ws_router
from app.events import event_consumer
from app.services.camera_heartbeat import get_heartbeat_service

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    logger.info("Application startup")
    # Initialize database tables
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    # Start event consumer
    try:
        event_consumer.start()
        logger.info("Event consumer started")
    except Exception as e:
        logger.error(f"Failed to start event consumer: {e}")
    
    # Start camera heartbeat service
    try:
        heartbeat_service = get_heartbeat_service()
        heartbeat_service.start()
        logger.info("Camera heartbeat service started")
    except Exception as e:
        logger.error(f"Failed to start camera heartbeat service: {e}")
    
    yield
    
    # Stop camera heartbeat service
    try:
        heartbeat_service = get_heartbeat_service()
        heartbeat_service.stop()
        logger.info("Camera heartbeat service stopped")
    except Exception as e:
        logger.error(f"Failed to stop camera heartbeat service: {e}")
    
    # Stop event consumer
    try:
        event_consumer.stop()
        logger.info("Event consumer stopped")
    except Exception as e:
        logger.error(f"Failed to stop event consumer: {e}")
    
    logger.info("Application shutdown")


# Create FastAPI app
app = FastAPI(
    title="IntelliStock Agent API",
    description="AI-powered inventory intelligence platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limit middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next: Callable):
    """Rate limiting middleware."""
    # Skip rate limiting for health checks
    if request.url.path in ["/health", "/api/v1/health"]:
        return await call_next(request)
    
    try:
        await check_rate_limit(request)
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail},
        )
    
    return await call_next(request)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if hasattr(settings, "CORS_ORIGINS") else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(cameras.router)
app.include_router(products.router)
app.include_router(inventory.router)
app.include_router(zones.router)
app.include_router(alerts.router)
app.include_router(events.router)
app.include_router(dashboard.router)
app.include_router(agents.router)
app.include_router(ws_router)


@app.get("/health")
def health_check():
    """
    Health check endpoint.
    Returns status and connection checks for Postgres and Redis.
    """
    db_status = check_database()
    redis_status = check_redis()
    
    return {
        "status": "ok" if (db_status and redis_status) else "degraded",
        "database": "connected" if db_status else "disconnected",
        "redis": "connected" if redis_status else "disconnected",
    }


@app.get("/api/v1/health")
def api_health_check():
    """
    API health check endpoint (versioned).
    """
    return health_check()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
    )
