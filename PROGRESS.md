# IntelliStock Agent — Progress Tracker

> Update this file the moment a task is finished. This is the single source of truth for "where did I leave off" — it's how work resumes cleanly across sessions and across logins, since it lives in the repo, not in chat memory.

**Currently On:** Video/image upload now fills the desktop workspace when camera capture is unavailable. Authenticated console browser acceptance remains blocked by the existing local API login timeout; licensed DINOv2 SKU references, RBAC Phase 7, PostgreSQL concurrency acceptance and Redis remain open.
**Last Updated:** Oct 21, 2026 | 315 backend tests, 38 frontend tests, TypeScript, targeted ESLint and production frontend build passed


### Video/image upload workspace width (Oct 21, 2026)

- [x] Made the upload panel span the full desktop grid when the current role cannot access Camera capture, removing the unused right-side column. Camera-authorized users retain the existing two-panel layout; upload behavior and responsive mobile/tablet layout are unchanged.
- Verification: frontend TypeScript, targeted route ESLint, full 38-test frontend suite and production build passed. Full backend suite passed 315 tests. No API, permission, upload-processing or shared-style changes.

### Settings page organization and preservation (Oct 21, 2026)

- [x] Audited the Settings route, authentication/profile contract, permission model, theme persistence, product and user management, notification delivery diagnostics and camera configuration before editing.
- [x] Reorganized personal settings into clear My Account, Security, Appearance and Notification Preferences panels with responsive two-column layout, concise descriptions and explicit saved-state feedback for the existing browser theme preference.
- [x] Preserved the existing Products, Users & access and Email delivery tabs, their real API-backed components and server-permission gates. Preserved the Shelves camera-configuration link and all existing role behavior.
- [x] Kept unsupported features honest: the backend exposes no self-service password/session-management or personal notification-preference APIs, so these panels explain current behavior without fake controls or invented persistence.
- Verification: 11 frontend test files / 38 tests passed; TypeScript and production build passed; ESLint has 0 errors and 10 existing Fast Refresh warnings. Added focused Settings rendering and RBAC regression coverage. No backend, API, dependency, global style or unrelated route changes.

### Frontend modernization and responsive density (Oct 21, 2026)

- [x] Audited the React/TanStack/Tailwind/Radix frontend, route structure, RBAC navigation, shared primitives, data tables, dialogs, loading/empty states and existing test/build commands.
- [x] Centralized shell sizing tokens and reduced the desktop sidebar, header, page gutters, page heroes, panel padding, toolbars, table rows and metric cards for higher information density without removing controls or routes.
- [x] Improved mobile dialog insets and scrolling, compacted the professional login layout, and tightened Dashboard, Shelves/Cameras, Video Processing, Agent Activity and Settings layouts. Shared PageHeader, Panel, table, toolbar and empty-state updates apply across Inventory, Alerts, Reports, Requests and Assistant.
- [x] Preserved API contracts, authentication, role permissions, navigation filtering, camera/AI behavior, inventory logic and real-data queries. No backend or functional behavior changes were required.
- Verification: TypeScript passed; 10 frontend test files / 36 tests passed; production build passed; ESLint has 0 errors and 10 existing Fast Refresh warnings; diff whitespace passed.
- Rendered login review passed at 1440x900, 768x1024 and emulated 390x844. True mobile layout reported innerWidth 390 and scrollWidth 390. Authenticated dashboard capture was attempted but the existing local API login timed out, so authenticated browser interaction remains unverified.


### Pretrained OCR and visual identity evidence (Oct 21, 2026)

- [x] Added lazy PP-OCRv6 packaging-text evidence and local-only DINOv2 catalog retrieval behind explicit configuration. Video tracks reuse evidence until a sharper crop appears.
- [x] Added conservative OCR/visual confidence fusion: agreement can identify a unique catalog product; conflicting or weak evidence stays ambiguous/unknown for human review. Detection evidence still cannot mutate inventory.
- [x] Added provider health, CPU defaults, pinned dependencies in the main backend requirements, safe relative reference-image resolution, focused tests and setup/evaluation documentation.
- [x] Installed the pinned identity runtime. PP-OCRv6 model files are cached under private media, OCR is locally enabled, and a CPU image smoke read `LAYS MASALA 34 GM` at 99.99% confidence. DINOv2-small is staged under ignored models and returned 1.0 for an identical synthetic reference/crop smoke test.
- [ ] Add licensed multi-view reference images for real catalog SKUs, calibrate thresholds on held-out images/video, then explicitly enable DINOv2. No product-accuracy claim until that acceptance is complete.

### Supplied model preparation (Oct 14, 2026)

- Owner subsequently requested publishing the model folder: explicitly allowlisted models/best.pt, model-manifest.draft.json and README.md for Git. Runtime caches, secrets and local activation manifests remain excluded. Earlier local-only notes describe the original preparation, not this publishing decision.

- [x] Inspected Downloads/best.pt.zip: it is already a PyTorch checkpoint ZIP, not an outer archive. Copied unchanged to ignored models/best.pt; original preserved. SHA-256: 6502323f9dc4339312bc41d1e5281cd7d51d0c84f42c6286970db8259a5d46c5.
- [x] Metadata reports detection task, 25 exact Pakistani product labels and training Ultralytics 8.4.177. Current runtime Ultralytics 8.0.207/Torch 2.2.2 loads it and passes one blank-frame prediction plus three blank-frame YOLO/ByteTrack calls on CPU. This is not accuracy or real tracked-object acceptance; no dependency upgrades performed.
- [x] Set ignored .env CV_MODEL_PATH to the local weights; retained CPU and blank CV_MODEL_MANIFEST to block activation. Created ignored models/model-manifest.draft.json with exact labels/hash and deliberately empty product codes. Verified incomplete mapping is rejected.
- [ ] Current catalog has generic demo products with different sizes/names, not exact matches for these labels. Need owner choice to create 25 matching products or provide exact mappings. No catalog, shelf, stock or camera mutations made. Need representative shelf video and labelled counts/regions before offline accuracy review and live activation. No live worker started, emails sent, commit or push.

### Approved RBAC Phase 6 (Oct 14, 2026)

- [x] `RBAC-P6-HTTP` Added isolated real-handler acceptance for all three roles: password login, exact server permissions, operational reads, restricted settings/exports, disabled-session read/write denial and forged-header/self-promotion denial. Existing suites cover request approval/replay/staleness, history isolation, migration preservation and WebSocket revocation.
- [x] `RBAC-P6-FIX` Signup approval UI now uses users.create, matching the API policy instead of users.update; added rendered-control regression test.
- [x] `RBAC-P6-VERIFY` Full backend 285 passed; frontend 36 passed; TypeScript and production build passed; lint 0 errors/10 existing warnings; whitespace passed. No new dependencies. Tests use isolated databases/local or fake providers.
- [x] `RBAC-P6-RUNTIME` Reloaded verified API parent 33932/child 28960 as hidden process 38104 using the existing port-6543 runtime override; .env unchanged. Admin login/verify succeeded. Bounded read-only inventory, alerts, requests, audit, cameras, chat status/history all 200; anonymous chat 401, chat cache-control private/no-store. Frontend root and /requests returned 200 (HTTP only, not browser interaction). Database health connected, Redis disconnected. One earlier connection disconnect and a subsequent login timeout occurred; later bounded checks passed, so reliability is not certified. Event/email workers were not restarted or configured; no test emails or stock writes issued.
- [ ] Browser interactions, PostgreSQL multi-session race tests and live manager/staff account acceptance remain unverified. Playwright/Selenium tooling and local PostgreSQL/Docker were unavailable; no packages installed or live accounts altered. Real camera acceptance still awaits trained weights. Phase 7 requires approval; no commit/push.

### Approved RBAC Phase 5 (Oct 14, 2026)

- [x] `RBAC-P5-RETRIEVAL` Read-only tools require both chatbot permission and underlying inventory/alerts/reports/product/shelf permissions before queries or product clarification. Graph independently checks previous context before provider invocation. Malformed plans fail closed with safe 403 responses.
- [x] `RBAC-P5-HISTORY` Saved turns, request-ID retries and follow-up context reauthorize under current policy; conversation-list titles are redacted when any saved turn is no longer accessible. Owner-only access and deletion retained. Post-turn account lock rechecks activation, pending signup and session version.
- [x] `RBAC-P5-CACHE` Chat HTTP success/error responses explicitly private/no-store. No shared server answer cache or graph checkpoint exists; frontend history keys are account scoped and Phase 4 authorization changes clear caches/remount state. No vector database added; existing structured database retrieval retained.
- Verification: targeted chat/RBAC tests 41 passed; full backend suite 278 passed (existing deprecation warnings remain); whitespace check passed. Includes permission reduction across saved reads/retries/follow-ups/titles, underlying resource denials, malicious model plan denial, malformed saved plans, pre-provider context denial and HTTP cache headers. Isolated SQLite and fake/local providers only; no live LLM call, production data mutation, migration, secret changes or emails. Running API not restarted in this phase; deployment/reload and live browser/concurrency acceptance remain pending. No commit/push.

### Approved RBAC Phase 4 (Oct 14, 2026)

- [x] `RBAC-P4-UI` Server permissions drive navigation, protected routes, inventory corrections, alert actions, exports, catalog thresholds, camera/shelf configuration and account/email settings. Unknown routes deny access. Role labels never grant client permissions.
- [x] `RBAC-P4-REQUESTS` Paginated Requests page submits physical counts, discrepancies and restock requests; Staff see own submissions, authorized reviewers see team requests. Review checks current inventory, requires reasons and physical-count confirmation, and explains stale/replayed conflicts. Submissions do not directly modify inventory.
- [x] `RBAC-P4-SESSION` Session verification refreshes permissions every 30 seconds without overlapping polls; authorization changes clear query caches and remount protected content. Stale unauthorized responses cannot clear a newer session.
- Verification: 35 frontend tests passed; explicit chat-rendering/control test run 5 passed (overlaps main suite). TypeScript and production build passed; ESLint 0 errors/10 existing refresh warnings; whitespace check passed. No new dependencies, secrets, migrations, live inventory mutations or test emails. Browser interaction acceptance remains pending. No commit/push. Phase 5 not started.

### Approved RBAC Phase 3 (Oct 14, 2026)

- [x] `RBAC-P3-POLICY` Central explicit role/route permission map; deny unknown routes/permissions. Every registered business route covered by policy test. Managers cannot configure cameras/shelves/thresholds, Staff cannot export, diagnostics restricted to Admin. Product creation by Managers uses existing default thresholds; explicitly supplied threshold fields require Admin permission. Removed legacy broad role helper/map.
- [x] `RBAC-P3-REQUESTS` Real count/discrepancy/restock submissions with server-assigned actor; Staff reads only own submissions. Admin/Manager review, terminal-state replay prevention, atomic existing correction workflow with stale-inventory rejection, no inventory mutation for restock/discrepancy approval. Operational audit list filters ordinary users to own request activity. UI pending Phase 4.
- [x] `RBAC-P3-SESSIONS` Session-version claim/counter, role/deactivation revocation, logout invalidates all account sessions; login/refresh/verify return server permissions. Legacy tokens accepted only while account version remains zero. WebSocket broadcasts revalidate tokens before sending; periodic checks retained. Single-store shared read scope; no invented assignments.
- [x] `RBAC-P3-PRIVACY` Camera connection URLs never returned, detailed agent traces restricted and raw prompt/reasoning/error/output payloads omitted, validation responses strip rejected input. Chat graph/tools require trusted user and query permission; saved turns recheck plan authorization. Denied permissions produce safe actor/permission logs. Alert actions/report exports produce audit records; diagnostic observation submission records actor.
- [x] `RBAC-P3-MIGRATION` Additive 0008 applied to Supabase through verified transaction pool. Verified accounts/password hashes/roles/activation and inventory counts unchanged. New operational_requests table has RLS enabled, anon/authenticated table privileges denied. Existing audit status field reused, no audit-outcome migration needed. No new dependencies or .env changes this phase.
- [x] `RBAC-P3-VERIFY` Full backend suite 268 passed (existing dependency deprecation warnings remain); whitespace check passed. Tests cover exact route policy coverage, permitted/forbidden actions, secret redaction, submission validation/ownership/approval/replay/stale versions, revocation/fresh login, tool denial, revoked WebSocket delivery and migration preservation. Live API login/verify/requests/operational-audit/chat-status/cameras returned 200; anonymous requests 401; SMTP ready true. Health database connected, Redis disconnected. API restarted (33932); email/event workers left running. PostgreSQL concurrency stress and browser acceptance remain Phase 6 work. No frontend changes, commits or pushes in this phase.

### Chat quality and approved audit fixes (Oct 14, 2026)

- [x] `EMAIL-AUTO` Owner approved continuous delivery. Set ignored .env NOTIFICATIONS_ENABLED=true; launched hidden event worker (31316/39904) and notification worker (34168/42092) with working transaction-pool connection override. Verified processes alive, rules backlog drained to zero, and automatic escalation mail acceptance increased from 24 to 28 with 20 pending at check time. Existing deduplication/retry safeguards preserved; no inventory changes. Redis remains disconnected. Workers run only while this PC/processes remain running; no boot-time service or restart supervisor installed. Future starts still need working database pool configuration. API restarted to reload enabled flag.
- [x] `ALERT-RECIPIENT-CONFIRMED` Owner explicitly approved umerusman563@gmail.com. Queued and sent 12 current inventory alerts; SMTP accepted all 12, no failures. Previously accepted manager messages were not resent. Inbox delivery remains unverified; this was a one-time run, not activation of a persistent worker.
- [x] `ALERT-RETRY` Updated .env SMTP credentials successfully used for owner-requested retry: 12 messages accepted by SMTP for the previously approved manager recipient; 12 messages for the removed recipient cancelled by allowlist checks. Inbox delivery unverified. New configured recipient umerusman563@gmail.com requires explicit owner confirmation before queueing; safety review blocked that additional egress. No persistent notification worker enabled by this one-time run.
- [x] `ALERT-SEND` (Oct 14) Owner-requested one-time run evaluated current inventory through existing deduplicating rules: created 8 low-stock and 4 out-of-stock alerts; queued 24 messages for the two configured recipients. Stopped on first SMTPServerDisconnected: zero accepted, 23 pending, 1 retry. Inventory counts and .env unchanged; ongoing notifications remain disabled. SMTP configuration/authorization must be corrected before retrying.
- [x] `CHAT-QUALITY` Exact product-code precedence, ambiguous-product choices, shelf/date follow-ups, UTC calendar history, inventory/alert/history source timestamps and backward-compatible evidence cards. User-facing labels use product/inventory terminology; internal contracts remain unchanged.
- [x] `AUDIT-CONSISTENCY` Evaluate delayed events against locked current inventory; recheck inventory before email, cancel obsolete messages and defer uncertain observations. Refresh manual-correction form snapshot after save. New demo fixtures use normalized camera regions (existing live regions not rewritten).
- [x] `DB-PRIVACY` Migration 0007 explicitly covers all backend tables and checks ownership. Live verification: 18/18 RLS enabled, zero anon/authenticated table grants, backend reads and admin login succeed. No unrelated tables changed. Rollback intentionally does not reopen access.
- [x] Reduced default per-process connection budget from 10+20 to 3+2. Session pool port 5432 was exhausted even after local server shutdown; migration and restarted backend use the same database's working transaction pool port 6543. Runtime override only: .env unchanged. Normal future launches still use configured port 5432 unless the operator changes DATABASE_URL or clears excess sessions.
- Verification: full backend suite 256 passed plus new uncertain-email regression (4 audit tests passed); frontend existing 23 tests plus 2 evidence-rendering tests passed, TypeScript passed. Live /health 200 (database connected, Redis disconnected), admin login and authenticated chat status 200. No real email sent or enabled; no inventory quantities changed. Changes not committed or pushed.

### Frontend branding (Oct 14, 2026)

- [x] `UI-POLISH` Unified page headers/cards/forms/filter toolbars and table styling, roomy dashboard/activity metrics, wider camera cards, login card, labelled scrollable mobile navigation, skip link/focus states/reduced-motion CSS and correctly labelled committed-count tooltip. Settings split into accessible Account/Products/Users/Email tabs preserving staff product reads and admin-only sections. Shared styling includes Assistant. 23 frontend tests, TypeScript, production build and whitespace checks passed; lint 0 errors/10 pre-existing warnings. No backend behavior changes or dependencies. Automated browser tooling unavailable; desktop/mobile visual and interaction acceptance remains pending.

- [x] `BRAND-ICON` Added shared IntelliStock scan-eye SVG for browser-tab icon, login and sidebar; removed @Lovable social attribution. Existing development integration retained. TypeScript, targeted ESLint, 19 frontend tests and whitespace checks passed; browser visual acceptance pending. Old favicon asset is no longer referenced by page metadata.

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
