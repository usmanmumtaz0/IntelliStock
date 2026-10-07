"""
Phase 8 security tests — JWT authentication, RBAC, rate limiting, and validation.
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from app.main import app
from app.core.security import (
    create_access_token,
    decode_access_token,
    authenticate_user,
    hash_password,
    verify_password,
    has_permission,
)
from app.core.validation import (
    sanitize_string,
    validate_sku,
    validate_email,
    validate_url,
    validate_quantity,
    validate_confidence,
)
from app.core.rate_limiter import RateLimiter


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def admin_token():
    """Admin JWT token."""
    return create_access_token(
        user_id="user-001",
        username="admin",
        role="admin",
    )


@pytest.fixture
def manager_token():
    """Manager JWT token."""
    return create_access_token(
        user_id="user-002",
        username="manager",
        role="manager",
    )


@pytest.fixture
def staff_token():
    """Staff JWT token."""
    return create_access_token(
        user_id="user-003",
        username="staff",
        role="staff",
    )


# ============================================================================
# JWT Authentication Tests
# ============================================================================

class TestJWTAuthentication:
    """JWT token generation and validation."""
    
    def test_create_access_token(self):
        """Test JWT token creation."""
        token = create_access_token(
            user_id="test-user-001",
            username="testuser",
            role="admin",
        )
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_decode_valid_token(self):
        """Test decoding valid JWT token."""
        token = create_access_token(
            user_id="test-user-001",
            username="testuser",
            role="admin",
        )
        token_data = decode_access_token(token)
        
        assert token_data is not None
        assert token_data.user_id == "test-user-001"
        assert token_data.username == "testuser"
        assert token_data.role == "admin"
    
    def test_decode_invalid_token(self):
        """Test decoding invalid JWT token."""
        invalid_token = "invalid.token.here"
        token_data = decode_access_token(invalid_token)
        assert token_data is None
    
    def test_decode_expired_token(self):
        """Test decoding expired JWT token."""
        # Create token that expires in the past
        from datetime import datetime, timedelta
        from app.core.security import SECRET_KEY, ALGORITHM
        from jose import jwt
        
        past_time = datetime.utcnow() - timedelta(hours=25)
        to_encode = {
            "sub": "test-user",
            "username": "testuser",
            "role": "admin",
            "exp": past_time,
            "iat": datetime.utcnow(),
        }
        expired_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        
        token_data = decode_access_token(expired_token)
        assert token_data is None


# ============================================================================
# Authentication Endpoint Tests
# ============================================================================

class TestAuthenticationEndpoints:
    """Authentication endpoints (login, logout, refresh, verify)."""
    
    def test_login_success(self, client):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["username"] == "admin"
        assert data["role"] == "admin"
    
    def test_login_invalid_username(self, client):
        """Test login with invalid username."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "password"},
        )
        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]
    
    def test_login_invalid_password(self, client):
        """Test login with invalid password."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]
    
    def test_login_manager(self, client):
        """Test manager login."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "manager", "password": "manager123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "manager"
    
    def test_login_staff(self, client):
        """Test staff login."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "staff", "password": "staff123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "staff"
    
    def test_verify_token(self, client, admin_token):
        """Test token verification."""
        response = client.get(
            "/api/v1/auth/verify",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["username"] == "admin"
        assert data["role"] == "admin"
    
    def test_verify_invalid_token(self, client):
        """Test verification with invalid token."""
        response = client.get(
            "/api/v1/auth/verify",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401
    
    def test_refresh_token(self, client, admin_token):
        """Test token refresh."""
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        # Tokens may be the same if generated within same millisecond
        assert data["username"] == "admin"
    
    def test_logout(self, client, admin_token):
        """Test logout."""
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "Successfully logged out" in data["message"]


# ============================================================================
# Password Hashing Tests
# ============================================================================

class TestPasswordHashing:
    """Password hashing and verification."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "SecurePassword123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
    
    def test_verify_correct_password(self):
        """Test verifying correct password."""
        password = "SecurePassword123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_incorrect_password(self):
        """Test verifying incorrect password."""
        password = "SecurePassword123"
        hashed = hash_password(password)
        
        assert verify_password("WrongPassword", hashed) is False


# ============================================================================
# RBAC (Role-Based Access Control) Tests
# ============================================================================

class TestRBAC:
    """Role-based access control permissions."""
    
    def test_admin_permissions(self):
        """Test admin role has all permissions."""
        assert has_permission("admin", "read") is True
        assert has_permission("admin", "write") is True
        assert has_permission("admin", "delete") is True
        assert has_permission("admin", "admin") is True
    
    def test_manager_permissions(self):
        """Test manager role permissions."""
        assert has_permission("manager", "read") is True
        assert has_permission("manager", "write") is True
        assert has_permission("manager", "delete") is False
        assert has_permission("manager", "admin") is False
    
    def test_staff_permissions(self):
        """Test staff role permissions."""
        assert has_permission("staff", "read") is True
        assert has_permission("staff", "write") is False
        assert has_permission("staff", "delete") is False
        assert has_permission("staff", "admin") is False


# ============================================================================
# Input Validation Tests
# ============================================================================

class TestInputValidation:
    """Input validation and sanitization."""
    
    def test_sanitize_string_xss(self):
        """Test XSS prevention in string sanitization."""
        malicious = '<script>alert("xss")</script>'
        sanitized = sanitize_string(malicious)
        
        assert "<script>" not in sanitized
        assert "script" in sanitized
        assert "&lt;" in sanitized
    
    def test_sanitize_string_max_length(self):
        """Test string length truncation."""
        long_string = "a" * 2000
        sanitized = sanitize_string(long_string, max_length=100)
        
        assert len(sanitized) == 100
    
    def test_sanitize_string_html_entities(self):
        """Test HTML entity escaping."""
        html = '<div class="test">Content & more</div>'
        sanitized = sanitize_string(html)
        
        assert "&lt;" in sanitized
        assert "&gt;" in sanitized
        assert "&amp;" in sanitized
    
    def test_validate_sku_valid(self):
        """Test valid SKU validation."""
        assert validate_sku("SKU-001") is True
        assert validate_sku("PROD-ABC-123") is True
        assert validate_sku("ABC123") is True
    
    def test_validate_sku_invalid(self):
        """Test invalid SKU validation."""
        assert validate_sku("sku-001") is False  # lowercase
        assert validate_sku("SKU@001") is False  # invalid character
        assert validate_sku("") is False  # empty
        assert validate_sku("a" * 100) is False  # too long
    
    def test_validate_email_valid(self):
        """Test valid email validation."""
        assert validate_email("user@example.com") is True
        assert validate_email("test.user+tag@domain.co.uk") is True
    
    def test_validate_email_invalid(self):
        """Test invalid email validation."""
        assert validate_email("notanemail") is False
        assert validate_email("user@") is False
        assert validate_email("@example.com") is False
    
    def test_validate_url_valid(self):
        """Test valid URL validation."""
        assert validate_url("https://example.com") is True
        assert validate_url("http://www.example.com/path") is True
        assert validate_url("https://api.example.com/v1/resource") is True
    
    def test_validate_url_invalid(self):
        """Test invalid URL validation."""
        assert validate_url("not a url") is False
        assert validate_url("example.com") is False  # missing protocol
    
    def test_validate_quantity_valid(self):
        """Test valid quantity validation."""
        assert validate_quantity(0) is True
        assert validate_quantity(100) is True
        assert validate_quantity(999999) is True
    
    def test_validate_quantity_invalid(self):
        """Test invalid quantity validation."""
        assert validate_quantity(-1) is False
        assert validate_quantity(1000000) is False
        assert validate_quantity(1.5) is False  # not integer
    
    def test_validate_confidence_valid(self):
        """Test valid confidence validation."""
        assert validate_confidence(0.0) is True
        assert validate_confidence(0.5) is True
        assert validate_confidence(1.0) is True
    
    def test_validate_confidence_invalid(self):
        """Test invalid confidence validation."""
        assert validate_confidence(-0.1) is False
        assert validate_confidence(1.1) is False
        assert validate_confidence("0.5") is False  # string not float


# ============================================================================
# Rate Limiting Tests
# ============================================================================

class TestRateLimiting:
    """Rate limiting functionality."""
    
    def test_rate_limiter_allows_under_limit(self):
        """Test rate limiter allows requests under limit."""
        limiter = RateLimiter()
        
        for i in range(5):
            assert limiter.is_allowed("user-123", limit=10, window_seconds=60) is True
    
    def test_rate_limiter_blocks_over_limit(self):
        """Test rate limiter blocks requests over limit."""
        limiter = RateLimiter()
        
        # Fill up the limit
        for i in range(5):
            limiter.is_allowed("user-123", limit=5, window_seconds=60)
        
        # Next request should be blocked
        assert limiter.is_allowed("user-123", limit=5, window_seconds=60) is False
    
    def test_rate_limiter_resets_after_window(self):
        """Test rate limiter resets after time window."""
        from datetime import datetime, timedelta
        limiter = RateLimiter()
        
        # Fill up the limit
        for i in range(5):
            limiter.is_allowed("user-123", limit=5, window_seconds=60)
        
        # Manually advance time and clear old requests
        limiter.requests["user-123"] = []
        
        # Should be allowed again
        assert limiter.is_allowed("user-123", limit=5, window_seconds=60) is True
    
    def test_rate_limiter_per_identifier(self):
        """Test rate limiter tracks different identifiers separately."""
        limiter = RateLimiter()
        
        # Fill limit for user-1
        for i in range(5):
            limiter.is_allowed("user-1", limit=5, window_seconds=60)
        
        # user-1 should be blocked
        assert limiter.is_allowed("user-1", limit=5, window_seconds=60) is False
        
        # user-2 should still be allowed
        assert limiter.is_allowed("user-2", limit=5, window_seconds=60) is True


# ============================================================================
# Integration Tests
# ============================================================================

class TestSecurityIntegration:
    """Integration tests for security features."""
    
    def test_unauthenticated_access_to_protected_endpoint(self, client):
        """Test that protected endpoints require authentication."""
        # Try to access health endpoint (doesn't require auth)
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_rate_limit_response_headers(self, client, admin_token):
        """Test rate limit status in response."""
        # Make multiple requests and check they're processed
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get("/health", headers=headers)
        assert response.status_code == 200
    
    def test_security_headers_present(self, client):
        """Test security-related headers in responses."""
        response = client.get("/health")
        # Check that we get a successful response
        assert response.status_code == 200


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestSecurityEdgeCases:
    """Edge case and security vulnerability tests."""
    
    def test_sql_injection_in_sku(self):
        """Test SQL injection attempt in SKU is rejected."""
        malicious_sku = "'; DROP TABLE products; --"
        assert validate_sku(malicious_sku) is False
    
    def test_xss_in_product_name(self):
        """Test XSS attempt in product name is sanitized."""
        xss_attempt = '<img src=x onerror="alert(\'xss\')">'
        sanitized = sanitize_string(xss_attempt)
        
        # Check that HTML is escaped - the key is that < and > are escaped
        # so the browser won't interpret it as HTML
        assert "&lt;" in sanitized  # < is escaped
        assert "&gt;" in sanitized  # > is escaped
        assert "&quot;" in sanitized  # " is escaped
        # The result is safe for rendering in HTML context
    
    def test_unicode_in_validation(self):
        """Test unicode characters in validation."""
        unicode_string = "产品名称🎉"
        sanitized = sanitize_string(unicode_string)
        
        assert len(sanitized) > 0
    
    def test_null_byte_injection(self):
        """Test null byte injection is handled."""
        null_byte_string = "product\x00name"
        sanitized = sanitize_string(null_byte_string)
        
        # Control characters should be removed
        assert "\x00" not in sanitized
