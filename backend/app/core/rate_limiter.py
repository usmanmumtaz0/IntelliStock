"""
Rate limiting middleware — prevent abuse and ensure fair access.
"""
import logging
from typing import Dict
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    In-memory rate limiter using token bucket algorithm.
    For production, use Redis-backed rate limiter.
    """
    
    def __init__(self):
        """Initialize rate limiter."""
        self.requests: Dict[str, list] = {}
    
    def is_allowed(
        self,
        identifier: str,
        limit: int = 100,
        window_seconds: int = 60,
    ) -> bool:
        """
        Check if a request is allowed based on rate limit.
        
        Args:
            identifier: Identifier (IP, user_id, etc)
            limit: Max requests allowed
            window_seconds: Time window in seconds
        
        Returns:
            True if allowed, False if rate limited
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)
        
        # Initialize or get request list
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        # Remove old requests outside the window
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > cutoff
        ]
        
        # Check if limit exceeded
        if len(self.requests[identifier]) >= limit:
            return False
        
        # Add current request
        self.requests[identifier].append(now)
        return True
    
    def cleanup(self):
        """Remove old entries to prevent memory leak."""
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=1)
        
        for identifier in list(self.requests.keys()):
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if req_time > cutoff
            ]
            
            if not self.requests[identifier]:
                del self.requests[identifier]


# Global rate limiter instance
rate_limiter = RateLimiter()

# Rate limiting rules
RATE_LIMITS = {
    "default": {"limit": 100, "window": 60},  # 100 requests per minute
    "auth": {"limit": 5, "window": 60},  # 5 auth attempts per minute
    "write": {"limit": 50, "window": 60},  # 50 writes per minute
    "read": {"limit": 200, "window": 60},  # 200 reads per minute
}


async def check_rate_limit(request: Request) -> bool:
    """
    Middleware to check rate limits.
    
    Args:
        request: FastAPI request
    
    Returns:
        True if allowed, raises HTTPException if rate limited
    """
    # Get client identifier (IP or user_id)
    client_id = request.client.host if request.client else "unknown"
    
    # Try to get user_id from JWT token (if available)
    try:
        from app.core.security import decode_access_token
        
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            token_data = decode_access_token(token)
            if token_data:
                client_id = token_data.user_id
    except Exception:
        pass
    
    # Determine rate limit category
    method = request.method
    path = request.url.path
    
    if path.startswith("/auth"):
        limit_config = RATE_LIMITS["auth"]
    elif method in ["POST", "PUT", "DELETE"]:
        limit_config = RATE_LIMITS["write"]
    elif method == "GET":
        limit_config = RATE_LIMITS["read"]
    else:
        limit_config = RATE_LIMITS["default"]
    
    # Check rate limit
    if not rate_limiter.is_allowed(
        client_id,
        limit=limit_config["limit"],
        window_seconds=limit_config["window"],
    ):
        logger.warning(f"Rate limit exceeded for {client_id}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
        )
    
    return True


def get_rate_limit_status(identifier: str) -> dict:
    """
    Get current rate limit status for an identifier.
    
    Args:
        identifier: Client identifier
    
    Returns:
        Dict with current usage and limits
    """
    if identifier not in rate_limiter.requests:
        return {
            "current": 0,
            "limit": 100,
            "remaining": 100,
            "reset": datetime.utcnow().timestamp() + 60,
        }
    
    current = len(rate_limiter.requests[identifier])
    limit = 100
    
    return {
        "current": current,
        "limit": limit,
        "remaining": max(0, limit - current),
        "reset": (datetime.utcnow() + timedelta(seconds=60)).timestamp(),
    }
