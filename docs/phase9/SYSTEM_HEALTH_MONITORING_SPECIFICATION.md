# System Health Monitoring Specification

**Purpose:** Enhanced health checks for production monitoring  
**Component:** Backend observability  
**Priority:** MEDIUM (Phase 9.4)  
**Complexity:** Low  
**Estimated Effort:** 2 days

---

## Overview

Phase 8 has basic health endpoint. Phase 9 adds component-level health checks with structured responses for integration with monitoring systems.

---

## Health Components

```
System Health
├── Database (PostgreSQL)
├── Cache (Redis)
├── Background Jobs
├── AI Agents
├── Real-time Communications (WebSocket)
└── API Processing
```

---

## Health States

```
HEALTHY     - Component working perfectly
DEGRADED    - Component working but with issues
UNHEALTHY   - Component not working
```

---

## Endpoints

### 1. Basic Health

```
GET /api/v1/health

Response 200:
{
  "status": "ok",
  "database": "connected",
  "redis": "connected",
  "timestamp": "2026-10-07T14:05:00Z"
}
```

### 2. Detailed Health

```
GET /api/v1/health/detailed

Response 200:
{
  "status": "healthy",
  "timestamp": "2026-10-07T14:05:00Z",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5,
      "connections": "15/20",
      "queries_ok": true
    },
    "redis": {
      "status": "healthy",
      "response_time_ms": 2,
      "memory_usage_mb": 45,
      "subscriptions": 8
    },
    "agents": {
      "status": "healthy",
      "supervisor": {"status": "healthy", "last_run": "2026-10-07T14:04:00Z"},
      "insight": {"status": "healthy", "last_run": "2026-10-07T14:03:00Z"},
      "anomaly": {"status": "healthy", "last_run": "2026-10-07T14:02:00Z"},
      "notification": {"status": "healthy", "last_run": "2026-10-07T14:00:00Z"}
    },
    "api": {
      "status": "healthy",
      "avg_response_time_ms": 125,
      "error_rate": 0.001,
      "requests_per_minute": 450
    }
  }
}
```

### 3. Readiness Probe

```
GET /api/v1/health/ready

Response 200 (ready):
{
  "ready": true,
  "message": "Service is ready to accept traffic"
}

Response 503 (not ready):
{
  "ready": false,
  "message": "Waiting for database connection"
}
```

### 4. Liveness Probe

```
GET /api/v1/health/live

Response 200 (alive):
{
  "live": true,
  "uptime_seconds": 3600
}

Response 503 (dead):
{
  "live": false,
  "error": "Memory leak detected"
}
```

---

## Implementation

```python
class HealthService:
    def get_database_health(self) -> ComponentHealth:
        """Check database connectivity."""
        try:
            result = db.session.execute("SELECT 1")
            return ComponentHealth(
                status="healthy",
                response_time_ms=measure_time(),
                connections=get_pool_status()
            )
        except:
            return ComponentHealth(status="unhealthy")
    
    def get_redis_health(self) -> ComponentHealth:
        """Check Redis connectivity."""
        try:
            redis_client.ping()
            return ComponentHealth(
                status="healthy",
                memory_usage_mb=redis_client.info()['used_memory_mb']
            )
        except:
            return ComponentHealth(status="unhealthy")
    
    def get_agents_health(self) -> dict:
        """Check AI agent status."""
        agents = {}
        for agent in ["supervisor", "insight", "anomaly", "notification"]:
            last_run = get_agent_last_run(agent)
            is_stale = (now() - last_run) > timedelta(minutes=5)
            agents[agent] = {
                "status": "degraded" if is_stale else "healthy",
                "last_run": last_run
            }
        return agents
    
    def get_overall_health(self) -> SystemHealth:
        """Determine overall health."""
        components = {
            "database": self.get_database_health(),
            "redis": self.get_redis_health(),
            "agents": self.get_agents_health(),
            "api": self.get_api_health()
        }
        
        # Determine overall status
        if any(c.status == "unhealthy" for c in components.values()):
            return "unhealthy"
        elif any(c.status == "degraded" for c in components.values()):
            return "degraded"
        else:
            return "healthy"
```

---

## Monitoring Integration

### Prometheus Format (Optional)

```
# HELP intellistock_health_database_response_ms Database query response time
# TYPE intellistock_health_database_response_ms gauge
intellistock_health_database_response_ms 5

# HELP intellistock_health_agents_healthy Number of healthy agents
# TYPE intellistock_health_agents_healthy gauge
intellistock_health_agents_healthy 4

# HELP intellistock_api_error_rate API error rate
# TYPE intellistock_api_error_rate gauge
intellistock_api_error_rate 0.001
```

### Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /api/v1/health/live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /api/v1/health/ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

---

## Success Criteria

✅ All components health visible  
✅ Response <100ms  
✅ Accurate status reporting  
✅ Kubernetes compatible  
✅ Monitoring system integration ready  

---

**Document Version:** 1.0  
**Last Updated:** October 7, 2026

