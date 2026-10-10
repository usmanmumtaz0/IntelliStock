"""Read-only local-video replay: CSV observations on stdout, never database writes.

Use frame indices (zero-based) as ground-truth sample_id. Every decoded frame is
processed to preserve track warm-up, but only ground-truth keys are exported.
"""
import argparse
import csv
from contextlib import redirect_stdout
from pathlib import Path
import sys

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.cv.count_evaluation import FIELDS, read_counts
from app.cv.model_artifact import verify_artifact, verify_model_metadata
from app.cv.runtime import ShelfPipeline, Zone, YOLOTracker, frame_healthy
from app.schemas.zone import validate_polygon


class ReplayZone(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    zone_id: str = Field(min_length=1, max_length=255)
    polygon: list[tuple[float, float]] = Field(min_length=3, max_length=32)
    class_ids: list[int] = Field(min_length=1, max_length=100)
    allow_empty_class_ids: list[int] = Field(default_factory=list)
    confidence: float = Field(default=0.6, ge=0.6, le=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_zone(self):
        validate_polygon(self.polygon)
        if len(set(self.class_ids)) != len(self.class_ids):
            raise ValueError("Duplicate class IDs")
        if not set(self.allow_empty_class_ids) <= set(self.class_ids):
            raise ValueError("Empty-count classes must be mapped to the zone")
        return self


class ReplayConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    zones: list[ReplayZone] = Field(min_length=1, max_length=100)


def replay_zones(config, manifest, truth):
    classes = {item.class_id: item.sku for item in manifest.classes}
    if len({z.zone_id for z in config.zones}) != len(config.zones):
        raise ValueError("Duplicate zone IDs")
    zones = []
    for row in config.zones:
        if not set(row.class_ids) <= set(classes):
            raise ValueError("Replay configuration includes unknown model classes")
        zones.append(Zone(row.zone_id, row.polygon,
                          {i: classes[i] for i in row.class_ids},
                          frozenset(row.allow_empty_class_ids), row.confidence))
    valid_pairs = {(z.id, sku) for z in zones for sku in z.products.values()}
    if not truth:
        raise ValueError("Ground truth is empty")
    for sample, zone, sku in truth:
        if not sample.isascii() or not sample.isdecimal() or str(int(sample)) != sample:
            raise ValueError("sample_id must be a canonical zero-based frame index")
        if (zone, sku) not in valid_pairs:
            raise ValueError("Ground-truth zone/SKU is absent from replay configuration")
    return zones


def collect_predictions(source, tracker, zones, truth, max_frames):
    pipeline = ShelfPipeline(zones)
    predictions = {}
    decoded = 0
    for sequence in range(max_frames):
        ok, frame, captured = source.read()
        if not ok:
            break
        decoded += 1
        healthy = frame_healthy(frame)
        detections = tracker.detect(frame) if healthy else []
        for zone, sku, quantity, _ in pipeline.observe(detections, sequence, captured, healthy):
            key = (str(sequence), zone, sku)
            if key in truth:
                predictions[key] = quantity
    if decoded == 0:
        raise ValueError("No video frames decoded; check the local file and codec")
    if max(int(key[0]) for key in truth) >= decoded:
        raise ValueError("Ground-truth frame exceeds decoded video or --max-frames; no report emitted")
    return predictions, decoded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ("model", "manifest", "video", "zones", "truth"):
        parser.add_argument("--" + argument, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--max-frames", type=int, default=10000)
    args = parser.parse_args()
    try:
        if not 1 <= args.max_frames <= 100000:
            raise ValueError("--max-frames must be between 1 and 100000")
        if not Path(args.video).is_file():
            raise ValueError("Replay accepts an existing local video only")
        manifest = verify_artifact(args.model, args.manifest)
        truth = read_counts(args.truth)
        config = ReplayConfig.model_validate_json(Path(args.zones).read_text(encoding="utf-8"))
        zones = replay_zones(config, manifest, truth)
        # Keep third-party diagnostics out of machine-readable CSV stdout.
        with redirect_stdout(sys.stderr):
            tracker = YOLOTracker(args.model, args.device)
            verify_model_metadata(manifest, tracker.model)
            from app.cv.capture import FrameSource
            source = FrameSource(str(Path(args.video).resolve()), replay=True)
            try:
                predictions, decoded = collect_predictions(source, tracker, zones, truth, args.max_frames)
            finally:
                source.close()
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(FIELDS)
    for key, count in predictions.items():
        writer.writerow((*key, count))
    print(f"Read-only replay: {decoded} frames, {len(predictions)}/{len(truth)} labeled predictions; "
          f"model {manifest.model_version}, SHA-256 {manifest.sha256}. No inventory updated.", file=sys.stderr)


if __name__ == "__main__":
    main()
