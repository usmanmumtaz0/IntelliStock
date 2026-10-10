"""Offline count scoring. Missing predictions are abstentions, never zero counts."""
import csv
from pathlib import Path

KEY_FIELDS = ("sample_id", "zone_id", "sku")
FIELDS = (*KEY_FIELDS, "quantity")
MAX_ROWS = 100_000


def read_counts(path):
    rows = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(FIELDS):
            raise ValueError("CSV header must be sample_id,zone_id,sku,quantity")
        for line, row in enumerate(reader, start=2):
            if line > MAX_ROWS + 1:
                raise ValueError("CSV exceeds 100000 rows")
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Malformed CSV row {line}")
            key = tuple(row[field].strip() for field in KEY_FIELDS)
            value = row["quantity"].strip()
            if any(not part or len(part) > 255 for part in key):
                raise ValueError(f"Invalid sample/zone/SKU at row {line}")
            if not value.isascii() or not value.isdecimal() or len(value) > 9:
                raise ValueError(f"Quantity must be a nonnegative integer at row {line}")
            if key in rows:
                raise ValueError(f"Duplicate sample/zone/SKU at row {line}")
            rows[key] = int(value)
    return rows


def _metrics(expected, predicted):
    paired = [(count, predicted[key]) for key, count in expected.items() if key in predicted]
    n = len(paired)
    nonempty = sum(actual > 0 for actual, _ in paired)
    false_empty = sum(actual > 0 and estimate == 0 for actual, estimate in paired)
    return {
        "expected_samples": len(expected), "predicted_samples": n,
        "abstained_samples": len(expected) - n,
        "coverage": n / len(expected) if expected else None,
        "exact_match_rate_on_predictions": sum(a == p for a, p in paired) / n if n else None,
        "mae_on_predictions": sum(abs(a - p) for a, p in paired) / n if n else None,
        "signed_bias_on_predictions": sum(p - a for a, p in paired) / n if n else None,
        "false_empty_predictions": false_empty,
        "false_empty_rate_on_nonempty_predictions": false_empty / nonempty if nonempty else None,
        "false_nonempty_predictions": sum(a == 0 and p > 0 for a, p in paired),
    }


def evaluate_counts(expected, predicted):
    if not expected:
        raise ValueError("Ground truth must contain at least one sample")
    if set(predicted) - set(expected):
        raise ValueError("Predictions include samples absent from ground truth")
    return {
        "overall": _metrics(expected, predicted),
        "by_sku": {sku: _metrics({k: v for k, v in expected.items() if k[2] == sku}, predicted)
                   for sku in sorted({key[2] for key in expected})},
        "by_zone": {zone: _metrics({k: v for k, v in expected.items() if k[1] == zone}, predicted)
                    for zone in sorted({key[1] for key in expected})},
        "acceptance": "not_assessed",
        "note": "Paired count metrics only; not detection mAP, tracking quality or live reconciliation acceptance.",
    }
