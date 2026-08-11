"""
Health check utilities for database and Redis connectivity.
"""
import logging
from typing import Optional

import psycopg2
import redis

from app.core.config import settings

logger = logging.getLogger(__name__)


async def check_database() -> bool:
    """
    Check PostgreSQL database connectivity.
    Returns True if connection successful, False otherwise.
    """
    try:
        conn = psycopg2.connect(settings.DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        logger.debug("Database connection check: OK")
        return True
    except Exception as e:
        logger.warning(f"Database connection check failed: {e}")
        return False


async def check_redis() -> bool:
    """
    Check Redis connectivity.
    Returns True if connection successful, False otherwise.
    """
    try:
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        r.ping()
        r.close()
        logger.debug("Redis connection check: OK")
        return True
    except Exception as e:
        logger.warning(f"Redis connection check failed: {e}")
        return False
