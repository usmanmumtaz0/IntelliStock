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

Prerequisites: Python 3.11+, Node.js 24+, PostgreSQL, and Redis.

1. Copy `.env.example` to `.env` and replace every credential placeholder.
2. Install and run the backend:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
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

Backend settings are listed in `.env.example`. The frontend uses:

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

See [docs/API_REFERENCE.md](docs/API_REFERENCE.md) for the broader backend contract and [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for deployment guidance.
