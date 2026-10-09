# IntelliStock Agent — AI-Powered Shelf Inventory Monitoring

**Status:** Backend hardening implemented and verified
**Build:** ✅ Backend | ⚠️ Frontend source absent from this checkout | ✅ API Layer | ✅ AI Agents | 🔄 Verification

---

## Overview

IntelliStock Agent is an AI-powered inventory monitoring system that uses computer vision, probabilistic reconciliation, and LLM-based agents to provide trusted, real-time inventory state for retail shelves.

**Key Features:**
- 📷 Real-time shelf monitoring with YOLO + ByteTrack
- 🔄 Probabilistic reconciliation engine (not raw detections)
- 📊 Dashboard with live metrics and alerts
- 🤖 LangGraph AI agents for insights and anomaly detection
- 🔐 State machine inventory validation
- 🌐 WebSocket real-time updates

**Tech Stack:**
- Frontend: React 19 + Vite + TanStack Router
- Backend: FastAPI + SQLAlchemy + PostgreSQL
- CV: YOLOv8 + ByteTrack + OpenCV
- AI: LangGraph + (OpenAI/Claude configurable)
- Cache: Redis (pub/sub + events)
- Deployment: Docker Compose

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 13+
- Redis 6+
- Docker & Docker Compose (optional)

### Development Setup

**1. Clone and setup:**
```bash
git clone <repo>
cd intellistock-agent
```

**2. Configure and run the backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\Activate
pip install -r requirements.txt

# Copy environment template
cp ../.env.example .env
# Edit .env: set DATABASE_URL and generate a unique JWT_SECRET (32+ chars)

# Apply reviewed migrations
alembic upgrade head

# Securely create the initial administrator (interactive password prompt)
python -m scripts.create_admin --email you@example.com --username admin

# Start server
uvicorn app.main:app --reload
```
Backend: `http://localhost:8000`  
API Docs: `http://localhost:8000/docs`

**3. Frontend:** The current repository checkout does not contain the documented
`frontend/` source. Restore the frontend project before enabling the optional
Compose `frontend` profile. The backend wire contract is documented in
[`docs/API_REFERENCE.md`](docs/API_REFERENCE.md).

### Docker Compose (Backend Infrastructure)

```bash
docker compose up -d postgres redis backend
```

Services:
- FastAPI backend: `http://localhost:8000`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

Compose requires `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`,
`DATABASE_URL_DOCKER`, and `JWT_SECRET` in the untracked `.env` file. The
frontend service is profile-gated because its source is not present.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Retail Shelf Environment                           │
│  ├─ Cameras (RTSP/USB/File streams)                │
│  └─ Physical products & zones                       │
└────────────────────┬────────────────────────────────┘
                     │ Video frames
                     ▼
┌─────────────────────────────────────────────────────┐
│  Computer Vision Pipeline                          │
│  ├─ YOLOv8 detection (per frame)                  │
│  ├─ ByteTrack (persistent IDs)                    │
│  └─ ROI assignment (center-based polygon)         │
└────────────────────┬────────────────────────────────┘
                     │ Observations (temporary)
                     ▼
┌─────────────────────────────────────────────────────┐
│  Reconciliation Engine                              │
│  ├─ Redis observation window (TTL=600s)           │
│  ├─ Confidence checks + temporal validation       │
│  └─ State machine transitions (6 states)          │
└────────────────────┬────────────────────────────────┘
                     │ Verified inventory state changes
                     ▼
┌─────────────────────────────────────────────────────┐
│  PostgreSQL (Source of Truth)                       │
│  ├─ Inventory (current state)                      │
│  ├─ Events (audit trail)                           │
│  └─ Alerts (business state)                        │
└────────────┬──────────────────────────────┬─────────┘
             │ State changes                │ Queries
             ▼                              ▼
         ┌────────┐                    ┌─────────────┐
         │ Redis  │◄───┐              │  FastAPI    │
         │ Pub/Sub│    │              │  REST API   │
         └────────┘    └──────┐       └─────────────┘
             │                │           │
             └────────┬──────────────┬────┘
                      ▼              ▼
              ┌──────────────────────────────┐
              │  LangGraph AI Agents         │
              │  ├─ Supervisor (routing)     │
              │  ├─ Insight (analysis)       │
              │  ├─ Anomaly (detection)      │
              │  └─ Notification (alerts)    │
              └──────────────┬───────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │  Frontend (React + Vite)     │
              │  ├─ Dashboard                │
              │  ├─ Inventory view           │
              │  ├─ Alerts                   │
              │  └─ Settings                 │
              └──────────────────────────────┘
```

---

## File Structure

```
intellistock-agent/
├── backend/
│   ├── app/
│   │   ├── api/              # REST endpoints
│   │   │   ├── cameras.py
│   │   │   ├── products.py
│   │   │   ├── inventory.py
│   │   │   ├── zones.py
│   │   │   ├── alerts.py
│   │   │   ├── events.py
│   │   │   ├── dashboard.py
│   │   │   ├── agents.py
│   │   │   ├── websocket.py
│   │   │   └── __init__.py
│   │   ├── agents/           # LangGraph AI agents
│   │   │   ├── supervisor.py
│   │   │   ├── insight_agent.py
│   │   │   ├── anomaly_agent.py
│   │   │   ├── notification_agent.py
│   │   │   └── __init__.py
│   │   ├── cv/               # Computer vision (shared with cv/)
│   │   ├── core/             # Config, health checks
│   │   ├── database/         # SQLAlchemy setup
│   │   ├── events/           # Event pub/sub
│   │   ├── models/           # SQLAlchemy models
│   │   ├── repositories/     # Data access layer
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   ├── websocket/        # WebSocket manager
│   │   └── main.py           # FastAPI app
│   ├── tests/                # Unit & integration tests
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── venv/                 # Virtual environment
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── routes/           # TanStack Router pages
│   │   ├── components/       # React components
│   │   ├── lib/              # API client, store, utils
│   │   └── styles.css
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── public/
├── cv/                       # Standalone CV pipeline
│   ├── pipeline.py
│   ├── yolo_detector.py
│   ├── byte_tracker.py
│   ├── roi_assignment.py
│   └── test_pipeline.py
├── docs/
│   ├── API_REFERENCE.md      # API documentation
│   ├── DEPLOYMENT.md         # Deployment guide
│   ├── ARCHITECTURE.md       # System design
│   └── ...
├── docker-compose.yml
├── .env.example
├── .gitignore
├── PROGRESS.md               # Task progress tracker
├── CLAUDE.md                 # Development guidelines
└── README.md                 # This file
```

---

## API Endpoints

See [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) for complete API documentation.

### Key Endpoints

**Dashboard:**
- `GET /api/v1/dashboard/metrics` — KPI aggregation
- `GET /api/v1/dashboard/store-info` — Store metadata

**Inventory:**
- `GET /api/v1/zones` — List shelf zones
- `GET /api/v1/inventory` — Inventory state
- `POST /api/v1/inventory/reconcile` — Reconcile observation

**Alerts & Events:**
- `GET /api/v1/alerts` — Active alerts
- `GET /api/v1/events` — Activity feed
- `POST /api/v1/alerts/{id}/acknowledge` — Mark acknowledged

**AI Agents:**
- `GET /api/v1/agents/runs` — Agent execution history
- `GET /api/v1/agents/stats` — Agent performance stats

**Real-time:**
- `WS /ws/inventory` — authenticated WebSocket event stream

---

## Configuration

### Backend (.env)

```env
# API
APP_ENV=development
API_HOST=0.0.0.0
API_PORT=8000

# Database
DATABASE_URL=postgresql://DB_USER:URL_ENCODED_PASSWORD@localhost:5432/intellistock

# Cache
REDIS_URL=redis://localhost:6379/0

# Authentication (generate a unique random value; never commit it)
JWT_SECRET=<at-least-32-random-characters>
JWT_EXPIRATION_HOURS=8

# Login throttling
RATE_LIMIT_LOGIN_REQUESTS=5
RATE_LIMIT_LOGIN_WINDOW_SECONDS=60

# Logging
LOG_LEVEL=INFO

# CV Pipeline
CV_CONFIDENCE_THRESHOLD=0.6
CV_FPS_SAMPLING=2

```

### Frontend (.env)

```env
VITE_API_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/ws/inventory
```

---

## Development Workflow

1. **Read `CLAUDE.md`** — Development guidelines and non-negotiables
2. **Check `PROGRESS.md`** — Current task status
3. **Work from task list** — Don't skip ahead
4. **After each task:**
   - Run tests: `pytest tests/`
   - Test manually (see verification below)
   - Update `PROGRESS.md`
   - Commit: `git commit -m "feat: <task>"`

---

## Testing

### Backend Tests

```bash
cd backend
pytest tests/
pytest tests/test_reconciliation.py -v
pytest tests/test_health.py -v
```

### Frontend Tests (Playwright, if added)

```bash
cd frontend
npm run test
```

---

## Deployment

### Docker Compose (Recommended)

```bash
docker-compose up -d
```

Automatically starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Backend (port 8000)
- Frontend (port 3000)

### Manual Deployment

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for production deployment guide.

---

## Monitoring & Debugging

### Backend Logs
```bash
docker-compose logs -f backend
```

### Database
```bash
psql -h localhost -U postgres -d intellistock
SELECT * FROM inventory;
```

### Redis
```bash
redis-cli
> KEYS *
> GET observation_window:A-1
```

### API Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Troubleshooting

### Frontend won't connect to backend
- Check backend is running: `curl http://localhost:8000/health`
- Verify `VITE_API_URL` in `.env`
- Check browser console for CORS errors

### Database migration errors
```bash
cd backend
alembic downgrade -1
alembic upgrade head
```

### Redis connection failed
```bash
redis-cli ping
# Should return "PONG"
```

### CV pipeline not detecting
- Check camera source is accessible
- Verify ROI polygons are valid
- Increase `CV_CONFIDENCE_THRESHOLD` if too strict

---

## Phase Status

| Phase | Epic | Status | Key Tasks |
|-------|------|--------|-----------|
| 1 | Foundation | ✅ Complete | Monorepo, config, CI |
| 2 | Frontend Shell | ⚠️ Not in checkout | Historical docs reference an external/missing frontend |
| 3 | Computer Vision | ✅ Complete | YOLO, ByteTrack, ROI |
| 4 | Reconciliation | ✅ Complete | Engine, state machine |
| 5 | Backend Core | ✅ Complete | Auth, DB, REST, events |
| 6 | E2E Integration | 🔄 In Progress | Backend API present; frontend source and E2E flow pending |
| 7 | AI Agents | ✅ Complete | Supervisor, insight, anomaly, notification |
| 8 | Hardening & Docs | ✅ Complete | Security implementation, migrations, regression tests, docs |

---

## Next Steps

### Remaining integration work
- [ ] Restore and update the missing frontend client
- [ ] Run the end-to-end CV → reconciliation → API → WebSocket flow
- [ ] Evaluation report for FYP

### Post-MVP
- [ ] Multi-store support
- [ ] Advanced forecasting
- [ ] Mobile app
- [ ] Cloud deployment (AWS/GCP)

---

## License

Proprietary — IntelliStock Final Year Project

---

## Support

For issues or questions:
1. Check `PROGRESS.md` for current status
2. Review `docs/` for detailed guides
3. Check backend logs: `docker-compose logs backend`
4. Review API docs: `http://localhost:8000/docs`

---

**Last Updated:** October 7, 2026  
**Maintainers:** FYP Team  
**Contact:** claude.md for guidelines

