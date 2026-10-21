# IntelliStock model artifacts

The owner approved publishing these files with the repository:

- `best.pt`: supplied 25-class product detection checkpoint (22,525,738 bytes).
- `model-manifest.json`: metadata-reviewed activation manifest with matching task,
  class labels, and checkpoint hash. Product codes remain blank, so exact catalog
  mappings stay review-only.
- `model-manifest.draft.json`: retained as the original handoff record.

SHA-256: `6502323f9dc4339312bc41d1e5281cd7d51d0c84f42c6286970db8259a5d46c5`.

On another PC, configure the root `.env` with absolute `CV_MODEL_PATH` and
`CV_MODEL_MANIFEST` paths pointing to `best.pt` and `model-manifest.json`.
Unmapped labels may create category/unknown review evidence but cannot update
inventory. Secrets and machine-specific environment settings are not included in Git.

CPU loading and blank-frame inference/tracker smoke checks passed; actual shelf
counting accuracy has not been evaluated. Only load checkpoints from trusted
sources. See `docs/VISION_PIPELINE.md` for setup and evaluation steps.

Other models, runtime configuration, caches and local manifests remain ignored.
