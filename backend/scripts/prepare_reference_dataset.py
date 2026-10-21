"""Validate labeled reference images and prevent exact train/validation leakage.

CSV columns: image,sku,split. ``split`` must be train, validation, or test.
Paths may be absolute or relative to the CSV file. This script never downloads,
copies, or relicenses images.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source = args.csv.resolve()
    records = []
    by_hash: dict[str, tuple[str, str]] = {}
    with source.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        required = {"image", "sku", "split"}
        if not reader.fieldnames or not required <= set(reader.fieldnames):
            parser.error("CSV must contain image, sku, and split columns")
        for row_number, row in enumerate(reader, start=2):
            split = row["split"].strip().lower()
            sku = row["sku"].strip()
            if split not in {"train", "validation", "test"} or not sku:
                parser.error(f"Invalid split or empty SKU on CSV row {row_number}")
            image = Path(row["image"].strip())
            if not image.is_absolute():
                image = source.parent / image
            image = image.resolve()
            if not image.is_file():
                parser.error(f"Image does not exist on CSV row {row_number}: {image}")
            import cv2

            decoded = cv2.imread(str(image), cv2.IMREAD_COLOR)
            if decoded is None or decoded.size == 0:
                parser.error(f"Image cannot be decoded on CSV row {row_number}: {image}")
            digest = file_hash(image)
            prior = by_hash.get(digest)
            if prior and prior[1] != split:
                parser.error(
                    f"Exact duplicate leaks across splits: {prior[0]} ({prior[1]}) and "
                    f"{image} ({split})"
                )
            by_hash[digest] = (str(image), split)
            records.append({
                "image": str(image),
                "sku": sku,
                "split": split,
                "sha256": digest,
                "width": int(decoded.shape[1]),
                "height": int(decoded.shape[0]),
            })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"schema_version": 1, "images": records}, indent=2),
                           encoding="utf-8")
    print(json.dumps({"images": len(records), "output": str(args.output.resolve())}))


if __name__ == "__main__":
    main()
