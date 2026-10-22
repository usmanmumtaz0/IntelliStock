# IntelliStock vision and product identity

## Implemented architecture

The required baseline is the repository checkpoint `models/best.pt`. Its SHA-256 is
`6502323f9dc4339312bc41d1e5281cd7d51d0c84f42c6286970db8259a5d46c5`; the embedded
task is detection, the training input size is 640, and the 25 embedded class labels match
`models/model-manifest.json`. The checkpoint was preserved unchanged.

`app.cv.detectors.Detector` is the common detector contract. The configured
`UltralyticsYOLODetector` loads the trusted YOLOv8 checkpoint once per worker, applies configured
confidence/NMS/max-detection limits, uses ByteTrack for video/camera jobs, resets tracker state
between sources, and exposes a read-only health report. `CV_DEVICE=auto` selects `cuda:0` only
when the installed PyTorch build can actually use CUDA; otherwise it reports and uses CPU.

The identity pipeline deliberately separates:

1. YOLO localization and detector class evidence.
2. Conservative grocery-category mapping.
3. Catalog-constrained exact identity.
4. Human review for category-only, unknown, or ambiguous detections.

An exact detector label becomes `identified` only when it uniquely matches a catalog product and
meets `CV_IDENTITY_MIN_CONFIDENCE`, or when an authorized manager/admin confirms a catalog item.
Optional pretrained identity evidence is implemented around the baseline detector:

- PP-OCRv6 reads packaging text from bounded product crops.
- DINOv2 compares each crop with explicitly configured, server-local catalog reference images.
- Strong OCR and visual agreement is fused; conflicting evidence becomes `ambiguous` and remains
  in human review.
- Video tracks reuse evidence until a materially sharper crop is available, avoiding OCR on every
  sampled frame.

Both providers are disabled by default and lazy loaded. Missing packages, model files, unreadable
references, or inference errors degrade to review-only evidence rather than failing the job. DINOv2
uses `local_files_only=True`; the API and worker never download its weights. A manually reviewed or
automatically identified detection changes evidence only and never changes inventory quantity.
YOLO-World and Grounding DINO remain evaluation/annotation options rather than production detectors;
they must beat the baseline on the same held-out manifest before activation.

## Database and APIs

Migration `0011_product_identity` adds brand, category, variant, package size, barcode, and reference
image metadata to products. Video detections store identity state, confidence, category, catalog
link, and evidence.

- `GET /api/v1/video-jobs/model-health` reports model, manifest, classes, and actual device.
- `GET /api/v1/video-jobs/review-queue` returns unresolved evidence scoped by job ownership/RBAC.
- `POST /api/v1/video-jobs/detections/{id}/identify` records manager/admin catalog review.
- Existing image, video, camera, job, frame, annotation, and cancellation endpoints remain in use.

Vision jobs publish durable `vision_job_updated` outbox events. The authenticated WebSocket causes
the frontend to invalidate job and review queries. Polling remains as recovery for transient Redis
disconnects.

## Windows setup

From PowerShell in the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

For NVIDIA execution, install a CUDA-capable PyTorch build compatible with the installed driver,
then confirm it before selecting CUDA:

```powershell
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

Set absolute local paths in `.env`; never commit the real `.env`:

```dotenv
CV_MODEL_PATH=C:/path/to/IntelliStock/models/best.pt
CV_MODEL_MANIFEST=C:/path/to/IntelliStock/models/model-manifest.json
CV_DETECTOR=yolov8
CV_DEVICE=auto
CV_CONFIDENCE_THRESHOLD=0.40
CV_NMS_IOU_THRESHOLD=0.45
CV_MAX_DETECTIONS=300
CV_IDENTITY_MIN_CONFIDENCE=0.65
CV_OCR_ENABLED=true
CV_OCR_VERSION=PP-OCRv6
CV_OCR_DEVICE=cpu
CV_EMBEDDING_ENABLED=false
CV_EMBEDDING_MODEL_PATH=C:/path/to/IntelliStock/models/dinov2-small
CV_REFERENCE_IMAGE_ROOT=C:/path/to/IntelliStock/backend/media/product-references
```

Create the reviewed 25-class catalog mapping before processing media:

```powershell
python -m scripts.sync_model_catalog --admin-email admin@intellistock.com
python -m scripts.sync_model_catalog --admin-email admin@intellistock.com --apply
```

The command is idempotent and audited. It creates missing products, preserves exact
matches, and refuses conflicting existing SKUs. Uploads then resolve detections to
catalog products. Live shelf quantities update only after an administrator maps the
relevant class IDs to products in a calibrated shelf zone.

PP-OCRv6 and DINOv2 dependencies are included in the main backend requirements:

```powershell
pip install -r requirements.txt
```

PP-OCR may retrieve its pretrained files only during an explicit connected setup. For DINOv2,
download `facebook/dinov2-small` ahead of time into the configured local directory, then run the
worker without network access. Product `reference_images` entries are relative paths below
`CV_REFERENCE_IMAGE_ROOT`; absolute paths and URLs are rejected. Use multiple licensed views per SKU.
Enable one provider at a time, run the held-out evaluation, and keep it enabled only when its unknown
rejection and top-1 results improve the baseline.

Verify and migrate:

```powershell
python -m scripts.check_model --model ..\models\best.pt --manifest ..\models\model-manifest.json --load-trusted --device cpu
alembic upgrade head
```

Run the API and worker in separate PowerShell terminals with the environment activated:

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
python -m app.workers.video_jobs
```

Run the frontend from `frontend`:

```powershell
npm install
npm run dev -- --host 127.0.0.1 --port 3000
```

## Functional verification

1. Open **Vision Processing** and upload a JPG/PNG/WebP. Confirm a queued job becomes completed,
   an annotated frame appears, identity state is visible, and Agent Activity records the run.
2. Upload MP4/MOV/AVI with tracking enabled. Confirm sampled frames show stable track IDs and the
   job summary distinguishes detection instances from unique tracks.
3. As an admin, configure `webcam://0` for a local webcam or an allowlisted RTSP/HTTP camera under **Shelves**, then queue a
   bounded 60-second camera capture. Disconnecting the stream must fail the job with a controlled
   error and failed Agent Activity entry.
4. Add product brand/category/variant/package/barcode metadata under **Settings â†’ Product catalog**.
   Review unresolved detections as a manager/admin. Confirm inventory quantities and inventory
   history do not change from identity review.
5. Keep the browser open while a job runs. `vision_job_updated` events travel through the durable
   outbox, Redis channel, authenticated WebSocket, and query invalidation. Stop Redis temporarily;
   periodic polling must still recover the final job state.

## Dataset preparation and evaluation

Create a CSV with `image,sku,split`, using only images you are licensed to use. Ensure different
views of the same capture session stay in one split. The preparation command validates decoding and
rejects exact file leakage across train, validation, and test:

```powershell
python -m scripts.prepare_reference_dataset --csv C:\data\pakistani-products.csv --output C:\data\reference-manifest.json
```

For detection evaluation, copy `docs/VISION_EVALUATION_MANIFEST.example.json`, enter normalized
ground-truth boxes, and keep test images outside training data. Run:

```powershell
python -m scripts.evaluate_vision --dataset C:\data\evaluation.json --model ..\models\best.pt --manifest ..\models\model-manifest.json --device auto --output C:\data\evaluation-report.json
```

The report calculates precision, recall, mAP@0.5, per-class AP, confidence-threshold calibration,
identity top-1 where SKU mappings exist, unknown rejection, latency, throughput, and GPU memory.
Metrics remain `null` when the manifest lacks the required ground truth. Duplicate-counting error
requires labeled video tracks and is explicitly left unmeasured for image-only manifests.

## Known limitations

- No held-out image/video dataset was supplied, so detection accuracy and Pakistani-brand/SKU
  accuracy are not claimed.
- The reviewed checkpoint contains exact product labels, but its manifest has no catalog SKUs yet;
  those detections remain category-only unless a catalog name matches uniquely or a reviewer acts.
- OCR and visual embedding retrieval are implemented but remain opt-in until their model files,
  local weights/reference images, and held-out validation data are installed. UPC/EAN decoding and
  open-vocabulary production detection remain future evaluated additions.
- This machine currently exposes CPU-only PyTorch, so CUDA latency and GPU memory are not measured.
- Camera jobs are bounded captures rather than an always-on multi-camera service. This prevents
  unbounded VRAM/task growth; continuous scheduling can be added after camera-specific load tests.
