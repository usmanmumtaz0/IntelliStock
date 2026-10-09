"""
Health check utilities for database and Redis connectivity.
"""
import logging

import redis
from sqlalchemy import text

from app.core.config import settings
from app.database.connection import engine

logger = logging.getLogger(__name__)


def check_database() -> bool:
    """
    Check PostgreSQL database connectivity.
    Returns True if connection successful, False otherwise.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.debug("Database connection check: OK")
        return True
    except Exception as e:
        logger.warning(f"Database connection check failed: {e}")
        return False


def check_redis() -> bool:
    """
    Check Redis connectivity.
    Returns True if connection successful, False otherwise.
    """
    try:
        r = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=settings.REDIS_SOCKET_TIMEOUT_SECONDS,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT_SECONDS,
        )
        r.ping()
        r.close()
        logger.debug("Redis connection check: OK")
        return True
    except Exception as e:
        logger.warning(f"Redis connection check failed: {e}")
        return False
