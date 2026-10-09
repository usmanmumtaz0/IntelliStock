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

`current_quantity` is the PostgreSQL-backed trusted quantity and is changed only by reconciliation. `verified` is true only when the record is in a stable inventory state (`adequate`, `low_stock`, or `out_of_stock`), has at least the minimum reconciliation observations, meets the reconciliation confidence threshold, and has a recorded observation time.

`pending_quantity` is a differing latest observation from the transient Redis window. It is nullable, is not authoritative, and does not replace `current_quantity`. Missing product relationships produce nullable `sku`, `name`, and `threshold` rather than invented values.

Invalid enum values or pagination values return `422`.

Other inventory routes:

- `GET /inventory/{inventory_id}`
- `GET /inventory/zone/{zone_id}`
- `GET /inventory/product/{product_id}`
- `GET /inventory/status/low-stock`
- `POST /inventory/reconcile` (manager/admin; testing and integration endpoint)

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
