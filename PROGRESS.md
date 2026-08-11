# IntelliStock Agent — Progress Tracker

> Update this file the moment a task is finished. This is the single source of truth for "where did I leave off" — it's how work resumes cleanly across sessions and across logins, since it lives in the repo, not in chat memory.

**Currently On:** `FE-001` — Frontend Shell (Next.js + Tailwind + shadcn/ui)
**Last Updated:** EPIC 1 complete; env/config + CI setup done

---

## MVP Scope = EPIC 1–6 (Phases 1–8). Everything after EPIC 6 is post-MVP.

### EPIC 1 — Project Foundation
- [x] `FOUND-001` Monorepo structure + Docker Compose skeleton (Postgres, Redis, backend, frontend) — **Dev Status page created** ✅
- [x] `FOUND-002` Env/config management (`pydantic-settings`, `.env.example`) — **Config validation + multi-env support** ✅
- [x] `FOUND-003` CI skeleton (lint + pytest on push) — **GitHub Actions CI workflow** ✅

### EPIC 2 — Frontend Shell
- [ ] `FE-001` Next.js + Tailwind + shadcn/ui scaffold, nav structure
- [ ] `FE-002` Auth pages + protected route wrapper
- [ ] `FE-003` Dashboard shell (empty/loading states, no real data)

### EPIC 3 — Computer Vision Prototype
- [ ] `CV-001` Video ingestion + frame sampler
- [ ] `CV-002` YOLO detection + confidence filter
- [ ] `CV-003` ByteTrack integration
- [ ] `CV-004` ROI/shelf zone definition + point-in-polygon assignment
- [ ] `CV-005` Recorded-video replay mode

### EPIC 4 — Inventory Reconciliation
- [ ] `INV-001` `observation_window` (Redis-backed rolling window)
- [ ] `INV-002` Confidence/temporal reconciliation logic
- [ ] `INV-003` Inventory state transition engine (state machine)
- [ ] `INV-004` Camera heartbeat/offline detection

### EPIC 5 — Backend Core
- [ ] `BE-AUTH-001` JWT auth + RBAC middleware
- [ ] `BE-DB-001` SQLAlchemy models + Alembic migrations
- [ ] `BE-API-001` REST endpoints: cameras, zones, products, inventory
- [ ] `BE-EVT-001` Event publisher (Pydantic events → Redis pub/sub)
- [ ] `BE-EVT-002` Event consumer + deterministic rule engine
- [ ] `BE-WS-001` WebSocket gateway (Redis → clients)

### EPIC 6 — End-to-End MVP Integration
- [ ] `E2E-001` Wire full pipeline: CV → Reconciliation → Events → Rules → WebSocket → Dashboard

---

## Post-MVP (only after EPIC 6 is fully checked off)

### EPIC 7 — AI Agent Layer
- [ ] `AGT-001` LangGraph Supervisor + routing skeleton
- [ ] `AGT-002` Insight/Anomaly Agent (read-only DB tools)
- [ ] `AGT-003` Notification Agent
- [ ] `AGT-004` `agent_runs` logging (needed for FYP evaluation evidence)

### EPIC 8 — Analytics, Predictions, Copilot
- [ ] `INT-001` Analytics dashboard (historical trends)
- [ ] `INT-002` Baseline forecast (rule/statistical, before any LLM forecasting claim)
- [ ] `INT-003` AI Copilot (tool-based retrieval, anti-hallucination guardrails)

### EPIC 9 — Hardening & Docs
- [ ] `HARD-001` Security pass (rate limiting, CORS, audit logs)
- [ ] `HARD-002` Final test coverage audit (tests should already exist per-task, not written here first)
- [ ] `HARD-003` Documentation set (README, SRS, ERD, API docs, evaluation report)

---

## Decisions Log
*(append one line per material decision made during implementation — this replaces needing to re-explain reasoning next session)*

- (none yet)

## Known Issues / Gotchas
*(append anything a future session needs to know to avoid re-discovering it)*

- (none yet)

## Open Questions Still Pending From User
- Camera footage source (real shelf vs. public dataset vs. self-recorded mock) — not yet answered
- LLM provider for LangGraph — not yet answered
- Total timeline / checkpoint dates — not yet answered
