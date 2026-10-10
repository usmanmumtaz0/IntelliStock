# Phase 5: notifications and operational reports

## What is implemented

- **Reports** in the console navigation: current inventory summary, stock-state counts, active-alert count and recorded change types for 1–90 days, optionally filtered by shelf.
- Authenticated CSV exports for current inventory or history. Current inventory includes last committed quantities even for offline/uncertain shelves; it is not a fresh physical-stock guarantee. History deltas are not sales or revenue.
- **Settings → Email notifications & delivery history**: administrator-only readiness and paginated durable attempts. No secrets are returned, and the UI cannot enable delivery or choose recipients.
- A standalone worker using the same backend package/database, not a new microservice or broker. SMTP failures do not run in reconciliation, stock-rule or HTTP request transactions.
- Migration `0004_notification_delivery` adds persistent attempts, recipient/stage uniqueness, retry times and outcomes. Existing inventory/alert data is preserved.

No new Python packages are required: SMTP/TLS, email formatting and CSV use Python's standard library. Existing `requirements.txt` installation remains sufficient. SMS, webhooks, scheduled email reports, PDF exports and chatbot changes are **not implemented** in this phase.

## Safe default

`NOTIFICATIONS_ENABLED=false` is the default and remains false in the local `.env`. Credentials alone do not enable delivery. Docker's notification worker is additionally behind the `notifications` profile. No external email was sent during implementation or tests.

Do not enable until the owner approves the destinations and a real-mail test. `NOTIFICATION_EMAIL_TO` accepts **1–20 comma-separated plain email addresses**. Exact duplicate addresses are removed; an invalid entry disables the whole list. Each recipient gets a separate message, delivery record and retry schedule. Enabling queues currently OPEN/ESCALATED, unsnoozed alerts, including older unresolved alerts—not only future alerts. Review the backlog before activation. Adding a recipient can queue active alerts to that new recipient; pending deliveries to removed recipients are cancelled.

Set these server-side values only in ignored `.env` files (never `VITE_*`):

```dotenv
NOTIFICATIONS_ENABLED=false
NOTIFICATION_EMAIL_TO=
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_SECURITY=starttls
SMTP_TIMEOUT_SECONDS=10
NOTIFICATION_MAX_ATTEMPTS=5
```

Use `SMTP_SECURITY=ssl` with the provider's implicit-TLS port when appropriate. Plaintext SMTP is unsupported. TLS certificates are verified. The authenticated SMTP sender must be permitted by your provider. Configure both the API and worker consistently; restart/recreate them after changing environment variables. Settings readiness describes API configuration, **not proof that a worker is running or SMTP credentials are accepted**.

## Start after approval and configuration

### Check setup and send an isolated test

From `backend`, with the project's virtual environment activated:

```powershell
python -m scripts.check_email
```

This lists missing setting names only and makes no network requests. Fill the
SMTP fields above in the root ignored `.env` using your mail provider's SMTP
credentials (not your IntelliStock login password). Quote passwords, especially
when they contain special characters. No additional Python library is needed.

Keep `NOTIFICATIONS_ENABLED=false` while testing. After approving the destination,
explicitly send one test to the exact address saved in `NOTIFICATION_EMAIL_TO`:

```powershell
python -m scripts.check_email --send-test --confirm-recipient "recipient@example.com"
```

Replace the example with one approved address from the list; the test sends only to that address, not the entire list. This sends no inventory data,
creates no alert/delivery rows and does not enable automatic notifications.
It uses the same verified-TLS transport as real alerts. Check the inbox and spam
folder; SMTP acceptance alone cannot confirm delivery. Errors expose exception
types only, never SMTP credentials or provider response text.

Then review unresolved alerts, set `NOTIFICATIONS_ENABLED=true`, restart the API
and start the worker below. Existing OPEN/ESCALATED alerts can be emailed on
activation. Do not start automatic delivery until that backlog is approved.

From `backend`, using the installed virtual environment:

```powershell
python -m alembic upgrade head
python -m app.workers.notifications
```

Or after deployment configuration:

```powershell
docker compose --profile notifications up -d --build
```

Activation also requires setting `NOTIFICATIONS_ENABLED=true`. We have not done that. To stop future sends, stop the notification worker immediately and set the flag false before restarting it. An already in-flight SMTP submission cannot be recalled.

## Delivery guarantees and limitations

- One durable row per alert/stage/recipient. OPEN and ESCALATED are separate stages; ACKNOWLEDGED, IN_PROGRESS and closed alerts do not generate new emails.
- The worker rechecks current stage, recipient and snooze before attempting mail. Obsolete stages/recipients become `cancelled`; snoozed attempts are deferred.
- Retries use bounded exponential delay (first retry 60 seconds, capped at one hour). Default maximum five attempts. Terminal `failed` records are retained for inspection, not automatically requeued forever. There is no manual retry endpoint yet.
- `accepted` means the SMTP server accepted the submission. It does **not** prove inbox delivery, reading, or absence of later bounces.
- SMTP does not provide transactional exactly-once delivery. A crash after submission but before database commit can cause a duplicate on restart. A stable Message-ID helps diagnosis but is not a guarantee of recipient-side deduplication. Attempts interrupted before commit may not be reflected in the recorded count.
- A message can become obsolete while SMTP is in flight. Always review current inventory before acting; email states the quantity was captured when the alert was created.
- Failures store exception class names only, not provider error strings or passwords. Delivery recipients/history are visible only to administrators.
- The existing LangGraph notification formatter now reports `planned`, not `queued`; it is not a second mail delivery path.

## Report contracts

- `GET /api/v1/reports/summary?days=7&zone_id=...`
- `GET /api/v1/reports/export?kind=inventory|history&days=7&zone_id=...`
- `GET /api/v1/notifications/configuration` (admin)
- `GET /api/v1/notifications/deliveries?limit=25&offset=0` (admin)

All reports require authentication; existing single-store read permissions apply. The history window is rolling UTC time. Inventory is current state, independent of the history window. CSVs include UTF-8 BOM, UTC timestamps, proper CSV quoting and formula escaping for untrusted textual fields. Numeric negative deltas remain numbers. Exports reject more than 10,000 rows with HTTP 413 instead of silently truncating; narrow the shelf/history window. These are live operational queries, not a transactionally frozen accounting ledger.

## Acceptance

Automated tests use disposable SQLite databases and fake SMTP transports, covering opt-out, duplicate prevention, retry exhaustion, snooze/cancellation, TLS paths, permissions, aggregation and CSV escaping. CI's disposable PostgreSQL/Redis smoke now also exercises notification queueing with an injected fake sender; it never contacts a mail provider.

Docker/PostgreSQL/Redis remain unavailable locally. Service-backed CI/deployment execution, real-browser acceptance and an approved real-recipient mail test remain pending. Training/model validation remains Phase 7; subsequent Assistant implementation is documented in [Phase 6](PHASE_6_ASSISTANT.md).
