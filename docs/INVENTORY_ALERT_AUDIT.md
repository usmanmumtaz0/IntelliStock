# Inventory alerts, thresholds, and email audit

## Audited flow

| Feature | Existing implementation | Verification | Result and completion |
| --- | --- | --- | --- |
| Authoritative quantity | `Inventory.quantity_estimate` with optimistic correction locking | API, PostgreSQL fixtures, rollback tests | Preserved; manual corrections and approved reconciliation remain authoritative |
| History and audit | Append-only inventory history plus user audit records | Authorized, unauthorized, conflict, and rollback tests | Working |
| Product threshold | `Product.low_stock_threshold` | Create/update schema, role checks, UI | Working; bounded to 0-1,000,000 |
| Alert generation | Transactional outbox followed by committed-row evaluation | Above, equal, below, zero, retry, and delayed-event tests | Working; active alert snapshots now refresh |
| Deduplication | Unique active key and active-condition lookup | Repeated-event and worker-retry tests | Working |
| Recovery and re-entry | Worker resolves obsolete active condition | Restock and immediate re-entry tests | Working; a genuine new episode is no longer hidden by cooldown |
| Dashboard | Persistent alert API, TanStack Query, WebSocket invalidation | API contracts and frontend tests | Working; cards now show quantity and threshold |
| Email | Opt-in SMTP worker and persistent delivery attempts | Mock TLS, failure, retry, recipient, stale-condition tests | Working when configured; content now includes required inventory context |
| Security | Exact route policy, role checks, server-only SMTP secrets | RBAC and response/log redaction tests | Working |

## Business rules

- Committed quantity is the source of truth. Pending camera observations never create stock alerts.
- Quantity `0` creates an out-of-stock condition.
- Quantity from `1` through the inclusive low-stock threshold creates a low-stock condition.
- Quantity above the threshold resolves active low/out-of-stock alerts.
- One active alert is allowed for each zone, product, and stock condition.
- Repeated worker events refresh the existing alert rather than creating duplicates.
- After recovery, a later threshold crossing creates a new alert episode.
- SMTP work is outside the inventory transaction. Delivery is persisted, allowlisted, retried with bounded backoff, and cancelled when the current condition is stale.

## Local commands

From `backend`:

```powershell
alembic upgrade head
python -m pytest -q
python -m app.workers.events
python -m app.workers.notifications
python -m scripts.check_email
```

A real SMTP test is explicit:

```powershell
python -m scripts.check_email --send-test --confirm-recipient approved@example.com
```

The confirmation address must already be present in `NOTIFICATION_EMAIL_TO`. The command reports SMTP acceptance, which does not prove inbox delivery.