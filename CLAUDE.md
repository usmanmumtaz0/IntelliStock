# IntelliStock Agent — Project Instructions

> Read this file FIRST, every session, before touching any code.
> Then read `PROGRESS.md` to see exactly what's done and what's next.
> Full architecture reasoning lives in `docs/IntelliStock_Agent_Architecture_Review_and_Plan.md` — read only the relevant section when needed, not the whole thing, to save context.

---

## 1. What This Project Is

IntelliStock Agent — an AI-powered inventory intelligence platform (BS CS Final Year Project).

Pipeline: `Camera → CV (YOLO+ByteTrack) → ROI/Shelf Assignment → Observation → Reconciliation Engine → Trusted Inventory State → Events → Rule Engine → LangGraph Agents → FastAPI → WebSocket → Next.js Dashboard`

Core principle (never violate): **YOLO output is an Observation, not truth.** Only the Reconciliation Engine, after confidence/temporal/tracking checks, may update trusted Inventory State. Business State (alerts) only ever changes in response to Inventory State, never directly from raw detections.

## 2. Non-Negotiable Architecture Rules

1. PostgreSQL = source of truth. Redis = transient/cache/event-bus only, never permanent storage.
2. Never write raw per-frame detections to PostgreSQL — only committed state changes.
3. LLMs never do deterministic math (threshold checks, arithmetic, quantity comparisons). Rule engine does that.
4. AI agents (LangGraph) are event-triggered, never frame-triggered.
5. A failed LangGraph agent must never block core inventory monitoring or the rule engine.
6. Frontend never talks to PostgreSQL or Redis directly — only REST (`/api/v1/...`) and WebSocket.
7. Secrets live in `.env` only, never in source. `.env` is gitignored; `.env.example` is committed.
8. Use the state machine exactly as defined in the architecture doc (Section 5.3): `UNKNOWN, ADEQUATE, LOW_STOCK, OUT_OF_STOCK, DETECTION_UNCERTAIN, CAMERA_OFFLINE`. Invalid transitions must be rejected at the repository layer.
9. Alert dedup/cooldown via the `observation_window` is mandatory before any alert is created — no flicker spam.
10. No Kafka, Kubernetes, RabbitMQ, Celery, ChromaDB, or new microservices unless a concrete requirement forces it and it's discussed first.
11. If a vector DB is ever genuinely needed, prefer **pgvector** over Qdrant/Chroma (stays in Postgres).

## 3. Tech Stack (locked)

Frontend: Next.js, TypeScript, Tailwind, shadcn/ui, Recharts
Backend: Python, FastAPI, Pydantic, SQLAlchemy, Alembic
DB: PostgreSQL | Cache/Events: Redis (pub/sub)
CV: Ultralytics YOLO, OpenCV, ByteTrack
AI: LangGraph, configurable LLM provider
Auth: JWT + RBAC
Deploy: Docker Compose
Tests: Pytest (backend/CV), Playwright (frontend, where useful)

Repo layout:
```
intellistock-agent/
  backend/app/{api,services,repositories,models,schemas,events,websocket,database,core}
  frontend/
  cv/
  docs/
  docker-compose.yml
  .env.example
  CLAUDE.md
  PROGRESS.md
```

## 4. How To Work In This Repo (every session)

1. Read this file, then `PROGRESS.md`.
2. Resume from the first unchecked task in `PROGRESS.md`. Don't jump ahead or re-plan unless explicitly asked.
3. Before writing code, briefly state: which task ID, what files you'll touch, acceptance criteria.
4. Implement, then run/verify (tests, `docker compose up`, whatever the task needs).
5. **Update `PROGRESS.md` immediately after finishing a task**: check the box, add a one-line note (date optional, key decision or gotcha only), and set the "Currently On" pointer to the next task. This is what makes cross-session/cross-login continuity work — don't skip it.
6. If a change would materially alter the locked architecture (Section 2 or the full architecture doc), stop and explain: existing decision → problem → proposed change → impact — then wait for approval before proceeding. Don't silently redesign.
7. Keep commits small: `feat:`, `fix:`, `test:`, `docs:` prefixes. Branch per feature area (`feature/vision`, `feature/inventory`, `feature/backend`, `feature/dashboard`, `feature/langgraph`).
8. Never fabricate test results or claim something works without having run it.

## 5. Code Quality Bar

Production-quality, modular, type-hinted, input-validated, structured logging, no dead code, no giant files, no hardcoded config, no fake/empty implementations (label placeholders explicitly if unavoidable).

## 6. Where To Look For Detail

| Need | Go to |
|---|---|
| Full audit / risk list / decision rationale | `docs/IntelliStock_Agent_Architecture_Review_and_Plan.md` §1-9 |
| Full backlog (all tasks, all epics) | `docs/IntelliStock_Agent_Architecture_Review_and_Plan.md` §10 |
| Current status / what to do next | `PROGRESS.md` |
| DB schema details | `docs/db_schema.md` (created in Phase 6) |
| API contracts | `docs/api_reference.md` (created in Phase 6) |

Don't re-read the full architecture doc every session — it's for reference, not context you need loaded every time. Pull only the section relevant to the current task.
