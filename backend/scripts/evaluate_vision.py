"""Evaluate the trusted detector on a labeled JSON manifest without inventing metrics."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
from statistics import mean
from time import perf_counter

from app.cv.detectors import UltralyticsYOLODetector
from app.cv.model_artifact import verify_artifact


def iou(left, right) -> float:
    x1, y1 = max(left[0], right[0]), max(left[1], right[1])
    x2, y2 = min(left[2], right[2]), min(left[3], right[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = ((left[2] - left[0]) * (left[3] - left[1])
             + (right[2] - right[0]) * (right[3] - right[1]) - intersection)
    return intersection / union if union > 0 else 0.0


def average_precision(records, ground_truth_count: int) -> float | None:
    if ground_truth_count == 0:
        return None
    records = sorted(records, key=lambda item: item[0], reverse=True)
    tp = fp = 0
    points = [(0.0, 1.0)]
    for _confidence, matched in records:
        tp += int(matched)
        fp += int(not matched)
        points.append((tp / ground_truth_count, tp / max(tp + fp, 1)))
    points.append((1.0, 0.0))
    for index in range(len(points) - 2, -1, -1):
        points[index] = (points[index][0], max(points[index][1], points[index + 1][1]))
    return sum(
        (points[index][0] - points[index - 1][0]) * points[index][1]
        for index in range(1, len(points))
    )


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--iou", type=float, default=0.5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    dataset_path = args.dataset.resolve()
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    samples = dataset.get("samples")
    if dataset.get("schema_version") != 1 or not isinstance(samples, list) or not samples:
        parser.error("Dataset must be schema_version 1 with a nonempty samples list")
    reviewed_manifest = verify_artifact(args.model, args.manifest)
    sku_by_class = {item.class_id: item.sku for item in reviewed_manifest.classes if item.sku}
    detector = UltralyticsYOLODetector(
        args.model, args.manifest, args.device,
        iou_threshold=0.45, max_detections=300, default_image_size=args.image_size,
    )
    detector.load_model()

    import cv2
    import torch

    if detector.cuda_available:
        torch.cuda.reset_peak_memory_stats()
    records_by_class = defaultdict(list)
    gt_by_class = defaultdict(int)
    all_records = []
    latencies = []
    identity_total = identity_correct = rejection_total = rejection_correct = 0
    for sample in samples:
        image_path = Path(sample["image"])
        if not image_path.is_absolute():
            image_path = dataset_path.parent / image_path
        image = cv2.imread(str(image_path.resolve()), cv2.IMREAD_COLOR)
        if image is None or image.size == 0:
            parser.error(f"Cannot decode evaluation image: {image_path}")
        started = perf_counter()
        result = detector.predict_image(image, confidence=0.01, image_size=args.image_size)
        latencies.append((perf_counter() - started) * 1000)
        boxes = result.boxes
        predictions = []
        if boxes is not None:
            predictions = list(zip(
                (int(value) for value in boxes.cls.cpu().tolist()),
                (float(value) for value in boxes.conf.cpu().tolist()),
                (tuple(float(coordinate) for coordinate in value)
                 for value in boxes.xyxyn.cpu().tolist()),
            ))
        ground_truth = sample.get("detections", [])
        matched_gt = set()
        for class_id, confidence, bbox in sorted(predictions, key=lambda item: item[1], reverse=True):
            best_index = None
            best_iou = 0.0
            for index, truth in enumerate(ground_truth):
                if index in matched_gt or int(truth["class_id"]) != class_id:
                    continue
                overlap = iou(bbox, tuple(float(v) for v in truth["bbox"]))
                if overlap > best_iou:
                    best_index, best_iou = index, overlap
            matched = best_index is not None and best_iou >= args.iou
            if matched:
                matched_gt.add(best_index)
            records_by_class[class_id].append((confidence, matched))
            all_records.append((confidence, matched))
        for truth in ground_truth:
            gt_by_class[int(truth["class_id"])] += 1

        expected_sku = sample.get("expected_sku")
        expected_state = sample.get("expected_identity_status")
        predicted_classes = [item[0] for item in sorted(predictions, key=lambda item: item[1], reverse=True)]
        predicted_skus = [sku_by_class[item] for item in predicted_classes if item in sku_by_class]
        if expected_sku:
            identity_total += 1
            identity_correct += int(bool(predicted_skus) and predicted_skus[0] == expected_sku)
        if expected_state in {"unknown", "ambiguous"}:
            rejection_total += 1
            rejection_correct += int(not predicted_skus)

    tp = sum(int(item[1]) for item in all_records)
    fp = len(all_records) - tp
    total_gt = sum(gt_by_class.values())
    fn = total_gt - tp
    per_class_ap = {
        str(class_id): average_precision(records_by_class[class_id], count)
        for class_id, count in sorted(gt_by_class.items())
    }
    measured_ap = [value for value in per_class_ap.values() if value is not None]
    threshold_scores = []
    for threshold in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
        threshold_tp = sum(int(matched) for confidence, matched in all_records
                           if confidence >= threshold)
        threshold_fp = sum(int(not matched) for confidence, matched in all_records
                           if confidence >= threshold)
        threshold_fn = total_gt - threshold_tp
        precision = threshold_tp / max(threshold_tp + threshold_fp, 1)
        recall = threshold_tp / max(threshold_tp + threshold_fn, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-12)
        threshold_scores.append({"threshold": threshold, "precision": precision,
                                 "recall": recall, "f1": f1})
    report = {
        "dataset": str(dataset_path),
        "samples": len(samples),
        "model_sha256": reviewed_manifest.sha256,
        "device": detector.actual_device,
        "detection": {
            "iou_threshold": args.iou,
            "precision": tp / max(tp + fp, 1) if total_gt else None,
            "recall": tp / max(tp + fn, 1) if total_gt else None,
            "map50": mean(measured_ap) if measured_ap else None,
            "per_class_ap50": per_class_ap,
            "threshold_calibration": threshold_scores,
        },
        "identity": {
            "top1_accuracy": identity_correct / identity_total if identity_total else None,
            "topk_accuracy": None,
            "unknown_ambiguous_rejection_accuracy": (
                rejection_correct / rejection_total if rejection_total else None
            ),
            "note": "Top-k requires an embedding retrieval adapter and labeled catalog candidates.",
        },
        "tracking": {
            "duplicate_counting_error": None,
            "note": "Requires labeled video track/count ground truth; image samples cannot measure it.",
        },
        "performance": {
            "mean_latency_ms": mean(latencies),
            "p95_latency_ms": percentile(latencies, 0.95),
            "throughput_images_per_second": 1000 / mean(latencies),
            "peak_gpu_memory_mb": (
                torch.cuda.max_memory_allocated() / 1024 / 1024
                if detector.cuda_available else None
            ),
        },
    }
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
