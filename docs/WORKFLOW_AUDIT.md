# IntelliStock workflow audit

Audit date: 2026-10-11 (workspace date). Changes to application behavior and deployment
are awaiting owner approval. Only isolated audit tests and this report were added.

## Evidence collected

- Existing backend suite: 249 passed. Frontend: 19 passed. TypeScript: passed.
- New isolated audit tests: 1 passed, 2 strict expected failures documenting defects.
- Backend /health: HTTP 200, database connected, Redis disconnected, degraded.
- Frontend root: HTTP 200. This is not browser interaction acceptance.
- Supabase aggregate read: 34 unprocessed and unpublished outbox events, zero alerts,
  zero delivery records, two active cameras. Active flags do not prove camera connectivity.
- One approved configuration email attempted to the approved test address. Failed with
  SMTPServerDisconnected. Subsequent authentication-only diagnostic reached TLS successfully
  but disconnected during authentication. No SMTP acceptance or inbox delivery verified.
- No real inventory was changed in audit tests; tests used disposable SQLite databases.

## Findings and proposed fixes

### Critical: database API access can bypass backend permissions

Live pg_class/has_table_privilege checks found RLS disabled and anon SELECT/INSERT/UPDATE
grants on 17 public application tables, including chat conversations/turns, inventory,
audit logs, cameras, alerts and notification deliveries. Authenticated also has SELECT.
Users is protected. If these tables are exposed via Supabase Data API, backend JWT and
ownership checks do not protect that alternate path. Data API exposure was not probed;
no evidence of exploitation is claimed.

Proposed: reviewed migration to revoke browser-role access and enable RLS on all backend-only
tables; protect future tables/default privileges; verify owner/backend access and denied
browser access. Do not apply indiscriminate schema-wide changes to unrelated applications.

### High: final email eligibility does not recheck current inventory

app/services/notifications.py deliver_one checks alert stage, snooze and recipient, but not
the latest inventory quantity/state/threshold. The isolated restock test reproduces delivery
of a stale low-stock message after inventory is adequate while the alert has not caught up.

Proposed: recheck current inventory and threshold before submission; cancel obsolete stock
notifications, account for unknown/offline state, and preserve independent recipient retries.
SMTP still cannot guarantee exactly-once delivery or eliminate changes during transmission.

### High: delayed events can create alerts against newer stock

app/services/stock_alerts.py locks current inventory but prefers payload quantity/status.
The isolated test reproduces an old low-stock event creating an alert when current inventory
is already adequate. Worker serialization alone does not establish per-item event order across
multiple workers. Proposed: current-state/version validation and concurrency/order tests.

### High: event delivery/runtime incomplete

Redis is disconnected and the live outbox has 34 unprocessed rows. Event processing is not
demonstrated to be running. Redis absence directly blocks realtime publication; database rule
processing is a separate worker step and does not intrinsically require a successful Redis ping.
Proposed: choose local Docker/WSL installation or hosted Redis, run the event worker with health
monitoring, and verify queue drain, alerts and authenticated WebSocket updates. Review demo
events before enabling email because they can produce real messages.

### High: email authentication not verified

Configuration is syntactically complete but NOTIFICATIONS_ENABLED remains false. Gmail SMTP
disconnects during authentication; this result does not establish whether the cause is account
configuration, credentials or provider/network policy. Confirm the login is the actual mailbox
owning the app password and that it is allowed to send as the configured sender. Replace the
credential exposed in chat. Repeat only a single approved test before enabling the mail worker.

### Missing feature: screenshot evidence

Current emails are plain text. No frame-to-alert evidence capture/storage/attachment pipeline
is implemented. Proposed: timestamped shelf-cropped evidence tied to the committed observation,
bounded size/type/retention, private storage and explicit stale/missing-image handling. Manual
corrections must never invent a camera screenshot. Real acceptance needs footage and weights.

### Medium: manual-correction form retains its old version after a successful save

frontend/src/components/app/inventory-correction.tsx keeps snapshot state across saves; success
invalidates queries but does not adopt the returned update timestamp. A second save can yield
409 until the operator uses the existing Use latest count control. Preserve conflict protection
for external edits, but refresh the local snapshot after the user's own successful save.

### Medium: demo shelf configuration is not camera-ready

Seeded ROIs use coordinates up to 100, while ZoneInput requires normalized [0,1] coordinates.
Demo shelves have no model-class mappings. They are deliberately disabled placeholders, but
the current ROI prevents round-tripping through the normal shelf editor unchanged. Proposed:
normalize demo geometry without claiming real calibration; add mappings only when trained
classes are known. Do not invent production camera streams or turn on placeholder cameras.

## Manual status behavior verified

The normal correction API passes: quantity 2 at threshold 2 -> low_stock;
quantity 0 -> out_of_stock; quantity 10 -> adequate. Corrections already write history,
audit and outbox transactionally. Status is stock condition, not proof of camera verification.
Alert lifecycle and real-time refresh require the downstream event workflow.

## Approval plan

1. Lock down backend-only Supabase tables first and verify permissions.
2. Fix stale event/email eligibility and manual form version refresh with regression tests.
3. Normalize demo shelf geometry; connect Redis and supervise the worker after runtime choice.
4. Implement screenshot evidence with retention/privacy controls.
5. Resolve SMTP authentication; test one email, then review backlog and explicitly activate delivery.
6. Browser acceptance: login/roles, repeated corrections, stock transitions, alerts, history,
   reports, chatbot follow-ups, reconnect/retry behavior and camera evidence.

This is a scoped code/runtime audit, not a penetration test or certification. Real camera
accuracy, full browser interaction, real PostgreSQL concurrency, deliverability, deployed
HTTPS/backups and dependency vulnerability scanning remain unverified. Existing deprecation
warnings also remain. No automatic emails, permission migrations or behavioral fixes applied.
