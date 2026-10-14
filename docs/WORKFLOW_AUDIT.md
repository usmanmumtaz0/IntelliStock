# IntelliStock workflow audit

Original audit date: 2026-10-11. The findings below preserve the original evidence.
Owner-approved remediation was implemented on 2026-10-14 as summarized here.

## RBAC Phase 6 verification - 2026-10-14

Approved automated verification: all 285 backend tests and 36 frontend tests passed.
TypeScript, production build and whitespace checks passed. ESLint reported zero errors
and 10 existing fast-refresh warnings; backend dependency/deprecation warnings remain.
Seven additional HTTP-handler tests exercise real password login and permission contracts
for Admin/Manager/Staff, operational reads, restricted settings/exports, disabled sessions
and forged role headers. Tests use isolated databases, not production accounts or inventory.

Found and fixed one contract mismatch: signup approval controls checked users.update while
the backend requires users.create. A rendered-control regression test now verifies both
allowed and denied cases. No unrelated features, dependencies or schema changes introduced.

Reloaded the identified local backend with current code (parent PID 38104), retaining the
working transaction-pool port 6543 override and leaving .env unchanged. Live saved-admin
login/verification succeeded. Authenticated bounded inventory, alerts, requests, operational
audit, cameras, chat status and conversation listing returned 200. Anonymous chat returned
401; chat responses included private/no-store. Direct bounded database SELECT succeeded.
Frontend root and Requests URLs returned 200; this is not browser interaction acceptance.

An initial inventory HTTP connection disconnected and the next login timed out; a later
bounded check passed across these endpoints. Cause remains unconfirmed; do not interpret
the passing smoke check as load/reliability certification. Database health was connected,
Redis disconnected. No test emails or inventory writes were issued. Existing workers were
left running; this does not assert they never performed their normal scheduled work.

Remaining acceptance: browser interactions/session transitions, live Manager/Staff accounts,
PostgreSQL concurrent review/correction races, Redis-backed delivery and real trained-camera
accuracy. Browser automation packages and local PostgreSQL/Docker tooling were not available;
none were installed and no remote test schema/accounts were created. Approval is required
before Phase 7 delivery work. This phase is automated verification plus limited live smoke
testing, not a full production security/reliability sign-off.

## RBAC Phase 5 handoff - 2026-10-14

Separately approved chatbot authorization work is complete in code. Retrieval requires
both the relevant chatbot permission and underlying resource permissions before querying,
including product clarification and shelf evidence. The graph validates previous plans
before sending context to a provider. Invalid plans produce safe denials, not database
queries or raw validation details. Answers remain deterministic, read-only database results;
LLM plans cannot select arbitrary SQL, tools, actors or permission scopes.

Saved turns, retries and follow-ups recheck current permissions. Conversation-list titles
are replaced with a generic restricted label if saved content is no longer authorized.
Owner-private conversation access still applies even to administrators. Owners can delete
restricted conversations. Turn processing also rechecks the account session version after
acquiring its lock, alongside activation and pending-signup status.

Chat HTTP responses, including authorization failures, now use private/no-store headers.
There is no shared server answer cache or persistent graph checkpoint to partition. Existing
frontend caches use account IDs and are cleared/remounted on authorization changes.
No vector store was introduced: the current single-store read scope is shared by all three
roles, with server-owned permission checks; no fictitious shelf assignments are claimed.

Verification: 41 targeted chat/RBAC tests and all 278 backend tests passed. Tests use isolated
SQLite and fake/local providers, exercising underlying access denial, saved-history/replay/
follow-up/title revocation, injected model plans, malformed stored plans, provider context
protection and non-cacheable responses. Whitespace check passed. Existing deprecation
warnings remain. No production mutations, external LLM calls, emails, migrations or
environment changes. API restart/reload was not performed; live deployment verification,
browser workflows and PostgreSQL concurrency tests remain pending for Phase 6 approval.

## RBAC Phase 4 handoff - 2026-10-14

Implemented after separate approval. Navigation, protected routes and mutation controls
use permissions returned by authentication APIs, not inferred role privileges. Settings
sections, report exports, alert actions, stock corrections, threshold editing and camera/
shelf configuration follow the Phase 3 server policy. Backend remains the security boundary.

The new Requests page supports physical counts, discrepancies and restock submissions,
scoped request history, operational activity and authorized reviews. Physical approvals
require explicit confirmation and current inventory retrieval; backend version checks
reject stale counts. Other request decisions do not modify stock. Errors, empty states,
pagination and pending controls are present.

Permission/account changes clear query caches and reset protected local state. Verification
polling is serialized; a late 401 from an old token cannot discard a newer session.

Verification: 35 frontend tests passed, plus an explicit 5-test chat-rendering/permission-
control run (overlapping the suite). TypeScript, production build and whitespace checks
passed. ESLint has 0 errors and 10 existing fast-refresh warnings. Tests cover route policy,
permission controls, account isolation keys, stale 401 handling, request payloads/pagination
and 403/409 failures. Existing backend authorization test evidence remains in Phase 3 below;
this frontend phase does not replace server security testing. Browser interaction testing,
full session lifecycle integration and Phase 6 end-to-end acceptance remain pending.

No environment, database, dependencies or live inventory changed in this phase. No test
emails sent. Phase 5 chatbot permission completion awaits explicit approval.

## RBAC Phase 3 handoff — 2026-10-14

Backend implemented and activated after explicit approval of Phases 1–3. Phase 4
frontend work was not started at that handoff; the approved Phase 4 work is recorded above.

### Policy and API contracts

- `backend/app/core/permissions.py` is the explicit role-to-permission and HTTP route
  registry. Unknown permissions and unmapped business routes fail closed. A test checks
  every registered business route uses the policy dependency. Public authentication
  routes and basic health probes remain separate; authenticated session endpoints are
  self-scoped. Workers are trusted server processes, not user-controlled API tools.
- Admin manages users/configuration/thresholds/diagnostics; Manager performs operational
  actions and exports; Staff reads single-store operational data and submits requests.
  All three roles retain private conversations. There are no store or shelf assignments.
- Manager product creation must omit threshold fields to use server defaults. Explicit
  threshold values, including unchanged values, require thresholds.manage permission.
- GET/POST `/api/v1/requests`: list visible requests or submit a request. Input:
  `inventory_id`, `kind` (physical_count/discrepancy/restock), `reason`; `quantity`
  is required only for physical_count. Actor/status fields are not accepted from clients.
- GET `/api/v1/requests/{id}`: owner-scoped for Staff; other users' records return 404.
- POST `/api/v1/requests/{id}/review`: authorized reviewer supplies `decision`
  (approved/rejected) and `reason`. A second review returns 409. Approved physical counts
  use the existing stock correction transaction, history/audit/outbox, and saved inventory
  timestamp. Stale counts return 409 and remain pending; request a new count or reject.
  Restock/discrepancy approval records review only and never changes inventory quantities.
- GET `/api/v1/operational-audit`: Admin/Manager operational entries; Staff sees only
  own request activity. Full administrative audit endpoints remain Admin-only.
- Login/refresh/verify include a `permissions` array. Role changes/deactivation invalidate
  issued tokens; logout invalidates ALL sessions for that account. Re-login is required.
  WebSocket delivery revalidates access and closes revoked connections.
- Camera responses retain the `source_url` key but always return null, including for
  Admin. The stored connection is unchanged and may still be replaced through an
  authorized mutation. Agent traces omit raw prompts, reasoning, outputs and errors.
- Chat tools require trusted user context and check their query permission independently
  of model output. Saved answers/previous query context are reauthorized. Phase 5 will
  complete chatbot-specific adversarial coverage and frontend handling; no vector RAG
  or document-retrieval feature was added.

### Migration, deployment and verification

`0008_rbac_requests_sessions` adds users.session_version and operational_requests.
Existing audit_logs.status already provides an outcome field. No accounts/passwords
were reset and no inventory counts changed. Live verification confirmed preservation
and denied browser access/RLS on the new table. Migration rollback intentionally
preserves submissions and session counters; it is not a destructive schema rollback.

On another installation, from `backend` with the project environment active, run
`python -m alembic upgrade head` BEFORE starting the new API (`python -m uvicorn
app.main:app --host 127.0.0.1 --port 8000`). Restart deployed API processes together so
old code cannot continue accepting revoked tokens. No new dependencies or environment
variables are needed. Existing database URL must point to a working connection.
This PC still uses the process-only transaction-pool override documented below.

Validation: 268 backend tests passed; git whitespace check passed. Tests use disposable
databases and fake mail/providers, not live security mutations. Live login, permission
responses, request/audit/chat reads and camera redaction passed; anonymous request access
returned 401. Email/event workers were left running, SMTP readiness remains true.
Redis is still disconnected. Browser acceptance and PostgreSQL concurrent approval
stress tests remain pending. No frontend edits, new users, commits or pushes in Phase 3.

## Remediation update — 2026-10-14

### Subsequent owner-requested alert delivery

Created 8 low-stock and 4 out-of-stock alerts from current inventory using the existing
deduplicating rules. Queued 24 messages for manager@intellistock.com and
usmanmumtaz005@gmail.com. The first real delivery attempt failed with
SMTPServerDisconnected; execution stopped to avoid repeated failures. Zero messages
were accepted, 23 remain pending and 1 awaits retry. Ongoing automatic notifications
remain disabled; no inventory quantities or .env settings changed. The earlier
remediation tests below did not send mail; this subsequent operation attempted delivery.

- Supabase migration `0007_backend_table_privacy` applied. Verified all 18 explicitly
  named backend tables have RLS enabled and neither anon nor authenticated has direct
  SELECT/INSERT/UPDATE/DELETE grants. Backend reads and administrator login still work.
  No unrelated public tables or global default privileges were changed. Future tables
  need explicit protection; a metadata coverage test detects missing migration coverage.
- Delayed stock events now read locked current inventory instead of trusting old event
  quantities. Email delivery checks current inventory, cancels obsolete stock alerts and
  defers unknown/offline/uncertain counts without consuming a delivery attempt.
  Both previously expected-failure regressions now pass.
- Manual correction form refreshes its concurrency snapshot after a successful save.
  Newly seeded demo camera regions use normalized coordinates; existing live regions
  remain unchanged and still require real-camera calibration.
- Chat answers query inventory, alerts and history; exact product codes take priority,
  ambiguous products trigger clarification, and shelf/date follow-ups retain context.
  Evidence shows product code, shelf, source and UTC timestamps. Yesterday means recorded
  changes during the UTC calendar day, not an invented historical inventory snapshot.
  User-facing terminology uses natural product/inventory wording.
- Default backend connection budget reduced to five per process. The configured Supabase
  session pool (5432) rejected connections due to its 15-session limit. The same database's
  transaction pool (6543) was verified and used for migration and the restarted server,
  through a process-only override; `.env` was not changed. Future normal starts require
  fixing session exhaustion or selecting the working pool in DATABASE_URL.
- Verification: 256 backend tests passed, with one additional uncertain-email regression
  passing in the four-test audit suite; 23 existing frontend tests and two new evidence
  rendering tests passed; TypeScript and production build passed. Live health, admin login and authenticated
  chat status return 200. Health remains degraded because Redis is disconnected.

Remaining: Redis runtime setup, SMTP authentication/delivery acceptance, camera weights/
footage, real-camera calibration and screenshot attachment support. Automatic email
remains disabled. No real inventory counts were changed and no mail was sent by these tests.
These results do not constitute a complete production security or browser-interaction audit.

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
