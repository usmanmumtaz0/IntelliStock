# Phase 4: operating the console

This release uses the existing single-store role model. It does not introduce store tenancy, password reset emails, Google authentication or a trained vision model.

## Page map

| Page | Operations | Access |
| --- | --- | --- |
| Settings | Product creation, names/descriptions and stock thresholds | Admin / manager; staff can view catalog |
| Settings | Create accounts, change roles, activate/deactivate accounts | Admin only |
| Shelves | Existing camera create/enable/disable; edit source, FPS, timeout; configure shelf polygons and class-to-product mappings | Admin / manager |
| Inventory | Select a specific shelf/product record, review history, record a physical-count correction with reason | Admin / manager corrections; all roles read |

Backend role checks are authoritative, not just hidden buttons. API tokens resolve the current active account on every request. Open WebSockets recheck active status/expiry at least every 15 seconds. The frontend rechecks the session every 30 seconds and clears cached data when signing out. Account creation requires a 12–128 character password and stores only an Argon2id hash. Account responses and audits exclude password material. Share initial passwords securely; there is no self-service password-reset workflow in this phase.

## Products and thresholds

Create products in Settings before configuring shelf mappings. SKU is immutable after creation. Low-stock comparison is inclusive (`quantity <= threshold`); zero means out of stock. Changing the threshold re-evaluates trusted inventory states and queues committed-state events for the event worker. Offline/uncertain records are not silently relabeled as healthy. Reorder point remains a planning reference, not an automatic purchase command.

Product mutations are audited transactionally. Referenced products cannot be deleted through the API; stock history and mappings must not be silently removed. Cameras with zones/history must be disabled instead of deleted.

## Shelf calibration workflow

1. Open a camera on Shelves, disable it, and stop its vision worker.
2. Edit camera fields or select/create a shelf zone.
3. Enter ROI corners in perimeter order using normalized coordinates (0–1). The diagram previews geometry only, not a camera image. The camera cards remain explicitly labeled illustrative layouts.
4. Map each trained-model class ID to one existing product. Class IDs and products must be unique within a zone. IDs cannot be checked against your model until you provide it; the vision worker validates them on startup.
5. Leave **Allow empty shelf to commit zero** off until the ROI has been calibrated and tested. A missing detection is not automatically proof of zero stock.
6. Save, enable the camera, and restart its vision worker. Configuration revisions cause old workers to exit; saving a form does not launch a worker or install a model.

The API rejects active-camera shelf configuration, invalid/self-intersecting/zero-area polygons, missing products and duplicate mappings. You cannot move an existing zone between cameras or remove a mapped product that already has inventory. These safeguards preserve historical identity. Configuration changes retain quantities but mark existing zone inventory offline until new evidence arrives.

Camera source values may contain credentials: the editor masks them and audits redact them. Existing camera-read API permissions are unchanged; avoid credential-bearing URLs for environments where staff must not know camera credentials. Restrict deployment access and use a protected camera source. Application/API secrets remain in ignored `.env` files.

## Manual inventory corrections

Open the desired inventory record and enter the physical count and a reason. The backend locks the record and checks `expected_updated_at`; concurrent changes return HTTP 409 instead of silently overwriting an unseen count. Refresh/review the record before retrying.

One transaction writes quantity/state, immutable correction history with actor/reason, an audit log, and a durable stock event. No camera observation or confidence is fabricated. The record is not camera-verified again until subsequent reconciliation. A correction is **not a permanent override**: later reconciled observations may replace it. Stop/disable faulty vision ingestion before correcting counts if you do not want immediate camera updates.

The console flags observations older than 60 seconds or missing/invalid timestamps. This visual freshness warning does not erase committed stock. Offline and uncertain states remain visible. Modification time and observation time are intentionally different.

## API additions

- `GET/POST /api/v1/users`, `PUT /api/v1/users/{id}` (admin)
- `GET /api/v1/zones/{id}/configuration` (authenticated)
- `POST /api/v1/zones`, `PUT /api/v1/zones/{id}` (admin/manager)
- `POST /api/v1/inventory/{id}/corrections` (admin/manager)

Existing product/camera routes now audit writes and guard referenced deletes. Camera updates accept `offline_timeout_seconds`. No schema migration or new library was required for Phase 4; run the existing migrations through 0003 for the earlier durable pipeline.

## Acceptance still requiring deployment

Docker, PostgreSQL and Redis were not found locally (commands, standard install paths, services and listening ports checked). Service-backed checks remain pending; the previously added CI smoke job has not been run here. Browser interaction acceptance against the real deployed backend is also pending; API tests, frontend unit/type checks and production compilation do not substitute for it. Real detection accuracy remains pending trained weights, class mapping and shelf footage.
