# IntelliStock API Reference

Base URL: `http://localhost:8000/api/v1`

Interactive OpenAPI documentation is available at `/docs`.

## Public endpoints

Only these endpoints are intentionally public:

- `GET /health` and `GET /api/v1/health`: liveness/readiness checks needed by deployment infrastructure.
- `POST /api/v1/auth/login`: obtains an access token.
- `/docs`, `/redoc`, and `/openapi.json`: API documentation; disable these at the deployment edge if the API must not expose its schema publicly.

Detailed health, inventory, product, camera, event, alert, agent, and audit endpoints require an active database user and a valid bearer token.

## Authentication

### POST `/auth/login`

The login identifier is always a normalized email. Usernames and client-supplied roles are not accepted.

```json
{
  "email": "operator@example.com",
  "password": "user-supplied-password"
}
```

Successful response:

```json
{
  "access_token": "signed-jwt",
  "token_type": "bearer",
  "user_id": "uuid",
  "username": "operator",
  "email": "operator@example.com",
  "role": "staff"
}
```

Send the token on subsequent requests:

```http
Authorization: Bearer signed-jwt
```

### Swagger authorization

1. Open `http://127.0.0.1:8000/docs` and run `POST /api/v1/auth/login`.
2. Copy only the returned `access_token` value.
3. Select **Authorize** at the top right of Swagger UI.
4. Paste the token into **BearerAuth**. Swagger adds the `Bearer` prefix automatically.
5. Run `GET /api/v1/auth/verify` to confirm the current role and permissions.
6. Select **Authorize**, then **Logout**, before repeating the test with another role.

Missing or invalid authentication returns `401`. A valid token without the required
permission returns `403`. Do not paste the JSON response or the text `Bearer`; paste
only the JWT access-token value into the Swagger dialog.

Authentication failures return the same `401` message for unknown emails, wrong passwords, and inactive users. Missing, expired, malformed, or tampered tokens also return `401`. An authenticated user without the required role receives `403`.

### Role policy

| Operation | Staff | Manager | Admin |
|---|---:|---:|---:|
| Read operational resources | Yes | Yes | Yes |
| Create/update products and cameras | No | Yes | Yes |
| Submit reconciliation through the test API | No | Yes | Yes |
| Acknowledge/resolve/dismiss alerts | No | Yes | Yes |
| Delete products and cameras | No | No | Yes |
| Read audit and detailed health records | No | No | Yes |
| Upload and review video jobs | Yes | Yes | Yes |
| Start jobs from configured cameras | No | No | Yes |

## Video processing

- `POST /video-jobs` accepts a multipart MP4, AVI, or MOV plus bounded sampling options.
- `POST /video-jobs/images` accepts a multipart JPG, PNG, or WebP and queues one-frame detection.
- `POST /video-jobs/cameras/{camera_id}` queues a bounded capture from a server-configured camera (admin only).
- `GET /video-jobs` and `GET /video-jobs/{id}` return job state and aggregate results.
- `GET /video-jobs/{id}/frames` returns timestamps, detections, normalized/pixel boxes, confidence, and track IDs.
- `GET /video-jobs/{id}/frames/{frame_id}/image` returns a private annotated JPEG.
- `POST /video-jobs/{id}/cancel` requests cancellation.

Job responses never expose storage paths or camera credentials. Detection instances and unique tracks are
review evidence; these endpoints do not mutate committed inventory.

## Inventory contract

### GET `/inventory`

Query parameters:

- `zone_id`: optional exact zone ID.
- `product_id`: optional exact product ID.
- `status`: optional inventory state enum.
- `limit`: 1–500, default 100.
- `offset`: zero or greater, default 0.

The body remains a JSON array for backward compatibility. Pagination metadata is returned in `X-Total-Count` and `Content-Range` headers.

```json
[
  {
    "id": "inventory-uuid",
    "zone_id": "zone-uuid",
    "product_id": "product-uuid",
    "sku": "BEV-1042",
    "name": "Example Product",
    "current_quantity": 12,
    "threshold": 5,
    "status": "adequate",
    "verified": true,
    "pending_quantity": null,
    "confidence": 0.92,
    "last_observation_time": "2026-10-09T10:30:00Z",
    "observations_count": 3,
    "updated_at": "2026-10-09T10:30:00Z"
  }
]
```

`current_quantity` is the PostgreSQL-backed committed quantity. It can change through trusted reconciliation, an audited physical-count correction, or an audited checkout transaction. `verified` is true only when camera evidence meets the reconciliation requirements; manual changes remain committed and audited without being labeled camera-verified.

`pending_quantity` is a differing latest observation from the transient Redis window. It is nullable, is not authoritative, and does not replace `current_quantity`. Missing product relationships produce nullable `sku`, `name`, and `threshold` rather than invented values.

Invalid enum values or pagination values return `422`.

Other inventory routes:

- `GET /inventory/{inventory_id}`
- `GET /inventory/zone/{zone_id}`
- `GET /inventory/product/{product_id}`
- `GET /inventory/status/low-stock`
- `POST /inventory/{inventory_id}/corrections` (manager/admin; set a physical or starting count)
- `POST /inventory/{inventory_id}/checkout` (manager/admin; subtract sold units)
- `POST /inventory/reconcile` (manager/admin; testing and integration endpoint)

Checkout request:

```json
{
  "quantity": 2,
  "reason": "Customer checkout",
  "expected_updated_at": "2026-10-22T12:00:00Z"
}
```

`quantity` is the number of units sold, not the resulting stock. The server locks the shelf and inventory row, rejects stale versions and quantities above available stock, records a `SALE` history entry, and subtracts the units atomically. `reason` is optional. Inventory in `unknown` or `detection_uncertain` state requires a physical starting count before checkout.

Every committed correction, checkout, or accepted reconciliation publishes a durable `stock_updated` event. The event worker creates or refreshes one active low-stock/out-of-stock alert when the resulting quantity is at or below the configured product threshold. The notification worker queues and sends that alert only when `NOTIFICATIONS_ENABLED=true` and the SMTP/recipient settings are complete. Repeated stock events refresh the active alert instead of sending duplicate alert episodes.

## Frontend field mapping

Python code and database models use snake_case. Pydantic response aliases define the only JSON mapping for activity and alert fields:

| Python field | JSON field |
|---|---|
| `from_qty` | `from` |
| `to_qty` | `to` |
| `min_ago` | `minAgo` |

The API does not emit duplicate snake_case and camelCase versions. Unknown event quantities are returned as `null`; the server does not fabricate zero quantities.

## Endpoint groups

All routes below require bearer authentication unless the public list above says otherwise.

- Dashboard: `GET /dashboard/metrics`, `GET /dashboard/store-info`
- Zones: `GET /zones`, `GET /zones/{zone_id}`
- Products: list/get; manager/admin create/update; admin delete
- Cameras: list/get; manager/admin create/update; admin delete
- Alerts: `GET /alerts` with lifecycle filters and pagination; manager/admin acknowledge, acknowledge-all, resolve, and dismiss mutations
- Events: `GET /events`, `/events/zone/{zone_id}`, `/events/product/{product_id}`
- Inventory history: recent, by zone/product/type, and depletion metrics
- Agents: run history, trace, and statistics
- Audit and detailed health: admin only

## WebSocket

Connect to `WS /ws/inventory`. Authentication is required before the socket is accepted. Browser clients may provide an access token through the `token` query parameter; non-browser clients may use `Authorization: Bearer ...`.

```javascript
const socket = new WebSocket(
  `ws://localhost:8000/ws/inventory?token=${encodeURIComponent(accessToken)}`,
);
```

Use TLS (`wss://`) in production. Because query parameters may be recorded by proxies, configure access logs to redact the `token` parameter and prefer an authorization header when the client supports it.

Inventory events use a versioned envelope. `type`, `version`, `occurred_at`, and `data` are stable envelope fields; the version-1 payload is also present at the top level for compatibility with existing consumers. Clients should use the envelope and refetch authoritative REST resources after an event rather than treating a camera event as inventory truth.

## Rate limiting

Login attempts are limited on the effective `/api/v1/auth/login` route by both direct peer IP and a SHA-256 digest of the normalized email. Limits are configured with `RATE_LIMIT_LOGIN_REQUESTS` and `RATE_LIMIT_LOGIN_WINDOW_SECONDS`.

Redis provides shared counters across workers. If Redis is unavailable, the application logs a warning and uses a process-local fallback; that fallback cannot coordinate multiple workers. Arbitrary forwarded IP headers are ignored unless `TRUSTED_PROXY_HEADERS=true` is deliberately configured behind a trusted proxy.

A blocked request returns:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
```

```json
{"detail": "Too many login attempts. Please try again later."}
```

## Vision processing and identity

- `POST /video-jobs` uploads a bounded video job.
- `POST /video-jobs/images` uploads a JPG, PNG, or WebP job.
- `POST /video-jobs/cameras/{camera_id}` queues an administrator-only bounded camera job.
- `GET /video-jobs/model-health` reports checkpoint/manifest/device readiness without downloading a model.
- `GET /video-jobs/review-queue` returns owner-scoped unresolved identity evidence.
- `POST /video-jobs/detections/{detection_id}/identify` lets an authorized manager/admin attach a catalog item without changing inventory.

Detection responses include `identity_status`, `identity_confidence`, category, optional catalog
product metadata, and evidence. Supported states are `identified`, `category_only`, `unknown`, and
`ambiguous`. Job changes publish durable `vision_job_updated` events; clients must refetch the REST
resource and must not treat WebSocket payloads or bounding-box counts as authoritative stock.
