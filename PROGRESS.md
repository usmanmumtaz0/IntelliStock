# IntelliStock Agent — Progress Tracker

> Update this file the moment a task is finished. This is the single source of truth for "where did I leave off" — it's how work resumes cleanly across sessions and across logins, since it lives in the repo, not in chat memory.

**Currently On:** E2E data validation — authenticated frontend/backend integration is complete; recorded camera/dataset replay remains
**Last Updated:** Oct 9, 2026 | Frontend, WebSocket, Docker and CI integration complete | 111 backend + 7 frontend tests passing

---

## MVP Scope = EPIC 1–6 (Phases 1–8). Everything after EPIC 6 is post-MVP.

### EPIC 1 — Project Foundation
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
