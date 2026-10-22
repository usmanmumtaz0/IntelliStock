# IntelliStock Agent

IntelliStock is an authenticated inventory intelligence platform that combines camera observations, probabilistic reconciliation, persistent alerts, agent execution telemetry, and a real-time React console.

## What is integrated

- FastAPI API with JWT authentication and role-protected mutations
- React 19 + TanStack Start console for dashboard, inventory history, alerts, cameras, settings, and agent activity
- PostgreSQL inventory state and Redis event delivery
- Authenticated WebSocket cache refresh for inventory, dashboards, alerts, cameras, and events
- YOLO/ByteTrack computer-vision pipeline and reconciliation history
- Backend and frontend tests, Docker images, Compose, and GitHub Actions CI

## Local development

For the current vision worker, durable event worker, migrations and acceptance
limits, follow [Phases 1-3 setup](docs/PHASES_1_3_SETUP.md).

Prerequisites: Python 3.11 or 3.12, Node.js 24, PostgreSQL, and Redis.

1. Copy `.env.example` to `.env` and replace every credential placeholder.
2. Install and run the backend:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
cd backend
alembic upgrade head
python -m scripts.create_admin --email admin@example.com --username admin
uvicorn app.main:app --reload
```

3. In another terminal, install and run the frontend:

```powershell
cd frontend
Copy-Item .env.example .env
npm ci
npm run dev
```

The console runs at `http://localhost:3000`, the API at `http://localhost:8000`, and API documentation at `http://localhost:8000/docs`.

## Docker Compose

After configuring the root `.env` file:

```powershell
docker compose up --build
```

This starts PostgreSQL, Redis, FastAPI, and the frontend development server. Production frontend builds use the final stage in `frontend/Dockerfile`.

For production-style containers without source mounts or reloaders:

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

## Configuration

Backend settings are listed in `.env.example`.

The backend reads the root `.env` automatically, regardless of working directory.
An existing `backend/.env` overrides the root file; process environment variables
override both. Keep real credentials only in ignored local files. On another PC,
copy `.env.example` to `.env` and supply that machine's database credentials and
a newly generated JWT secret. Do not overwrite an existing configured `.env`.

Generate a JWT secret locally with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

LangChain, LangGraph and the OpenAI client are already included in the Python
requirements. Installation does **not** enable external AI or notification delivery.
The Assistant defaults to local read-only queries; OpenAI interpretation and SMTP
each require explicit configuration. RAG and SMS remain unimplemented. Administrator passwords
should be entered interactively using `scripts.create_admin`.

Python requirements do not install PostgreSQL, Redis, Node.js, frontend npm
packages, camera drivers, CUDA or trained model weights. Install/start the services
and run the migrations above. Run `npm ci` separately for the frontend. The
`cv/requirements.txt` now includes the shared backend dependency set. Run the
canonical CV worker described in the linked guide. These requirements pin direct Python
dependencies, but are not a complete cross-platform transitive lockfile.

Only public backend URLs belong in the frontend `.env`:

```env
VITE_API_URL=http://127.0.0.1:8000/api/v1
VITE_WS_URL=ws://127.0.0.1:8000/ws/inventory
```

The access token is held in browser session storage, attached by the shared API client, and verified with `/api/v1/auth/verify` before protected routes render.

## Verification

```powershell
cd backend
pytest -q

cd ..\frontend
npm run typecheck
npm test
npm run build
```

GitHub Actions runs the same backend and frontend checks for pushes to `main` and `develop` and for pull requests.

## Primary API surfaces

- `POST /api/v1/auth/login`, `GET /api/v1/auth/verify`
- `GET /api/v1/dashboard/metrics`, `GET /api/v1/dashboard/store-info`
- `GET /api/v1/inventory`, `GET /api/v1/inventory/{zone}/{product}/history`
- `GET /api/v1/alerts`, alert acknowledgement/resolution/dismissal actions
- Camera CRUD under `/api/v1/cameras`
- `GET /api/v1/agents/runs`, `GET /api/v1/agents/stats`
- Authenticated `WS /ws/inventory`
- Durable media jobs under `/api/v1/video-jobs` for pictures, videos, and bounded camera captures

See [docs/API_REFERENCE.md](docs/API_REFERENCE.md) for the broader backend contract and [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for deployment guidance.

Uploaded video processing requires a separate durable worker. Run `python -m app.workers.video_jobs`
from `backend`, or use the `video-worker` Compose service. Setup, limits, model behavior, and
inventory safety are documented in [Video processing](docs/VIDEO_PROCESSING.md).

## Operational console (Phase 4)

Settings now contains the product catalog/threshold editor and administrator-only user management. Shelves provides camera and normalized ROI/class-mapping configuration. Inventory supports audited physical-count corrections and flags stale camera evidence.

See [Phase 4 operations](docs/PHASE_4_OPERATIONS.md) for permissions, worker restart instructions, correction semantics and the new API contracts. Service-backed deployment and real trained-model acceptance are still pending; local compilation and automated tests are not deployment certification.

## Notifications and reports (Phase 5)

The Reports page provides committed inventory summaries and authenticated CSV exports. Administrators can inspect notification readiness and durable email attempts in Settings. SMTP delivery is disabled by default and requires an explicitly approved recipient, server-side credentials, migration `0004`, and the separate notification worker. Local alert delivery was verified on 2026-10-23: the SMTP server accepted the open alert for both configured recipients. SMTP acceptance does not confirm inbox placement.

Read the [Phase 5 runbook](docs/PHASE_5_NOTIFICATIONS_REPORTS.md) before enabling delivery; it explains retries, snooze/cancellation, SMTP acceptance versus inbox delivery, and pending deployment checks.

## Read-only assistant (Phase 6)

The Assistant page provides account-private conversations, product-context follow-ups and sourced inventory/alert/history answers through a bounded LangGraph workflow. Counts and source links come from backend queries, not generated prose. Local mode is enabled by default; optional OpenAI question interpretation remains off.

Install the updated requirements (Pydantic 2.7.4 fixes the pinned LangGraph stack on Python 3.12.4+) and apply migration `0005`. Read the [Phase 6 runbook](docs/PHASE_6_ASSISTANT.md) for limitations, privacy and provider setup. No model-provider calls were made during implementation.

## Model handoff and evaluation (Phase 7)

Vision startup uses explicit `CV_MODEL_PATH` and `CV_MODEL_MANIFEST` values. The repository's
25-class YOLOv8 checkpoint and metadata-reviewed manifest have matching SHA-256 and embedded class
labels. Empty catalog SKU mappings remain review-only and cannot change inventory.

The [vision pipeline guide](docs/VISION_PIPELINE.md) covers Windows/NVIDIA setup, image/video/camera
testing, product identity review, dataset preparation, evaluation, and current limitations. No
held-out dataset was supplied, so accuracy is not claimed.

### Running alert email delivery locally

Start the notification worker alongside the API and video/event workers. Starting
only the frontend and API does not send alert emails.

```powershell
cd backend
python -m app.workers.notifications
```

Keep this process running and restart it after restarting the project or changing
SMTP settings in `.env`. It checks eligible open/escalated alerts every five seconds,
queues one delivery per alert stage and configured recipient, and retries temporary
SMTP failures. Resolved alerts and inventory that no longer qualifies are skipped.
Administrators can inspect delivery status in Settings; `accepted` means SMTP
accepted the message, so check spam/junk if it is absent from the inbox.

For Docker, include the notification service with
`docker compose --profile notifications up -d`.
