# IntelliStock model artifacts

The owner approved publishing these files with the repository:

- `best.pt`: supplied 25-class product detection checkpoint (22,525,738 bytes).
- `model-manifest.draft.json`: exact class labels and checkpoint hash; product codes
  are intentionally blank pending catalog mapping approval. Not an activation manifest.

SHA-256: `6502323f9dc4339312bc41d1e5281cd7d51d0c84f42c6286970db8259a5d46c5`.

On another PC, configure the root `.env` with an absolute `CV_MODEL_PATH` pointing
to this checkout's `models/best.pt`. Keep `CV_MODEL_MANIFEST` blank until the
product mapping and shelf validation are complete. Do not activate the draft.
Secrets and machine-specific environment settings are not included in Git.

CPU loading and blank-frame inference/tracker smoke checks passed; actual shelf
counting accuracy has not been evaluated. Only load checkpoints from trusted
sources. See `docs/PHASE_7_MODEL_HANDOFF.md` for evaluation and activation steps.

Other models, runtime configuration, caches and local manifests remain ignored.
