"""
Input validation and sanitization — prevent injection attacks and ensure data integrity.
"""
import re
from typing import Any, Optional
from pydantic import BaseModel, validator, Field


class SafeString(str):
    """String that's been sanitized for XSS prevention."""
    pass


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Sanitize a string to prevent XSS and injection attacks.
    
    Args:
        value: String to sanitize
        max_length: Maximum allowed length
    
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return str(value)
    
    # Truncate
    value = value[:max_length]
    
    # Remove control characters
    value = "".join(char for char in value if ord(char) >= 32 or char in "\n\t\r")
    
    # Escape HTML special characters
    html_escape_table = {
        "&": "&amp;",
        '"': "&quot;",
        "'": "&#x27;",
        ">": "&gt;",
        "<": "&lt;",
    }
    value = "".join(html_escape_table.get(char, char) for char in value)
    
    return value


def validate_sku(sku: str) -> bool:
    """
    Validate SKU format (alphanumeric and hyphens only).
    
    Args:
        sku: SKU to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not sku or len(sku) > 50:
        return False
    return bool(re.match(r"^[A-Z0-9\-]+$", sku))


def validate_uuid(value: str) -> bool:
    """
    Validate UUID format.
    
    Args:
        value: String to validate
    
    Returns:
        True if valid UUID, False otherwise
    """
    uuid_pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE,
    )
    return bool(uuid_pattern.match(value))


def validate_email(email: str) -> bool:
    """
    Validate email format (basic).
    
    Args:
        email: Email to validate
    
    Returns:
        True if valid email, False otherwise
    """
    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    return bool(email_pattern.match(email))


def validate_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
    
    Returns:
        True if valid URL, False otherwise
    """
    url_pattern = re.compile(
        r"^https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)$"
    )
    return bool(url_pattern.match(url))


def validate_quantity(value: int) -> bool:
    """
    Validate quantity (must be non-negative integer).
    
    Args:
        value: Value to validate
    
    Returns:
        True if valid, False otherwise
    """
    return isinstance(value, int) and value >= 0 and value <= 999999


def validate_confidence(value: float) -> bool:
    """
    Validate confidence score (must be between 0 and 1).
    
    Args:
        value: Value to validate
    
    Returns:
        True if valid, False otherwise
    """
    return isinstance(value, (int, float)) and 0.0 <= value <= 1.0


# Pydantic validators for common use cases

class ValidatedProductUpdate(BaseModel):
    """Validated product update schema."""
    sku: str = Field(..., max_length=50, pattern=r"^[A-Z0-9\-]+$")
    name: str = Field(..., max_length=255)
    category: str = Field(..., max_length=100)
    
    @validator("sku")
    def sku_must_be_valid(cls, v):
        if not validate_sku(v):
            raise ValueError("Invalid SKU format")
        return v
    
    @validator("name", "category", pre=True)
    def sanitize_strings(cls, v):
        if isinstance(v, str):
            return sanitize_string(v)
        return v


class ValidatedInventoryUpdate(BaseModel):
    """Validated inventory update schema."""
    quantity_estimate: int = Field(..., ge=0, le=999999)
    confidence: float = Field(..., ge=0.0, le=1.0)
    
    @validator("confidence")
    def confidence_must_be_valid(cls, v):
        if not validate_confidence(v):
            raise ValueError("Confidence must be between 0 and 1")
        return v


class ValidatedCameraConfig(BaseModel):
    """Validated camera configuration schema."""
    name: str = Field(..., max_length=255)
    location: str = Field(..., max_length=255)
    source_url: Optional[str] = Field(None, max_length=512)
    fps: int = Field(default=2, ge=1, le=60)
    
    @validator("name", "location", pre=True)
    def sanitize_strings(cls, v):
        if isinstance(v, str):
            return sanitize_string(v, max_length=255)
        return v
    
    @validator("source_url", pre=True)
    def validate_source_url(cls, v):
        if v and not validate_url(v):
            raise ValueError("Invalid source URL format")
        return v


# Request size limits
MAX_REQUEST_SIZE = 1024 * 1024  # 1MB
MAX_JSON_SIZE = 512 * 1024  # 512KB
MAX_QUERY_STRING_LENGTH = 2048
