# Phase 9: Complete API Specification

**Purpose:** All Phase 9 API endpoints with request/response contracts  
**Total Endpoints:** 25 new + 5 modified = 30 total new/modified (59 backend total)

---

## Inventory History Endpoints (5)

### 1. Get Zone/Product History

```
GET /api/v1/inventory/{zone_id}/{product_id}/history

Query Parameters:
  days=30                    # Last N days (default: 30)
  limit=50                   # Page size (default: 50)
  offset=0                   # Page offset (default: 0)
  change_type=DETECTION      # Filter by type (optional)
  source_system=reconcile    # Filter by source (optional)

Response 200:
{
  "data": [
    {
      "id": "hist-001",
      "zone_id": "zone-A",
      "product_id": "prod-X",
      "previous_quantity": 10,
      "new_quantity": 8,
      "quantity_delta": -2,
      "change_type": "DETECTION",
      "confidence": 0.95,
      "source_system": "reconciliation",
      "reason": "CV detection",
      "created_at": "2026-10-07T14:05:00Z"
    }
  ],
  "pagination": {
    "total": 150,
    "limit": 50,
    "offset": 0,
    "pages": 3
  }
}
```

### 2. Get Trend Data

```
GET /api/v1/inventory/{zone_id}/{product_id}/trend

Query Parameters:
  days=30                       # Period
  aggregation=daily             # hourly|daily|weekly

Response 200:
{
  "product": "Product X",
  "zone": "Zone A",
  "period": "30_days",
  "data": [
    {
      "date": "2026-10-07",
      "avg_quantity": 8.5,
      "min_quantity": 7,
      "max_quantity": 10,
      "changes": 3,
      "confidence": 0.94
    }
  ]
}
```

### 3. Get Recent Changes

```
GET /api/v1/inventory/history/recent

Query Parameters:
  limit=50                   # Default 50
  offset=0

Response 200:
{
  "data": [...],             # List of InventoryHistory
  "pagination": {...}
}
```

### 4. Get Changes by Type

```
GET /api/v1/inventory/history/by-type/{change_type}

Query Parameters:
  days=30
  limit=50
  offset=0
  zone_id=optional
  product_id=optional

Response 200:
{
  "change_type": "DETECTION",
  "count": 150,
  "data": [...],
  "pagination": {...}
}
```

### 5. Get Zone History

```
GET /api/v1/zones/{zone_id}/inventory/history

Query Parameters:
  days=30
  limit=100

Response 200:
{
  "zone": "Zone A",
  "total_changes": 450,
  "data": [...]
}
```

---

## Analytics Endpoints (8)

### 1. Inventory Trends

```
GET /api/v1/analytics/inventory/trends

Query Parameters:
  zone_id=optional
  product_id=optional
  days=30
  aggregation=daily

Response 200:
{
  "period": "30_days",
  "data": [...]
}
```

### 2. Depletion Analysis

```
GET /api/v1/analytics/inventory/depletion

Query Parameters:
  zone_id=optional
  days=30

Response 200:
{
  "analysis": [
    {
      "zone": "Zone A",
      "product": "Product X",
      "depletion_rate": 0.5,     # per day
      "total_depleted": 15,
      "events": 30,
      "trend": "stable",
      "eta_stockout": "2026-10-15"
    }
  ],
  "highest_depletion": "Product X"
}
```

### 3. Stockout Analysis

```
GET /api/v1/analytics/inventory/stockouts

Query Parameters:
  days=30
  threshold=2

Response 200:
{
  "stockouts": [
    {
      "zone": "Zone A",
      "product": "Product X",
      "date": "2026-10-06",
      "duration_hours": 4,
      "frequency": "2x in 30 days",
      "severity": "high"
    }
  ]
}
```

### 4. Product Performance

```
GET /api/v1/analytics/products/performance

Query Parameters:
  days=30
  sort_by=depletion|frequency|volatility
  limit=20

Response 200:
{
  "products": [
    {
      "sku": "X-123",
      "name": "Product X",
      "movements": 150,
      "depletion_rate": 1.0,
      "volatility": "low",
      "trend": "high_velocity"
    }
  ]
}
```

### 5. Zone Performance

```
GET /api/v1/analytics/zones/performance

Query Parameters:
  days=30
  sort_by=activity|stability

Response 200:
{
  "zones": [
    {
      "name": "Zone A",
      "activity": "high",
      "confidence": 0.93,
      "stockouts": 3,
      "health": "healthy"
    }
  ]
}
```

### 6. Alert Analytics

```
GET /api/v1/analytics/alerts/summary

Query Parameters:
  days=30
  severity=optional

Response 200:
{
  "total_alerts": 145,
  "by_severity": {...},
  "by_type": {...},
  "avg_resolution_hours": 2.5,
  "unresolved": 12
}
```

### 7. System Performance

```
GET /api/v1/analytics/system/performance

Query Parameters:
  days=7

Response 200:
{
  "events_processed": 50000,
  "avg_latency_ms": 125,
  "accuracy": 0.94,
  "api_availability": 0.9995,
  "agents": {...}
}
```

### 8. Comparison Analytics

```
GET /api/v1/analytics/compare

Query Parameters:
  compare_type=zone|product|period
  dimension1_id=required
  dimension2_id=required
  metric=depletion|activity

Response 200:
{
  "dimension1": {...},
  "dimension2": {...},
  "difference": 0.2,
  "winner": "dimension1"
}
```

---

## Alert Lifecycle Endpoints (5)

### 1. Acknowledge Alert

```
POST /api/v1/alerts/{alert_id}/acknowledge

Body:
{
  "reason": "Already addressing"
}

Response 200:
{
  "id": "alert-123",
  "status": "ACKNOWLEDGED",
  "acknowledged_by": "user-001",
  "acknowledged_at": "2026-10-07T14:05:00Z"
}
```

### 2. Resolve Alert

```
POST /api/v1/alerts/{alert_id}/resolve

Body:
{
  "reason": "Issue fixed"
}

Response 200:
{
  "id": "alert-123",
  "status": "RESOLVED",
  "resolved_by": "user-001",
  "resolution_reason": "Issue fixed"
}
```

### 3. Reopen Alert

```
POST /api/v1/alerts/{alert_id}/reopen

Body:
{
  "reason": "Issue recurred"
}

Response 200:
{
  "id": "alert-123",
  "status": "ACTIVE"
}
```

### 4. Get Alert Lifecycle

```
GET /api/v1/alerts/{alert_id}/lifecycle

Response 200:
{
  "id": "alert-123",
  "status": "RESOLVED",
  "created_at": "2026-10-06T10:00:00Z",
  "acknowledged_at": "2026-10-06T10:05:00Z",
  "resolved_at": "2026-10-06T10:15:00Z",
  "history": [
    {
      "from": "CREATED",
      "to": "ACKNOWLEDGED",
      "actor": "user-001",
      "reason": "Reviewing"
    }
  ]
}
```

### 5. List Active Alerts (Enhanced)

```
GET /api/v1/alerts

Query Parameters:
  status=ACTIVE|ACKNOWLEDGED|RESOLVED
  severity=critical|warning|info
  limit=50
  offset=0

Response 200:
{
  "alerts": [...],
  "counts": {
    "active": 12,
    "acknowledged": 8,
    "resolved": 145
  }
}
```

---

## Agent Execution Endpoints (4)

### 1. Get Agent Statistics

```
GET /api/v1/agents/{agent_type}/stats

Query Parameters:
  days=30

Response 200:
{
  "agent_type": "insight_agent",
  "total_executions": 1200,
  "success_count": 1164,
  "failure_count": 36,
  "success_rate": 0.97,
  "avg_confidence": 0.92,
  "avg_execution_time_ms": 120,
  "error_breakdown": {...}
}
```

### 2. Get Agent History

```
GET /api/v1/agents/{agent_type}/history

Query Parameters:
  days=30
  limit=100
  offset=0

Response 200:
{
  "agent_type": "anomaly_agent",
  "runs": [...]
}
```

### 3. Get Execution Trace

```
GET /api/v1/agents/{agent_type}/trace/{run_id}

Response 200:
{
  "agent": "anomaly_agent",
  "status": "COMPLETED",
  "input": {...},
  "reasoning_steps": [...],
  "output": {...},
  "confidence": 0.98
}
```

### 4. Get Failed Executions

```
GET /api/v1/agents/{agent_type}/failures

Query Parameters:
  days=7
  limit=50

Response 200:
{
  "agent_type": "insight_agent",
  "failures": [
    {
      "run_id": "run-123",
      "error_type": "timeout",
      "error_message": "LLM request timeout",
      "timestamp": "2026-10-07T10:00:00Z"
    }
  ]
}
```

---

## Audit Endpoints (3)

### 1. Query Audit Logs

```
GET /api/v1/audit/logs

Query Parameters:
  action=LOGIN|INVENTORY_UPDATE|ALERT_RESOLVED
  resource_type=inventory|alert|product
  user_id=optional
  days=30
  limit=100

Response 200:
{
  "logs": [
    {
      "id": "audit-001",
      "action": "INVENTORY_UPDATE",
      "user_id": "user-001",
      "resource_type": "inventory",
      "old_values": {"quantity": 10},
      "new_values": {"quantity": 8},
      "timestamp": "2026-10-07T14:05:00Z"
    }
  ]
}
```

### 2. User Activity

```
GET /api/v1/audit/logs/user/{user_id}

Query Parameters:
  days=30
  limit=100

Response 200:
{
  "user_id": "user-001",
  "actions": [...]
}
```

### 3. Resource Changes

```
GET /api/v1/audit/logs/resource/{resource_type}/{resource_id}

Query Parameters:
  limit=50

Response 200:
{
  "resource": "inventory-123",
  "type": "inventory",
  "changes": [...]
}
```

---

## Health Endpoints (3 Enhanced)

### 1. Basic Health

```
GET /api/v1/health

Response 200:
{
  "status": "ok",
  "database": "connected",
  "redis": "connected"
}
```

### 2. Detailed Health

```
GET /api/v1/health/detailed

Response 200:
{
  "status": "healthy",
  "components": {
    "database": "healthy",
    "redis": "healthy",
    "agents": "healthy",
    "comms": "healthy"
  }
}
```

### 3. Readiness/Liveness

```
GET /api/v1/health/ready
GET /api/v1/health/live

Response 200:
{
  "ready": true|false,
  "live": true|false
}
```

---

## Response Codes

All endpoints return:

```
200 OK              Success
400 Bad Request     Invalid parameters
401 Unauthorized    Auth required
403 Forbidden       Permission denied
404 Not Found       Resource not found
429 Too Many        Rate limited
500 Server Error    Internal error
503 Service Down    Unavailable
```

---

## Pagination Standard

All list endpoints support:

```
{
  "data": [...],
  "pagination": {
    "total": 1000,
    "limit": 50,
    "offset": 0,
    "pages": 20,
    "has_next": true,
    "has_prev": false
  }
}
```

---

## Rate Limiting

```
/api/v1/analytics/*     :  50 req/min
/api/v1/alerts/*        :  50 req/min
/api/v1/agents/*        :  50 req/min
/api/v1/audit/*         :  20 req/min (sensitive)
/api/v1/inventory/*     : 100 req/min
```

---

**Document Version:** 1.0  
**Last Updated:** October 7, 2026

