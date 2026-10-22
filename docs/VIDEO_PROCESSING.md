# Video processing

IntelliStock processes uploaded MP4, AVI, and MOV footage, JPG/PNG/WebP pictures, or a bounded segment from an existing camera.
The API validates and stores the source, creates a durable database job, and returns immediately. A separate
worker samples frames sequentially, runs the configured YOLO model, applies ByteTrack when enabled, writes
annotated evidence, and records every frame and detection in PostgreSQL.

Uploaded jobs are storage-affine. The media volume contains an opaque node marker, and newly queued jobs are
claimed only by workers that can see that same volume. The API still reports the public state as `queued`.
This prevents an older worker connected to the same database on another machine from claiming a local file.

## Setup

Apply the latest Alembic migrations, then configure the settings in `.env.example`. At minimum,
`CV_MODEL_PATH` must identify readable trained weights. A reviewed `CV_MODEL_MANIFEST` enables product/SKU
mapping; without it, model class labels are retained and all results remain review-only. Do not point the
worker at `models/model-manifest.draft.json` until every blank SKU is reviewed and completed.

Start the API and the durable worker in separate terminals:

```powershell
cd backend
alembic upgrade head
uvicorn app.main:app --reload

# second terminal, from backend
python -m app.workers.video_jobs
```

Docker Compose starts the `video-worker` service automatically and shares `backend/media` with the API.
The worker uses `/models/best.pt` inside the container. CUDA is optional; set `CV_DEVICE=cpu` for the portable
default or a supported CUDA device only after its runtime is installed and verified.

Open `/video-processing` in the authenticated console. Staff, managers, and administrators can upload pictures or videos and
review their jobs. Only administrators can start a job from a configured camera. Administrators can review
all jobs; other roles can only see their own.

## Controls and results

`VIDEO_MAX_UPLOAD_BYTES`, `IMAGE_MAX_UPLOAD_BYTES`, `VIDEO_MAX_FRAMES`, and `VIDEO_MAX_DURATION_SECONDS` are hard server limits.
Sampling is timestamp-based and decoding is sequential, so long footage is not loaded into memory. The
worker processes one job at a time and commits each sampled frame so progress and partial evidence survive
process failures. On restart, interrupted jobs are returned to the queue.

Pictures use the same trained model and evidence format as video. Each picture produces one frame at timestamp
zero, with tracking disabled because there is no temporal sequence.

Each result includes its source timestamp, source frame index, inference time, annotated image, class label,
confidence, pixel and normalized bounding boxes, and optional track ID. The job summary distinguishes raw
detection instances from unique tracked objects. Neither value directly changes inventory. The existing
manifest-backed observation and reconciliation pipeline remains the only path to committed stock changes.

Camera sources accept RTSP(S) and HTTP(S). Private and loopback IP addresses are accepted for on-premise
cameras; public hosts must appear in `VIDEO_ALLOWED_CAMERA_HOSTS`. URLs and credentials stay in the camera
record and are never returned by the video-job API.

## Troubleshooting

- A job that remains `queued` usually means `python -m app.workers.video_jobs` is not running.
- The worker logs its resolved `media_root` at startup. The API and worker must resolve the same
  `VIDEO_STORAGE_ROOT`; Docker deployments must mount that directory into both services.
- A failed job can be retried from the results panel while its validated uploaded source remains
  available. Retry clears partial database evidence before reprocessing, so it does not duplicate detections.
- `Configured trained model weights are missing` means `CV_MODEL_PATH` is wrong for the worker process.
- An unreadable-video error means the installed OpenCV/FFmpeg build cannot decode the container or codec.
- Product IDs remain empty until an approved model manifest maps every relevant class to an existing SKU.
- Worker logs contain technical exceptions; API job errors are deliberately bounded and omit secrets.
