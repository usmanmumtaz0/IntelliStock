"""
Health check utilities for database and Redis connectivity.
"""
import logging
from typing import Optional

import psycopg
import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)


async def check_database() -> bool:
    """
    Check PostgreSQL database connectivity.
    Returns True if connection successful, False otherwise.
    """
    try:
        # Parse connection string
        # Format: postgresql://user:password@host:port/database
        async with await psycopg.AsyncConnection.connect(settings.DATABASE_URL) as conn:
            await conn.execute("SELECT 1")
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
        r = await redis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.ping()
        await r.close()
        logger.debug("Redis connection check: OK")
        return True
    except Exception as e:
        logger.warning(f"Redis connection check failed: {e}")
        return False
