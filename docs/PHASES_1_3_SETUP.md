# Phases 1-3: setup, vision and durable delivery

## Setup on another PC

Prerequisites: Python 3.11/3.12, Node 24, PostgreSQL 16 and Redis 7.
From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
```

If `.env` does not exist, copy `.env.example` to `.env`. Supply actual database
credentials and a generated JWT secret. Never overwrite a configured file. Backend
loads root `.env`, then `backend/.env`; process variables override both. Keep real
credentials, credential-bearing camera URLs and private model/data files out of Git.
Only public URLs belong in frontend `VITE_*` variables.

Start PostgreSQL/Redis, create the configured database/role, then:

```powershell
cd backend
alembic upgrade head
python -m scripts.create_admin --email YOUR_EMAIL --username admin
uvicorn app.main:app --reload
```

Admin provisioning asks for the password interactively. In another terminal,
activate the same environment, change to `backend`, and start the event worker:

```powershell
python -m app.workers.events
```

In a third terminal, change to `frontend`, copy its `.env.example` only if needed,
then run `npm ci` and `npm run dev`. Console: http://localhost:3000;
API documentation: http://localhost:8000/docs.

## Docker and migrations

Set root `.env`, including `DATABASE_URL_DOCKER` pointing to host `postgres`.
Run `docker compose up --build`. Services share a network; backend runs Alembic
before startup; the event worker waits for backend health. Provision an admin with
`docker compose exec backend python -m scripts.create_admin`.

Production-style command:
`docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d`.
Configure your own TLS reverse proxy and CORS. This is not a production-security
certification. Back up existing databases before migration. Migration 0003 refuses
duplicate inventory zone/product rows; it never deletes them automatically.
Downgrade intentionally preserves new fields/tables to retain pending work.

## Vision configuration and recorded-video replay

### Pending trained model

Training is still in progress. Leave `CV_MODEL_PATH` blank until it is finalized.
No trained weights were supplied or activated during this implementation.
When ready, provide the trusted `best.pt` path, class-name/ID list (such as training
`data.yaml`), SKU mapping, and validation results. Set this in the root `.env`:

```dotenv
CV_MODEL_PATH=C:/IntelliStock/models/best.pt
CV_MODEL_MANIFEST=C:/IntelliStock/model-manifest.local.json
CV_DEVICE=cpu
```

Use an absolute path on each PC; for Docker it must refer to a mounted container
path. Start with CPU; only select a GPU device after validating its Torch/CUDA
installation. `--model` overrides the environment path. Without either, the worker
exits with an explicit training-pending message. Model binaries are ignored by Git.
Adding the path does not train the model or automatically establish SKU mappings.
Phase 7 additionally requires a reviewed manifest before worker startup. Follow
[model handoff and offline evaluation](PHASE_7_MODEL_HANDOFF.md) to prepare it and
evaluate recordings without changing inventory.

### Configure and run

Create products using the authenticated products API first. Copy
`backend/camera.example.json` to a private local configuration file. Set real SKU
values, model class IDs and normalized `[0,1]` ROI polygons. The operator CLI is
create-only and rolls back invalid configuration; restrict direct database access.

```powershell
cd backend
python -m scripts.configure_camera PATH_TO_PRIVATE_CONFIG.json
python -m app.workers.vision --camera-id RETURNED_ID --model PATH_TO_TRUSTED_MODEL.pt
```

Run one worker per camera. Restart it after mapping changes. Existing local trusted
weights are required; models are not automatically downloaded. Generic object
labels are not proof of SKU recognition. To replay a recorded video:

```powershell
python -m app.workers.vision --camera-id RETURNED_ID --model PATH_TO_TRUSTED_MODEL.pt --source PATH_TO_VIDEO.mp4
```

Replay reads frames in order at configured sampling speed, not original video wall
clock timing. EOF marks the camera offline without setting stock to zero. Live
capture uses a two-frame queue, dropping oldest frames. Stale/invalid frames, weak
detections and unknown objects abstain; trusted quantities stay unchanged with an
uncertain/offline status. A blocked camera driver stops the worker instead of
creating an unbounded number of capture threads.

`allow_empty` defaults to false. Enable it only after calibrating an unobstructed
fixed shelf ROI and validating representative footage. Image-quality and
unknown-object guards cannot detect every occlusion/model false negative; they are
not a guarantee against false stockouts. Multiple stable observations are required.

The canonical pipeline is `backend/app/cv/runtime.py` via `app.workers.vision`.
The old generic-product entry point is retired. Older helpers under `cv/` are
historical references, not supported runtime paths. All dependency manifests now
use the backend requirements. Torch/TorchVision use the matching legacy pair
documented by [PyTorch](https://pytorch.org/get-started/previous-versions/), retained
for the pinned YOLO loader. Load only trusted model files; modernize and audit the
legacy dependencies before public production deployment.

## Delivery and alerts

Run one event worker initially. PostgreSQL locks and a unique active-alert key
protect processing; multi-worker event ordering is not yet qualified. SQLite is
only for tests. Inventory commits queue outbox records in the same transaction.
The worker applies committed stock events in order, saves alerts and processing
markers transactionally, then retries Redis delivery separately.

Delivery is at-least-once: a crash after publishing but before database commit can
repeat an invalidation. Events contain stable IDs. Redis accepting a publish does
not prove browser receipt. Browser reconnect, Redis reconnect and periodic API
refresh restore authoritative state even after missed invalidations.

Stock recovery resolves active stock alerts. Active duplicates are suppressed;
cooldown and escalation use `ALERT_COOLDOWN_SECONDS` and
`ALERT_ESCALATION_SECONDS`. Snoozes expire in the event worker. Escalation is a
persisted dashboard event, not email/SMS delivery (Phase 5).

Manager/admin snooze API: `POST /api/v1/alerts/{id}/snooze` with `{"minutes":60}`.
Allowed durations: 30, 60, 240, 1440 minutes. The UI offers a one-hour action.

## Validation boundaries

From `backend`, run `python -m pytest -q`. For repeatable synthetic detector replay:
`python -m pytest tests/test_durable_pipeline.py -q`.
These tests cover stockout/restock, failure preservation, deduplication, rollback,
delivery retries, snooze/escalation and camera isolation without paid services.
The optional `python -m scripts.verify_cv_runtime` smoke generates temporary random
weights and a tiny synthetic video to check YOLO/ByteTrack and codecs without
downloading a trained model. It passed in the isolated Windows Python 3.12 setup.
CI additionally runs `scripts.verify_services` against disposable PostgreSQL/Redis;
that service-backed job has not been executed on this PC.
They do not prove real model accuracy, PostgreSQL concurrency, live Redis fan-out
or camera throughput. Real model/footage and service-backed acceptance are still
required before all three phases can be marked deployment-verified.
