"""Validate operator-reviewed model identity before loading trusted checkpoints.

A checksum detects substitution, not malicious weights. Only load trusted files.
This module has no database, inference or network side effects.
"""
import hashlib
from pathlib import Path
from typing import Literal
from unittest.mock import patch

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ModelClass(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
    class_id: int = Field(ge=0)
    label: str = Field(min_length=1, max_length=255)
    # A reviewed checkpoint may be activated before catalog SKUs are mapped.
    # Empty means category/label evidence only and can never update inventory.
    sku: str = Field(default="", max_length=64)

    @field_validator("sku", mode="before")
    @classmethod
    def empty_or_non_whitespace_sku(cls, value):
        if isinstance(value, str) and value != "" and not value.strip():
            raise ValueError("SKU must be empty or contain a non-whitespace value")
        return value


class ModelManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True,
                              protected_namespaces=())
    schema_version: Literal[1]
    model_version: str = Field(min_length=1, max_length=100)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    task: Literal["detect"]
    classes: list[ModelClass] = Field(min_length=1, max_length=10000)

    @model_validator(mode="after")
    def unique_classes(self):
        for attribute in ("class_id", "label", "sku"):
            values = [getattr(item, attribute) for item in self.classes]
            if attribute == "sku":
                values = [value for value in values if value]
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate {attribute} in model manifest")
        return self


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_artifact(model_path, manifest_path):
    model = Path(model_path)
    if model.suffix.lower() != ".pt" or not model.is_file() or model.stat().st_size == 0:
        raise ValueError("Supply an existing nonempty trusted .pt checkpoint")
    manifest_file = Path(manifest_path)
    if not manifest_file.is_file() or manifest_file.stat().st_size > 2_000_000:
        raise ValueError("Supply a model manifest JSON file smaller than 2 MB")
    manifest = ModelManifest.model_validate_json(manifest_file.read_text(encoding="utf-8"))
    if file_sha256(model) != manifest.sha256:
        raise ValueError("Model SHA-256 differs from the reviewed manifest; activation refused")
    return manifest


def verify_model_metadata(manifest, model):
    if model.task != "detect":
        raise ValueError("Shelf counting requires a detection model")
    expected = {item.class_id: item.label for item in manifest.classes}
    if model.names != expected:
        raise ValueError("Model class IDs/names differ from the reviewed manifest")


def load_trusted_yolo_checkpoint(model_path):
    """Load an operator-configured Ultralytics checkpoint on PyTorch 2.6+.

    Ultralytics versions used by this project call ``torch.load`` without the
    new ``weights_only`` argument. Detection checkpoints contain model classes,
    so they require the legacy trusted-checkpoint mode. Callers must validate
    provenance/checksum before configuring the path; .pt files are executable
    pickle payloads and must never come from an untrusted upload.
    """
    import torch
    from ultralytics import YOLO

    original_load = torch.load

    def compatible_load(*args, **kwargs):
        kwargs.setdefault("weights_only", False)
        return original_load(*args, **kwargs)

    with patch.object(torch, "load", compatible_load):
        return YOLO(str(model_path))


def verify_zone_mappings(manifest, zones, product_skus):
    expected = {item.class_id: item.sku for item in manifest.classes if item.sku}
    for zone in zones:
        for class_id, product_id in zone.products.items():
            if class_id not in expected or product_skus.get(product_id) != expected[class_id]:
                raise ValueError("Shelf class-to-SKU mapping differs from the model manifest")
