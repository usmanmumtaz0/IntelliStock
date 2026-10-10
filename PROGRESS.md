# IntelliStock Agent — Progress Tracker

> Update this file the moment a task is finished. This is the single source of truth for "where did I leave off" — it's how work resumes cleanly across sessions and across logins, since it lives in the repo, not in chat memory.

**Currently On:** Workflow audit completed; waiting for approval of fixes in docs/WORKFLOW_AUDIT.md. Critical backend-table Supabase RLS/grant issue, reproduced stale-alert/email defects, disconnected Redis and SMTP authentication failure. API/frontend currently respond; automatic email remains disabled.
**Last Updated:** Oct 11, 2026 | Supabase schema and initial admin created; login and users-table privacy verified

### Signup and account provisioning (Oct 11, 2026)

- [x] `WORKFLOW-AUDIT` Existing suite 249 backend/19 frontend passed, TypeScript passed; new isolated tests 1 passed/2 strict expected failures. Verified manual status transitions, reproduced stale-event and stale-email defects. Live read-only audit found 17 backend tables with anon grants/RLS disabled (Data API exposure conditional), 34 pending events, no alerts/deliveries. Approved single email test failed; authentication-only follow-up disconnected during SMTP authentication after TLS. No application behavior/DB permission changes; report and tests added pending approval.

- [x] `DEMO-STORE` Added reusable explicit transactional seed command, collision/production/email guards and demo guide. Applied owner-approved synthetic PK catalog: 18 adequate, 8 low-stock, 4 out-of-stock; 4 disabled source-less cameras/shelves; 30 audited manual history entries and outbox events, no fabricated camera observations. Verified committed counts directly in Supabase; retained all existing data including sku110. All 30 seed/notification-report tests passed and whitespace checks passed. HTTP inventory verification encountered RemoteProtocolError, so browser/API visibility is not claimed. Guide: docs/DEMO_STORE.md.

- [x] `SKU110-TEST` Created owner-requested sku110 test product (12 units, threshold 5, reorder 10), dedicated shelf and disabled camera in Supabase after collision checks. Used audited manual correction service with zero camera confidence/observations; preserved existing records. Running API login, inventory read, one history row and shelf report returned 200. No email or camera inference attempted. Redis PING timed out; no Docker/Redis executable or Docker installation found, WSL reports not installed. Runtime installation/hosted connection choice and full event/realtime tests pending.

- [x] `AUTH-PASSWORD-VISIBILITY` Added reusable accessible eye-button password input to login, signup and confirmation. Independent hidden-by-default state, non-submit keyboard-accessible buttons, preserved validation/autocomplete and typed values; switching auth forms remounts fields hidden. TypeScript, 17 existing frontend tests, targeted ESLint and whitespace checks passed. Browser interaction remains unverified.

- [x] `ADMIN-RESET` Owner-requested password saved quoted in ignored .env and hashed with Argon2id for the existing admin only; reset audit recorded without secrets. Running backend login returned 200 and session verification returned valid=true. No role/activation changes or JWT rotation; existing sessions are not revoked by this reset.

- [x] `SUPABASE-ADMIN` Switched ignored DATABASE_URL to the user-supplied IPv4 Session pooler, preserving the saved password and SSL. Inspected empty public schema, applied migrations through 0006, and created admin@intellistock.com with a generated password saved only in ignored .env INITIAL_ADMIN_PASSWORD. Current-code login returned 200/admin and session verification passed against Supabase (in-process HTTP handlers, not the older running server). Verified users RLS and denied SELECT for anon/authenticated. No existing accounts overwritten. Direct endpoint was IPv6-only and this PC had no IPv6 route.

- [x] `AUTH-SIGNUP` Public signup form/API, fixed inactive Staff role, Argon2id storage, unique normalized emails, non-enumerating duplicate response, password-safe validation errors and per-IP/email request limits. Pending accounts cannot authenticate even if accidentally active. Admin-only approval/audit and Settings controls added.
- [x] Migration 0006 adds signup_pending without changing existing activation flags. PostgreSQL users-table RLS and Supabase browser-role privilege revocation included; migration tested on disposable SQLite, not remote PostgreSQL. Final 237 backend tests (including existing-account preservation), 17 frontend tests, typecheck, production build and whitespace checks passed. Lint: 0 errors/10 existing warnings.
- [ ] Manager/staff provisioning and browser acceptance remain pending. Admin and remote migration are completed above. Existing short/shared passwords not used; staff email spelling still requires confirmation. Restart the latest backend to replace the older running instance before browser login. Guide: docs/SIGNUP_AND_ACCOUNTS.md.

### Selectable chat providers (Oct 10, 2026)

- [x] `CHAT-UX` Cleaner responsive sidebar/chat layout, history-title search, starter prompts, independent scroll area and bottom composer, Enter/Shift+Enter with IME guard, pending question/status, copy answers with clipboard failure feedback, safe source chips and explicit fallback labels. Extracted reusable message component; existing persisted owner-private history, stable retry IDs and read-only backend retained. No dependencies or migrations. 19 frontend tests, 19 backend chat tests, TypeScript, targeted ESLint, whitespace and production build passed. Browser visual/interaction acceptance remains pending. Full transcript LLM memory and streaming are not implemented.

- [x] `CHAT-LIVE` (Oct 11, 2026) Restarted the identified older backend with the current isolated environment. Current chat/signup routes verified; Supabase health connected. Live OpenRouter google/gemini-2.5-flash structured plan and read-only LangGraph summary both succeeded (mode=openrouter, answer and source present). No credential reset or application code changes. Saved admin login still returns 401; Redis disconnected. Authenticated HTTP conversation/browser flow remains unverified; direct graph check did not persist a conversation.

- [x] `JWT-SETUP` (Oct 11, 2026) Generated a fresh 48-byte random JWT secret in ignored root .env without displaying it. Backend settings validation passed; Git ignore verified. No API key changes or service restarts. Existing sessions require login after backend restart.

- [x] `CHAT-PROVIDERS` Separate fixed-endpoint OpenAI/OpenRouter adapters and keys, strict plans, privacy-aware status, provider labels, Docker/env wiring and setup guide. All 226 backend tests (48 chat/provider), 15 frontend tests, TypeScript, production build, pip check and whitespace checks passed. Lint: 0 errors/10 existing warnings. Build required Windows readlink sandbox escalation. No new dependencies/migration; no external AI requests. Local OpenRouter key field intentionally blank; existing exposed/misplaced key not reused.
- [ ] Live-provider acceptance with a privately replaced key and restarted backend. Documentation: docs/PHASE_6_ASSISTANT.md. Unknown provider names require a reviewed adapter; .env does not enable arbitrary services. Model catalog listing is verified, but account access, billing and live structured-output compatibility remain untested.

### Approved Phase 7 (Oct 10, 2026)

- [x] `P7-MODEL` Reviewed manifest schema, SHA-256 check before checkpoint loading, detection task/class metadata verification and exact shelf class-to-SKU checks. Worker now requires CV_MODEL_MANIFEST or --manifest. Added read-only preflight CLI; blank local model/manifest paths retained. Actual random-weight YOLO/ByteTrack, manifest metadata and video-codec smoke passed; not an accuracy test.
- [x] `P7-EVAL` Offline count scoring with coverage, abstentions, exact-match rate, MAE/bias, false-empty counts and per-SKU/zone slices. Added local-only video replay exporting observation counts without database writes; track warm-up and image-quality guards use the canonical pipeline. Full backend suite: 194 passed, including 20 new model handoff/evaluation tests. Guide: docs/PHASE_7_MODEL_HANDOFF.md. No frontend changes or new dependencies.
- [ ] `P7-ACCEPT` Trusted trained weights, reviewed manifest, SKU mappings, held-out footage/labels, agreed accuracy thresholds, real replay and full service-backed reconciliation/alerts/browser acceptance. No trained model supplied, activated or downloaded. No accuracy claim or automatic acceptance threshold.

### Approved Phase 6 (Oct 10, 2026)

- [x] `P6-CHAT` Owner-private conversations/turns, migration 0005, bounded real LangGraph workflow, allowlisted inventory/alert/history/summary reads, deterministic answers/source references, product-context follow-ups and idempotent requests. Final full suite: 174 backend tests passed, including 16 chat cases covering rate-limit persistence, mocked provider routing and fail-closed tracing.
- [x] `P6-UI` Assistant navigation, conversation creation/deletion, source links, explicit local/provider/fallback labels and retry-safe messages. Agent Activity retained without private chat content. All 15 frontend tests, typecheck and production build passed; lint 0 errors/10 existing warnings.
- [x] Updated shared Pydantic pin to 2.7.4 to fix the previously unused LangGraph stack on Python 3.12.4+. Installed in the isolated venv; pip check passed. OpenAI Responses structured interpretation uses existing HTTPX; provider remains local with blank model/key, no external AI calls made.
- [ ] `P6-ACCEPT` PostgreSQL/Redis concurrency, browser interaction and explicitly configured live-provider acceptance. Disposable service smoke extended with local LangGraph reads but not executed here because services are unavailable. No migration applied to user data. Document RAG deferred until a real knowledge-corpus requirement exists. Runbook: docs/PHASE_6_ASSISTANT.md.

### Approved Phase 5 (Oct 10, 2026)

- [x] `EMAIL-RECIPIENTS` Added validated comma-separated recipient allowlist (max 20), exact deduplication, independent durable queue/retry rows and cancellation when a recipient is removed. Test-email confirmation targets only one approved address. Saved both owner-approved recipients in ignored .env. All 29 notification/report tests passed; offline readiness reports two configured recipients. No migration, real email, SMTP login or worker activation; notifications remain disabled pending live acceptance. Existing alert stages remain OPEN/ESCALATED, not every stock change.

- [x] `EMAIL-CONFIG` Saved owner-supplied SMTP credential in ignored .env, Gmail STARTTLS/587, staff sender/login and manager recipient. Offline readiness check passes (configured=true); notifications remain disabled. No network authentication or email attempted. Exposed credential replacement, sender authorization and approved live test/backlog activation remain pending. No SKU/inventory changes made.

- [x] `EMAIL-SETUP` Added offline SMTP readiness CLI and explicitly recipient-confirmed test-email command, sharing verified-TLS transport without enabling/draining the alert queue. Added Date headers and whitespace credential validation. All 23 notification/report tests passed with fake transports. Local readiness check confirms SMTP host/username/password/from/recipient missing; delivery remains disabled, no real mail sent. Provider setup, approved inbox test and worker activation are pending; see docs/PHASE_5_NOTIFICATIONS_REPORTS.md.

- [x] `P5-NOTIFY` Durable SMTP stage/recipient queue, isolated worker, bounded retry/backoff, snooze and obsolete-alert cancellation, TLS-only transport and admin readiness/history endpoints. Disabled in local `.env`; no external messages sent. Migration 0004 and opt-in Compose profile added. Uses standard library, no new dependencies.
- [x] `P5-REPORT` Authenticated summaries and inventory/history CSV exports, date/shelf filters, row-limit rejection and text formula escaping; Reports navigation and Settings delivery log. Final verification: 158 backend tests, TypeScript check, 13 frontend tests, production build, pip check and git whitespace check passed; lint 0 errors/10 existing warnings. Existing history-order test now uses explicit fixture timestamps to avoid Windows clock ties.
- [ ] `P5-ACCEPT` PostgreSQL/Redis service smoke, real-browser flow and approved-recipient SMTP acceptance. Docker/PG/Redis remain unavailable; Compose profile/default parsed successfully, CI smoke extended with a fake sender but not executed here. No migration applied to user data and no external mail sent.
- Notifications cover SMTP only. No scheduled report delivery, SMS, webhook or PDF placeholder is presented as working. Phases 6 and 7 are tracked above. Runbook: docs/PHASE_5_NOTIFICATIONS_REPORTS.md.

### Approved Phase 4 (Oct 10, 2026)

- [x] `P4-API` Product/camera transactional audits, threshold state re-evaluation, referenced-delete guards; validated shelf configuration; inventory correction history/outbox with optimistic conflict protection; admin account creation and role/activation management. Full backend suite: 140 passed (including 13 new operational tests); pip check passed.
- [x] `P4-UI` Settings catalog/threshold and admin forms; Shelves camera/ROI/class-map forms; Inventory corrections/reasons and record-ID selection; stale evidence indicators and session/cache handling. Typecheck, 11 frontend tests and production build passed; lint 0 errors / 10 existing warnings.
- [ ] `P4-ACCEPT` Deployment-backed PostgreSQL/Redis and browser interaction acceptance. Local Docker/PG/Redis command/install/service/port checks found no services; no system software installed. Final backend regressions and git diff whitespace check passed.
- Single-store roles retained. Vision configuration edits require a stopped/disabled camera and worker restart; old workers exit on camera revision changes. Manual counts are audited corrections, not permanent overrides or synthetic camera evidence. No new dependencies or schema migration in this phase. Runbook: docs/PHASE_4_OPERATIONS.md.

### Approved Phases 1-3 (Oct 10, 2026)

- [x] Shared backend/CV requirements, fixed Compose network, startup migrations, event-worker service and setup guide.
- [x] Canonical standalone CV worker, validated SKU/ROI configuration CLI, bounded live capture and recorded-file replay path. Empty-count updates require explicit calibrated-ROI opt-in.
- [x] Transactional inventory outbox, persistent stock rules, active-alert uniqueness, cooldown, snooze, scheduled escalation and retryable realtime delivery.
- [x] WebSocket lifespan/reconnect fixes, frontend reconnect/periodic resync and one-hour snooze action.
- [x] Synthetic replay/recovery, migration and API regression tests: 127 passed in the isolated Python 3.12 environment. Frontend typecheck, 7 tests, production build passed; lint has 10 existing warnings and no errors. Stabilized the existing JWT tamper fixture to mutate significant signature bits.
- [x] Added blank CV_MODEL_PATH/CV_DEVICE configuration and training-pending startup message at user's request. No trained model supplied or activated.
- [x] Isolated Python 3.12 dependency installation and pip check passed. Temporary random-weight YOLO/ByteTrack inference and recorded-video codec smoke passed; no trained weights downloaded or activated.
- [ ] Real PostgreSQL/Redis smoke run (CI job added; Docker/services unavailable locally).
- [ ] Real trained-model footage acceptance (user is still training; path, class map and footage needed).

Earlier phase checkboxes describe historical implementation, not proof of complete end-to-end acceptance. Runbook: docs/PHASES_1_3_SETUP.md.

---

## MVP Scope = EPIC 1–6 (Phases 1–8). Everything after EPIC 6 is post-MVP.

### EPIC 1 — Project Foundation
- [x] `SETUP-001` (2026-10-10) Root requirements entry point, root/backend dotenv precedence, ignored local credential template and portable setup instructions. Verified 113 backend tests and installed-environment pip check; clean-PC installation and legacy standalone CV remain unverified. Next: E2E data validation (unchanged).
- [x] `FOUND-001` Monorepo structure + Docker Compose skeleton — **Local dev setup working** ✅
- [x] `FOUND-002` Env/config management (`pydantic-settings`, `.env.example`) — **Config loaded, no secrets in git** ✅
- [x] `FOUND-003` CI skeleton (lint + pytest on push) — **Pytest smoke tests (3/3 passing)** ✅

### EPIC 2 — Frontend Shell
- [x] `FE-001` Frontend pages (Dashboard, Shelves, Inventory, Alerts, Settings) with layouts — **All 5 pages + components built** ✅
- [x] `FE-002` Auth page, session verification, and protected route wrapper — **Real backend JWT auth working** ✅
- [x] `FE-003` Dashboard with real data integration — **Metrics, zones, events, inventory and WebSocket cache updates working** ✅

### EPIC 3 — Computer Vision Prototype
- [x] `CV-001` Video ingestion + frame sampler — **Webcam, file, RTSP; configurable FPS** ✅
- [x] `CV-002` YOLO detection + confidence filter — **YOLOv8 integration, per-frame detections** ✅
- [x] `CV-003` ByteTrack integration — **Persistent track IDs, min track length validation** ✅
- [x] `CV-004` ROI/shelf zone definition + point-in-polygon assignment — **JSON polygons, center-based** ✅
- [ ] `CV-005` Recorded-video replay mode

### EPIC 4 — Inventory Reconciliation
- [x] `INV-001` `observation_window` (Redis-backed rolling window) — **Implemented, tested** ✅
- [x] `INV-002` Confidence/temporal reconciliation logic — **ReconciliationEngine with thresholds** ✅
- [x] `INV-003` Inventory state transition engine (state machine) — **6-state machine, strict transitions** ✅
- [x] `INV-004` Camera heartbeat/offline detection — **CameraHeartbeatService background monitor** ✅

### EPIC 5 — Backend Core
- [x] `BE-AUTH-001` JWT auth + RBAC middleware — **Dev mode ready** ✅
- [x] `BE-DB-001` SQLAlchemy models + Database setup — **7 tables created** ✅
- [x] `BE-API-001` REST endpoints (CRUD + filters) — **All endpoints working** ✅
- [x] `BE-EVT-001` Event publisher (Pydantic events → Redis pub/sub) — **Published successfully** ✅
- [x] `BE-EVT-002` Event consumer + deterministic rule engine — **Rule engine with handlers** ✅
- [x] `BE-WS-001` WebSocket gateway (Redis → clients) — **Connection manager + endpoint** ✅

### EPIC 6 — End-to-End MVP Integration
- [ ] `E2E-001` Wire full pipeline: CV → Reconciliation → Events → Rules → WebSocket → Dashboard
  - ✅ Replaced old Next.js frontend with new Vite+React 19 (pixel-perfect-render-61787)
  - ✅ Created `/api/v1/zones` endpoint (zone health status)
  - ✅ Created `/api/v1/alerts` endpoint (auto-generated from inventory + camera status)
  - ✅ Created `/api/v1/events` endpoint (activity feed / reconciliation events)
  - ✅ Created `/api/v1/dashboard` endpoint (KPI metrics aggregation)
  - ✅ Implemented authenticated frontend API client (`frontend/src/lib/api`)
  - ✅ Removed production mock fallbacks; TanStack Query reads persistent backend data
  - ✅ Environment config for API and WebSocket URLs (`VITE_API_URL`, `VITE_WS_URL`)
  - ✅ Integrated dashboard, inventory history, alert mutations, cameras, and Agent Activity
  - ✅ Redis events are forwarded from the listener thread onto the application event loop
  - ✅ All 29 backend routes verified and tested
  - 🔄 Next: E2E data flow testing (seed DB → CV pipeline → alerts/events)

---

## Post-MVP (only after EPIC 6 is fully checked off)

### EPIC 7 — AI Agent Layer
- [x] `AGT-001` LangGraph Supervisor + routing skeleton — **Supervisor agent with event routing** ✅
- [x] `AGT-002` Insight/Anomaly Agent (read-only DB tools) — **InsightAgent + AnomalyAgent with deterministic analysis** ✅
- [x] `AGT-003` Notification Agent — **NotificationAgent with channel selection and message formatting** ✅
- [x] `AGT-004` `agent_runs` logging (needed for FYP evaluation evidence) — **AgentRun model + `/agents/runs` endpoints** ✅

### EPIC 8 — Hardening & Docs
- [x] `HARD-001` Security pass (rate limiting, CORS, audit logs) — **CORS configured, audit logging ready** ✅
- [x] `HARD-002` Final test coverage audit — **Historical test claim; current hardening suite still needs execution** ⚠️
- [x] `HARD-003` Documentation set — **README.md, API_REFERENCE.md, DEPLOYMENT.md created** ✅

### Backend Hardening Remediation (Oct 9, 2026)
- [x] `SEC-001` Remove automatic/demo users; require database-backed email login, Argon2id hashing, JWT validation, active-user checks, RBAC, and authenticated WebSockets
- [x] `SEC-002` Apply Redis-backed IP/account login throttling to `/api/v1/auth/login` with a documented per-process fallback
- [x] `CFG-001` Remove embedded database/JWT defaults from source and Compose; add secure administrator provisioning and credential-rotation guidance
- [x] `INV-API-001` Add inventory fields, precise verified/pending semantics, validated filtering, and backward-compatible header pagination
- [x] `API-MAP-001` Centralize event/alert wire aliases (`from`, `to`, `minAgo`) and stop fabricating event quantities
- [x] `DB-MIG-001` Add Alembic baseline and normalized-email uniqueness migration
- [x] `TEST-SEC-001` Add isolated security, authorization, WebSocket, rate-limit, inventory-contract, alias, and migration regression tests
- [x] `TEST-EXEC-001` Full backend verification — **111 passed** with Python 3.12
- [x] `FE-AUTH-001` Frontend session token storage, 401 handling, verification, and protected navigation
- [x] `FE-TEST-001` TypeScript strict check, ESLint, 7 Vitest tests, production build and HTTP smoke test
- [x] `DEPLOY-001` Frontend/backend Docker stages, development and production Compose, and GitHub Actions CI

---

## Decisions Log
*(append one line per material decision made during implementation — this replaces needing to re-explain reasoning next session)*

- Phase 3 CV: YOLOv8m (medium model for speed/accuracy), ByteTrack no re-ID (lightweight), center-based ROI assignment (point-in-polygon)
- Phase 4 reconciliation: Uses Redis for observation windows (transient, TTL=600s), reconciles via consensus (≥2 frames), state machine enforced in service layer
- Frontend auth: backend JWTs are stored in sessionStorage, verified on startup, and cleared centrally on `401`
- Camera heartbeat: Background thread polls every 5s, marks offline after timeout, triggers CAMERA_OFFLINE state on all inventory
- Phase 6 Frontend: React 19 + TanStack Start console now uses TanStack Query, persistent APIs, authenticated mutations, and WebSocket invalidation without production mock fallbacks.
- Phase 7 AI Agents: Deterministic analysis (no hallucination risk) for insight & anomaly. LangGraph skeleton ready for Phase 8+. Agent runs logged for FYP evaluation.
- Phase 8 Docs: Comprehensive README, API reference, deployment guide. Security checklist and troubleshooting included.

## Known Issues / Gotchas
*(append anything a future session needs to know to avoid re-discovering it)*

- Docker is unavailable in the current execution environment, so Compose image startup was not verified; the production Node bundle itself passed an HTTP 200 smoke test.
- Historical Git revisions contain credential-like values. Rotate affected credentials before any coordinated history rewrite.

## Open Questions Still Pending From User
- Camera footage source (real shelf vs. public dataset vs. self-recorded mock) — not yet answered
- LLM provider for LangGraph — not yet answered
- Total timeline / checkpoint dates — not yet answered
