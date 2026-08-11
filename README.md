# IntelliStock Agent — AI-Powered Inventory Intelligence Platform

A Final Year Project (FYP) implementing an intelligent inventory monitoring system using computer vision, reconciliation logic, and LLM-based agents.

## Project Overview

**Pipeline:** Camera → CV (YOLO+ByteTrack) → ROI/Shelf Assignment → Observation Window → Reconciliation Engine → Trusted Inventory State → Events → Rule Engine → LangGraph Agents → FastAPI → WebSocket → Next.js Dashboard

**Core Principle:** YOLO output is an *observation*, not truth. Only the Reconciliation Engine, after confidence/temporal/tracking checks, may update trusted Inventory State.

## Architecture

- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy
- **Database:** PostgreSQL (source of truth), Redis (cache/events/transient)
- **Frontend:** Next.js 14, TypeScript, Tailwind CSS
- **CV:** Ultralytics YOLO, OpenCV, ByteTrack
- **AI:** LangGraph with configurable LLM provider
- **Deployment:** Local development with Docker Compose (production-ready structure)

## Prerequisites

### Required
- **Python 3.11+** — [Download](https://www.python.org/downloads/)
- **PostgreSQL 16** — [Download](https://www.postgresql.org/download/)
- **Redis** — [Download](https://github.com/microsoftarchive/redis/releases) or [Memurai](https://www.memurai.com/)
- **Node.js 20+** — [Download](https://nodejs.org/)
- **npm** — Included with Node.js

### Verify Installation
```powershell
python --version      # Should show Python 3.11+
psql --version        # Should show PostgreSQL 16
redis-cli --version   # Should show Redis version
node --version        # Should show Node.js 20+
npm --version         # Should show npm 11+
```

## Quick Start

### 1. Clone/Navigate to Project
```powershell
cd d:\intellistock 1
```

### 2. Set Up Environment
Copy `.env.example` to `.env` and update with your local credentials:
```powershell
Copy-Item .env.example .env
```

Edit `.env`:
- `DATABASE_URL` — Update password to match your PostgreSQL installation
- `JWT_SECRET` — Use provided dev key or generate a new one

### 3. Start PostgreSQL
Ensure PostgreSQL service is running:
```powershell
# On Windows, PostgreSQL typically starts automatically
# Verify: psql -U postgres -d intellistock -c "SELECT NOW();"
```

### 4. Start Redis
```powershell
# If installed as service, ensure it's running
# Or start manually from installation directory:
redis-server
```

### 5. Start Backend (Python/FastAPI)
```powershell
cd backend
python -m venv venv  # Create virtual environment (first time only)
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt  # Install dependencies (first time only)
uvicorn app.main:app --reload --host localhost --port 8000
```

Backend will be available at: **http://localhost:8000**

### 6. Start Frontend (Next.js)
In a **new terminal**:
```powershell
cd frontend
npm install  # Install dependencies (first time only)
npm run dev
```

Frontend will be available at: **http://localhost:3000**

## Verification

### Backend Health Check
```powershell
# In browser or PowerShell:
Invoke-WebRequest http://localhost:8000/health | ConvertTo-Json
```

Expected response:
```json
{
  "status": "ok",
  "database": "connected",
  "redis": "connected"
}
```

### Frontend
Open **http://localhost:3000** in browser. You should see:
- Navigation bar: "IntelliStock Agent" with menu items (Dashboard, Shelves, Inventory, Alerts, Settings)
- Welcome message on homepage

### Run Tests
```powershell
cd backend
.\venv\Scripts\Activate.ps1
$env:PYTHONPATH = "."
pytest tests/ -v
```

## Project Structure

```
intellistock-agent/
├── backend/
│   ├── app/
│   │   ├── api/              # REST endpoints
│   │   ├── services/         # Business logic
│   │   ├── repositories/     # Database access
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── events/           # Event definitions
│   │   ├── websocket/        # WebSocket handlers
│   │   ├── database/         # Database configuration
│   │   ├── core/             # Core utilities (config, health)
│   │   └── main.py           # FastAPI application
│   ├── tests/                # Pytest test suite
│   ├── requirements.txt      # Python dependencies
│   ├── pytest.ini            # Pytest configuration
│   ├── Dockerfile            # Container image
│   └── venv/                 # Python virtual environment (local)
├── frontend/
│   ├── app/                  # Next.js app directory
│   ├── components/           # React components
│   ├── public/               # Static assets
│   ├── package.json          # Node.js dependencies
│   ├── next.config.js        # Next.js configuration
│   ├── tsconfig.json         # TypeScript configuration
│   ├── tailwind.config.js    # Tailwind CSS configuration
│   └── Dockerfile            # Container image
├── cv/                       # Computer Vision pipeline (Phase 3+)
├── docs/                     # Documentation and architecture
├── docker-compose.yml        # Docker Compose configuration (for production)
├── .env                      # Environment variables (git-ignored)
├── .env.example              # Environment template (committed)
├── CLAUDE.md                 # Architecture rules (locked)
├── PROGRESS.md               # Phase-by-phase progress tracker
└── README.md                 # This file
```

## Development Workflow

### Adding a New Endpoint
1. Create schema in `backend/app/schemas/`
2. Create route in `backend/app/api/`
3. Create service in `backend/app/services/`
4. Create repository in `backend/app/repositories/` (for DB access)
5. Write tests in `backend/tests/`
6. Update API documentation in `docs/`

### Database Schema Changes
Use Alembic for migrations (Phase 6):
```powershell
cd backend
alembic revision --autogenerate -m "Add new table"
alembic upgrade head
```

### Committing Code
Use conventional commits:
- `feat:` — New feature
- `fix:` — Bug fix
- `test:` — Test addition/update
- `docs:` — Documentation
- `chore:` — Maintenance

Example: `git commit -m "feat: Add inventory state machine"`

## Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `DATABASE_URL` | PostgreSQL connection | `postgresql://postgres:password@localhost:5432/intellistock` |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` |
| `JWT_SECRET` | JWT signing key | `local-dev-secret-key-change-in-production` |
| `API_HOST` | Backend listen address | `localhost` |
| `API_PORT` | Backend port | `8000` |
| `NEXT_PUBLIC_API_URL` | Frontend API endpoint | `http://localhost:8000/api/v1` |
| `LOG_LEVEL` | Logging verbosity | `DEBUG` or `INFO` |

## Troubleshooting

### "Cannot connect to PostgreSQL"
- Verify PostgreSQL is running: `psql -U postgres -c "SELECT 1;"`
- Check `DATABASE_URL` in `.env` — password must be URL-encoded (e.g., `#` → `%23`)
- Verify database exists: `psql -U postgres -c "CREATE DATABASE intellistock;"`

### "Redis connection refused"
- Verify Redis is running: `redis-cli ping` (should return `PONG`)
- Check `REDIS_URL` in `.env`
- Ensure Redis service is started (or run `redis-server` manually)

### "Module not found" errors (Python)
- Ensure virtual environment is activated: `.\venv\Scripts\Activate.ps1`
- Reinstall dependencies: `pip install -r requirements.txt`
- Set `PYTHONPATH`: `$env:PYTHONPATH = "."`

### "Port 8000/3000 already in use"
- Check what's running: `netstat -ano | findstr :8000`
- Kill process: `taskkill /PID <PID> /F`
- Or change port in `.env` and restart

## Testing

### Run All Tests
```powershell
cd backend
.\venv\Scripts\Activate.ps1
$env:PYTHONPATH = "."
pytest tests/ -v
```

### Run Specific Test
```powershell
pytest tests/test_health.py::test_health_endpoint -v
```

### Run with Coverage
```powershell
pytest tests/ --cov=app --cov-report=html
# Opens htmlcov/index.html in browser
```

## Project Phases

- **Phase 1 (COMPLETE):** Project Foundation (monorepo, Docker, health checks)
- **Phase 2:** Frontend Shell (pages, components, protected routes)
- **Phase 3:** Computer Vision (YOLO, ByteTrack, ROI assignment, video replay)
- **Phase 4:** Inventory Reconciliation (observation window, state machine, confidence/temporal logic)
- **Phase 5:** Backend Core (database models, REST API, authentication)
- **Phase 6:** Event System (Redis pub/sub, rule engine, WebSocket)
- **Phase 7-8:** AI Agents & Integration (LangGraph, end-to-end pipeline)
- **Phase 9-15:** Hardening, Analytics, Copilot, Documentation

## Documentation

- **`CLAUDE.md`** — Architecture rules and locked tech stack (read first every session)
- **`PROGRESS.md`** — Current phase and completion status
- **`IntelliStock_Agent_Architecture_Review_and_Plan.md`** — Full architecture review and master backlog
- **`docs/`** — API reference, database schema, sequence diagrams (added as phases complete)

## Contributing

1. Read `CLAUDE.md` and `PROGRESS.md`
2. Check which task is "Currently On" in `PROGRESS.md`
3. Work on that task only (no jumping ahead)
4. Write tests alongside implementation
5. Run `pytest` before committing
6. Commit with conventional prefix: `feat:`, `fix:`, `test:`, `docs:`, `chore:`
7. Update `PROGRESS.md` and set "Currently On" to next task
8. Open PR to `develop` branch (do NOT commit to `main`)

## License

This project is part of a Final Year Project (FYP) for academic evaluation. See `LICENSE` file for details.

## Contact

For questions or issues, refer to the architecture documentation in `docs/` or the project README.

---

**Last Updated:** 2026-08-12  
**Current Phase:** 1 (Foundation)  
**Status:** ✅ Complete — Backend health checks + frontend running, smoke tests passing
