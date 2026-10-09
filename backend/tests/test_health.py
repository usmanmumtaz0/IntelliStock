"""
Smoke tests for health endpoint.
"""
import pytest


def test_health_endpoint(client):
    """
    Test that GET /health returns 200 OK with expected structure.
    """
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    assert "database" in data
    assert "redis" in data
    
    assert data["status"] in ["ok", "degraded"]
    assert data["database"] in ["connected", "disconnected"]
    assert data["redis"] in ["connected", "disconnected"]


def test_health_endpoint_all_connected(client, monkeypatch):
    """
    Test that /health returns "ok" status when all services are connected.
    """
    monkeypatch.setattr("app.main.check_database", lambda: True)
    monkeypatch.setattr("app.main.check_redis", lambda: True)
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # For this test to pass, both database and redis must be running
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert data["redis"] == "connected"


def test_api_health_endpoint(client, monkeypatch):
    """
    Test that GET /api/v1/health returns the same response as /health.
    """
    monkeypatch.setattr("app.main.check_database", lambda: True)
    monkeypatch.setattr("app.main.check_redis", lambda: True)
    response = client.get("/api/v1/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert data["redis"] == "connected"
