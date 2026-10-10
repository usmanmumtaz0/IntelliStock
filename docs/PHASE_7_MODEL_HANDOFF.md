# Phase 7: model handoff and offline count evaluation

The integration tooling is implemented; **real-model acceptance is pending**.
No trained weights or shelf footage have been supplied. Nothing in this phase
trains a model, downloads weights, activates a camera, or proves SKU accuracy.
No new dependency is needed: the root requirements file includes the existing
backend/CV dependencies. The pinned legacy YOLO/Torch checkpoint loader must only
load trusted files; review/modernize it before public production deployment.

## What to provide after training

- Trusted detection `best.pt` and its training run/version identifier.
- Exact class IDs/names from training, and one existing IntelliStock SKU per class.
- Training dataset configuration, split details and held-out validation results.
- Representative local shelf videos with independently labeled counts, including
  empty/restock, partial occlusion, lighting changes and similar-looking SKUs.
- Fixed-camera normalized ROI polygons and the confidence/empty-count settings
  that were actually evaluated.

Keep training and held-out footage separate by recording session/camera where
possible; adjacent frames from the same clip are not independent acceptance data.
Agree acceptable count error, coverage and false-empty rates before assessing the
held-out set. This implementation deliberately does not invent a passing threshold.

## 1. Review the model identity

Copy `backend/model-manifest.example.json` to a private
`model-manifest.local.json`. The template deliberately has an invalid placeholder
hash and is not an approved model. Fill in every model class, not only classes used
by one camera. `label` must exactly match the embedded model name; `sku` must match
the catalog, including case. IDs, labels and SKUs must be unique in the manifest.

Calculate the hash in PowerShell:

```powershell
(Get-FileHash -LiteralPath 'C:\IntelliStock\models\best.pt' -Algorithm SHA256).Hash.ToLowerInvariant()
```

The hash verifies file identity, not safety, accuracy or ownership. Only accept a
checkpoint from a trusted training source. Keep the manifest and weights immutable
while workers use them. A replacement requires a reviewed hash and worker restart.

From `backend`, with the project virtual environment active:

```powershell
python -m scripts.check_model --model C:/IntelliStock/models/best.pt --manifest C:/IntelliStock/model-manifest.local.json
```

This checks schema/hash without deserializing weights or connecting to services.
Add `--load-trusted` to load the checkpoint and check the detection task and exact
embedded class map. Neither command measures accuracy or verifies camera mappings.
The worker separately checks every configured shelf class ID against its catalog
SKU before opening a camera. Unknown/mismatched mappings stop startup.

## 2. Offline replay without changing inventory

Copy `backend/replay-zones.example.json` to a private
`replay-zones.local.json`. Match ROI polygons, class IDs and confidence to the
intended deployment. `zone_id` is your stable label for evaluation, not necessarily
a database UUID. Leave `allow_empty_class_ids` empty until empty shelf behavior has
been calibrated; an unqualified empty detection is an abstention, not stock zero.

Create a UTF-8 ground-truth CSV with this exact header:

```csv
sample_id,zone_id,sku,quantity
0,A-1,YOUR-EXISTING-SKU,3
20,A-1,YOUR-EXISTING-SKU,3
40,A-1,YOUR-EXISTING-SKU,0
```

These rows illustrate the format only, not actual labels. `sample_id` is the
zero-based decoded video frame index, using canonical integers (no leading zeros).
Label a fixed set of frames independently of predictions; do not remove difficult
frames after seeing the result. One row per frame/zone/SKU, quantities nonnegative
integers. Use separate evaluations per clip (frame indices restart at zero).

```powershell
python -m scripts.replay_counts --model C:/IntelliStock/models/best.pt --manifest C:/IntelliStock/model-manifest.local.json --video C:/IntelliStock/footage/shelf.mp4 --zones C:/IntelliStock/replay-zones.local.json --truth C:/IntelliStock/evaluation/truth.csv --max-frames 10000 | Out-File -Encoding utf8 C:/IntelliStock/evaluation/predictions.csv
```

Use a new output filename; shell redirection can overwrite an existing file. Check
the process exit code before scoring. Replay accepts local video only, never RTSP
or webcams. It processes every decoded frame in order to preserve ByteTrack and
three-observation track warm-up, and exports only labeled sample keys. It uses the
same coarse frame-quality, ROI, confidence and ambiguity checks as the worker.
Inference exceptions abort instead of being silently omitted. Unread labeled frame
indices, missing codecs, bad mappings and empty videos fail the command.

Diagnostics go to stderr; CSV goes to stdout. Missing predictions remain absent,
including warm-up, low-confidence and unqualified empty observations. The replay
has no database/Redis connection and does not create alerts, heartbeat or inventory
updates. It reports **observations**, not reconciled trusted inventory. It also
does not reproduce live frame dropping, camera timing or service latency. Video
decode failure after the last labeled frame cannot be distinguished from EOF here.

## 3. Score counts

```powershell
python -m scripts.evaluate_counts --truth C:/IntelliStock/evaluation/truth.csv --predictions C:/IntelliStock/evaluation/predictions.csv
```

The JSON report includes coverage/abstentions, exact-match rate, mean absolute
error, signed count bias, false-empty/false-nonempty predictions, and per-SKU and
per-zone slices. Error rates are conditional on available predictions; inspect
coverage alongside them. With no predictions, error rates are null, not zero.
Unexpected or duplicate sample keys are errors, not silently ignored. Both CSVs
are limited to 100,000 rows. A false-empty prediction means predicted zero when
ground truth is positive; it is not proof a stockout alert was actually generated.

These are count metrics, not detection mAP, tracker identity scores or end-to-end
business acceptance. The report always says `acceptance: not_assessed`. Preserve
the manifest/hash, ROI config, truth and predictions together with training metrics
and deployment settings when recording an evaluation result.

## 4. Activate only after review

The ignored root `.env` now has blank paths ready for your artifacts:

```dotenv
CV_MODEL_PATH=C:/IntelliStock/models/best.pt
CV_MODEL_MANIFEST=C:/IntelliStock/model-manifest.local.json
CV_DEVICE=cpu
```

**Compatibility change:** vision startup now requires both model and manifest.
`--model` and `--manifest` override the environment. No generic weights are used as
a fallback. Existing Phases 1-3 commands work after both variables are set. Docker
paths must refer to explicitly mounted container files; there is no automatically
started vision service/model volume in Compose. Never place these in `VITE_*`.

After offline review, configure the matching catalog and shelves, stop old camera
workers, then start one worker per camera:

```powershell
python -m app.workers.vision --camera-id YOUR_CAMERA_ID
```

Unlike offline replay, the normal vision worker writes through reconciliation and
can trigger alerts/notifications. Use an isolated test database and disabled
outbound notifications for service-backed acceptance before activating live data.
Do not use its `--source` override as a read-only accuracy test. For rollback, stop
the worker, restore the previously reviewed model/manifest/mappings and restart;
never silently rewrite inventory to fit a new model.

## Verification boundaries

Synthetic tests cover hash substitution, metadata/SKU mismatch, strict manifests,
worker refusal without a manifest, abstention/count metrics, invalid CSVs and
read-only replay track warm-up. The dependency smoke creates temporary untrained
weights and checks actual YOLO/ByteTrack loading, manifest metadata and video codecs.
Neither proves trained SKU accuracy. Real footage, agreed acceptance thresholds,
PostgreSQL/Redis reconciliation, alerts/WebSocket/browser behavior and target
hardware throughput remain pending. Earlier phase deployment checks remain pending
as recorded in `PROGRESS.md`; implementing Phase 7 does not close them.
