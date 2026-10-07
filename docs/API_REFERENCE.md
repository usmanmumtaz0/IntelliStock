# IntelliStock API Reference

**Base URL:** `http://localhost:8000/api/v1`
**OpenAPI Docs:** `http://localhost:8000/docs`

## Authentication

Currently in development mode (no authentication). Phase 7+ will add JWT.

```
Authorization: Bearer <token>
```

## Response Format

All responses are JSON:

```json
{
  "status": "ok",
  "data": {},
  "error": null
}
```

---

## Endpoints

### Health & Status

#### GET /health
```bash
curl http://localhost:8000/health
```

Returns system health status.

### Dashboard

#### GET /dashboard/metrics
Aggregated KPI metrics for the overview screen.

**Response:**
```json
{
  "total_skus": 470,
  "active_cameras": 7,
  "total_cameras": 8,
  "low_stock_alerts": 3,
  "reconciliation_confidence": 93.5
}
```

#### GET /dashboard/store-info
Store/location metadata.

**Response:**
```json
{
  "name": "IntelliStock",
  "location": "Downtown Flagship",
  "floor": "Floor 1"
}
```

### Zones (Shelves)

#### GET /zones
List all shelf zones with health status.

**Query Params:**
- (none)

**Response:**
```json
[
  {
    "id": "A-1",
    "name": "A-1",
    "description": "Beverages · Water & Soda",
    "camera_id": "CAM-01",
    "camera_name": "Aisle A · North",
    "health": "healthy",
    "skus": 14,
    "confidence": 97.0,
    "aisle": "A",
    "label": "Beverages · Water & Soda"
  }
]
```

Health values: `healthy` | `low` | `offline` | `pending`

#### GET /zones/{zone_id}
Get a specific zone.

### Inventory

#### GET /inventory
List all inventory records.

**Query Params:**
- `zone_id` (optional): Filter by zone
- `product_id` (optional): Filter by product
- `status` (optional): Filter by status

**Response:**
```json
[
  {
    "id": "inv-123",
    "zone_id": "A-1",
    "product_id": "prod-456",
    "quantity_estimate": 48,
    "confidence": 0.97,
    "status": "adequate",
    "last_observation_time": "2026-10-07T15:30:00Z",
    "observations_count": 120
  }
]
```

Status values: `unknown` | `adequate` | `low_stock` | `out_of_stock` | `detection_uncertain` | `camera_offline`

#### POST /inventory/reconcile
Test reconciliation of an observation.

**Request:**
```json
{
  "camera_id": "CAM-01",
  "zone_id": "A-1",
  "product_id": "prod-456",
  "observed_quantity": 48,
  "confidence": 0.95
}
```

### Alerts

#### GET /alerts
List all active alerts.

**Query Params:**
- `acknowledged` (optional): Filter by true/false

**Response:**
```json
[
  {
    "id": "al-001",
    "type": "low_stock",
    "severity": "warning",
    "title": "Low stock: Lay's Classic",
    "detail": "Verified count 9, below threshold 18",
    "zone": "A-3",
    "sku": "SNK-2011",
    "min_ago": 3,
    "acknowledged": false
  }
]
```

Alert types: `low_stock` | `camera_offline` | `anomaly`
Severities: `critical` | `warning` | `info`

#### POST /alerts/{alert_id}/acknowledge
Mark an alert as acknowledged.

#### POST /alerts/acknowledge-all
Acknowledge all alerts.

### Events (Activity Feed)

#### GET /events
List recent reconciliation events.

**Query Params:**
- `limit` (default: 30, max: 100): Results to return

**Response:**
```json
[
  {
    "id": "evt-001",
    "zone": "A-3",
    "product": "Lay's Classic Salted 52g",
    "from_qty": 12,
    "to_qty": 9,
    "confidence": 96.0,
    "min_ago": 3
  }
]
```

#### GET /events/zone/{zone_id}
Filter events by zone.

#### GET /events/product/{product_id}
Filter events by product.

### Cameras

#### GET /cameras
List all cameras.

**Response:**
```json
[
  {
    "id": "CAM-01",
    "name": "Aisle A · North",
    "location": "Floor 1 · Aisle A · Bay 1–2",
    "is_active": true,
    "fps": 24,
    "offline_timeout_seconds": 30
  }
]
```

#### POST /cameras
Create a new camera.

#### PUT /cameras/{camera_id}
Update camera configuration.

#### DELETE /cameras/{camera_id}
Delete a camera.

### Products

#### GET /products
List all products (SKUs).

**Response:**
```json
[
  {
    "id": "prod-456",
    "sku": "BEV-1042",
    "name": "Coca-Cola Classic 330ml Can",
    "category": "Beverages"
  }
]
```

#### POST /products
Create a new product.

#### PUT /products/{product_id}
Update product details.

#### DELETE /products/{product_id}
Delete a product.

### Agents (AI / LLM)

#### GET /agents/runs
List agent execution history (for FYP evaluation).

**Query Params:**
- `agent_type`: Filter by agent type
- `status`: Filter by status
- `limit`: Max results (default: 50, max: 500)
- `hours`: Look back (default: 24)

**Response:**
```json
[
  {
    "id": "run-001",
    "agent_type": "insight",
    "status": "completed",
    "trigger_event": "low_stock_detected",
    "output_action": "recommend_restock",
    "confidence_score": 0.95,
    "execution_time_ms": 250,
    "created_at": "2026-10-07T15:30:00Z"
  }
]
```

#### GET /agents/runs/{run_id}
Get details of a specific agent run.

#### GET /agents/runs/{run_id}/trace
Get full execution trace (for debugging).

#### GET /agents/stats
Get agent performance statistics.

**Query Params:**
- `hours`: Stats period (default: 24)

**Response:**
```json
{
  "period_hours": 24,
  "total_runs": 127,
  "completed": 121,
  "failed": 6,
  "success_rate": 0.953,
  "by_agent_type": {
    "supervisor": 127,
    "insight": 45,
    "anomaly": 32,
    "notification": 44
  },
  "average_confidence": 0.942
}
```

### WebSocket

#### WS /ws
Real-time event stream.

**Connect:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

**Message Types:**
- `inventory_update`: Inventory state changed
- `alert_created`: New alert generated
- `camera_status`: Camera heartbeat or offline
- `agent_event`: Agent execution event

---

## Error Responses

Errors follow HTTP status codes:

- `400 Bad Request`: Invalid parameters
- `404 Not Found`: Resource doesn't exist
- `500 Internal Server Error`: Server error (check logs)

Error response body:
```json
{
  "detail": "Error message here"
}
```

---

## Rate Limiting

Not currently enforced (Phase 8 feature). Will implement in hardening pass.

---

## Pagination

Not currently implemented. Use `limit` parameter on list endpoints.

---

## Versioning

API version: `v1` (embedded in path `/api/v1/`)

Future versions will use `/api/v2/`, etc.

