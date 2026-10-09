# Frontend-Backend Enhancement Contract

**Purpose:** Define API requirements for frontend integration with Phase 9 backend  
**Audience:** Frontend team  
**Status:** Specification for frontend implementation

---

## Dashboard Enhancements

### Main Dashboard Widgets

**1. Inventory Trends Widget**
```
GET /api/v1/analytics/inventory/trends?days=30&aggregation=daily

Shows:
- Line chart of quantity over time
- Trend indicator (up/down/stable)
- Average quantity
- Peak and low values

Frontend Use:
```jsx
<TrendChart data={response.data} />
```

**2. Product Performance Widget**
```
GET /api/v1/analytics/products/performance?limit=10

Shows:
- Table of top products
- Columns: Product, Movement Count, Depletion Rate, Trend
- Sort by high/low velocity

Frontend Use:
```jsx
<ProductRanking products={response.products} />
```

**3. Alert Summary Widget**
```
GET /api/v1/analytics/alerts/summary?days=30

Shows:
- Total alerts
- By severity (critical/warning/info)
- Resolution time
- Unresolved count

Frontend Use:
```jsx
<AlertMetrics data={response} />
```

**4. System Health Widget**
```
GET /api/v1/health/detailed

Shows:
- Overall status (healthy/degraded/unhealthy)
- Component breakdown
- Last update timestamp

Frontend Use:
```jsx
<HealthIndicator status={response.status} components={response.components} />
```

---

## Inventory Page Enhancements

### Historical View

```
GET /api/v1/inventory/{zone_id}/{product_id}/history?days=30&limit=50

Shows:
- Full change history
- Columns: Timestamp, From Qty, To Qty, Change Type, Source, Confidence
- Sortable by date
- Pagination

Frontend Use:
```jsx
const history = await api.get(`/inventory/${zoneId}/${productId}/history`);
<HistoryTable records={history.data} pagination={history.pagination} />
```

### Trend Analysis

```
GET /api/v1/inventory/{zone_id}/{product_id}/trend?days=30

Shows:
- Interactive chart of quantity trends
- Depletion rate calculation
- Confidence scores

Frontend Use:
```jsx
<InventoryTrendChart data={response.data} />
```

---

## Alerts Page Enhancements

### Alert Lifecycle Management

```
1. List Alerts
GET /api/v1/alerts?status=ACTIVE,ACKNOWLEDGED&limit=100

Returns:
- Alert ID
- Type (low_stock, camera_offline, anomaly)
- Severity (critical, warning, info)
- Status (CREATED, ACTIVE, ACKNOWLEDGED, RESOLVED)
- Zone/Product
- Timestamp
- Dedup count (for grouping)

2. Acknowledge Alert
POST /api/v1/alerts/{alert_id}/acknowledge
Body: { reason: "Already addressing" }

Returns: Updated alert with status=ACKNOWLEDGED

3. Resolve Alert
POST /api/v1/alerts/{alert_id}/resolve
Body: { reason: "Issue fixed" }

Returns: Updated alert with status=RESOLVED

4. View Alert History
GET /api/v1/alerts/{alert_id}/lifecycle

Returns: Full state change history
```

### Frontend UI Flow

```
Alert List (shows dedup_count)
  ↓
Click Alert → Detail View
  ↓
[Acknowledge] or [Resolve] buttons
  ↓
Modal for reason input
  ↓
Call API endpoint
  ↓
Update UI with new status
```

---

## Analytics Dashboard (New)

### Inventory Analytics

```
GET /api/v1/analytics/inventory/depletion?days=30

Shows:
- Products ranked by depletion rate
- Stockout risk indicators
- Restocking frequency
- Historical average vs current
```

### Zone Analytics

```
GET /api/v1/analytics/zones/performance?days=30

Shows:
- Zone efficiency ratings
- Most active zones
- Most stable zones
- Alert concentration
```

### System Analytics

```
GET /api/v1/analytics/system/performance?days=7

Shows:
- Event processing rate
- Detection accuracy
- Agent success rates
- API latency trends
```

---

## Agent Monitoring Page (New)

### Agent Overview

```
GET /api/v1/agents/{agent_type}/stats?days=30

Shows:
- Execution count
- Success rate (%)
- Avg confidence
- Avg execution time
- Common recommendations
```

### Execution History

```
GET /api/v1/agents/{agent_type}/history?days=30&limit=100

Shows:
- List of executions
- Status (COMPLETED/FAILED)
- Execution time
- Confidence score
- Timestamp

Click to see trace:
GET /api/v1/agents/{agent_type}/trace/{run_id}
Returns:
- Input parameters
- Reasoning steps (array)
- Output recommendation
- Confidence score
- Error (if failed)
```

### Failed Executions

```
GET /api/v1/agents/{agent_type}/failures?days=7

Shows:
- Failed execution list
- Error type
- Error message
- Timestamp

Helps debugging agent behavior
```

---

## Audit Trail Page (New)

### Audit Log Query

```
GET /api/v1/audit/logs?action=INVENTORY_UPDATE&days=30&limit=100

Shows:
- User action log
- Columns: Timestamp, User, Action, Resource, Old Value, New Value
- Sortable and filterable
```

### User Activity

```
GET /api/v1/audit/logs/user/{user_id}?days=30

Shows:
- All actions by specific user
- Proves non-repudiation (what did this user do?)
```

### Resource Changes

```
GET /api/v1/audit/logs/resource/inventory/{inventory_id}?limit=50

Shows:
- All changes to specific resource
- Complete audit trail
```

---

## System Health Page (New)

### Health Status

```
GET /api/v1/health/detailed

Shows:
- Overall system status
- Component breakdown:
  - Database (response time, connections)
  - Redis (memory, subscriptions)
  - Agents (last run time)
  - API (response time, error rate)

UI Pattern:
✅ Healthy (green)
⚠️ Degraded (yellow)
❌ Unhealthy (red)
```

---

## API Error Codes

All endpoints return:

```
200 OK              Success
400 Bad Request     Invalid params (validation error)
401 Unauthorized    Missing or invalid auth token
403 Forbidden       User lacks permission
404 Not Found       Resource doesn't exist
429 Too Many Req    Rate limit exceeded
500 Server Error    Internal error
503 Service Down    Service unavailable
```

**Error Response Format:**
```json
{
  "detail": "Error message",
  "code": "RESOURCE_NOT_FOUND",
  "timestamp": "2026-10-07T14:05:00Z"
}
```

---

## Authentication

All endpoints (except /health) require JWT token:

```
Authorization: Bearer {jwt_token}

Get token:
POST /api/v1/auth/login
Body: { email: "you@example.com", password: "<user-supplied-password>" }
Returns: { access_token: "...", token_type: "bearer" }
```

---

## Rate Limiting

Backend applies rate limits (HTTP 429):

```
Limit headers:
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1665137100

Frontend should:
- Display "Too many requests" error
- Suggest retrying in X seconds
- Respect Retry-After header if present
```

---

## Pagination Standard

All list endpoints support:

```
Query Params:
- limit=50 (default)
- offset=0 (default)

Response:
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

Frontend:
- Implement next/prev buttons
- Show "Page X of Y"
```

---

## Data Type Reference

### InventoryHistory
```json
{
  "id": "uuid",
  "zone_id": "string",
  "product_id": "string",
  "previous_quantity": 0,
  "new_quantity": 0,
  "change_type": "DETECTION|RECONCILIATION|MANUAL_UPDATE|...",
  "confidence": 0.95,
  "source_system": "reconciliation|cv|manual",
  "reason": "string",
  "created_at": "2026-10-07T14:05:00Z"
}
```

### Alert
```json
{
  "id": "uuid",
  "alert_type": "low_stock|camera_offline|anomaly",
  "severity": "critical|warning|info",
  "status": "CREATED|ACTIVE|ACKNOWLEDGED|RESOLVED",
  "zone_id": "string",
  "product_id": "string",
  "title": "string",
  "dedup_count": 5,
  "acknowledged_by": "user-001",
  "acknowledged_at": "2026-10-07T14:05:00Z",
  "created_at": "2026-10-07T14:00:00Z"
}
```

---

## Testing the APIs

**Use Postman/curl:**

```bash
# Get JWT token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"<user-supplied-password>"}'

# Use token in requests
curl -H "Authorization: Bearer {token}" \
  http://localhost:8000/api/v1/analytics/inventory/trends
```

---

## Documentation

All endpoints documented in:
- OpenAPI/Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Click "Try it out" to test endpoints directly.

---

**Document Version:** 1.0  
**Last Updated:** October 7, 2026

