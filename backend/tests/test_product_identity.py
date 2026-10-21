from __future__ import annotations

import os

from app.database import SessionLocal
from app.models.product import Product
from app.services.product_identity import (
    IdentityEvidence,
    IdentityStatus,
    ProductIdentityService,
    category_for,
)


def _product(name: str, **values) -> Product:
    return Product(
        sku=f"identity-{os.urandom(5).hex()}",
        name=name,
        low_stock_threshold=2,
        reorder_point=5,
        **values,
    )


def test_category_rules_cover_representative_grocery_labels():
    assert category_for("LU Oreo Biscuit 19gm") == "biscuits_bakery"
    assert category_for("Lays Masala 34gm") == "chips_snacks"
    assert category_for("Fresher Guava Nectar 500ml") == "juice_beverages"
    assert category_for("unrecognized object") is None


def test_identity_requires_unique_catalog_evidence():
    with SessionLocal() as db:
        exact = _product(
            "Lays Masala 34gm",
            brand="Lays",
            category="chips_snacks",
            variant="Masala",
            package_size="34 gm",
            barcode=f"890{os.urandom(5).hex()}",
        )
        db.add(exact)
        db.commit()
        result = ProductIdentityService(db, 0.65).identify(
            IdentityEvidence("Lays Masala 34gm", 0.91)
        )
        assert result.status == IdentityStatus.IDENTIFIED
        assert result.product_id == exact.id
        assert result.brand == "Lays"

        weak = ProductIdentityService(db, 0.95).identify(
            IdentityEvidence("Lays Masala 34gm", 0.80)
        )
        assert weak.status == IdentityStatus.CATEGORY_ONLY
        assert weak.product_id is None and weak.brand is None


def test_unknown_and_ambiguous_are_explicit():
    with SessionLocal() as db:
        unknown = ProductIdentityService(db, 0.65).identify(
            IdentityEvidence("unseen grocery object", 0.99)
        )
        assert unknown.status == IdentityStatus.UNKNOWN
        db.add_all([_product("Duplicate label"), _product("Duplicate label")])
        db.commit()
        ambiguous = ProductIdentityService(db, 0.65).identify(
            IdentityEvidence("Duplicate label", 0.99)
        )
        assert ambiguous.status == IdentityStatus.AMBIGUOUS
        assert ambiguous.product_id is None


def test_validated_catalog_barcode_can_resolve_identity():
    barcode = f"890{os.urandom(5).hex()}"
    with SessionLocal() as db:
        product = _product("Barcode product", barcode=barcode, category="packaged_staples")
        db.add(product)
        db.commit()
        result = ProductIdentityService(db, 0.95).identify(
            IdentityEvidence("generic package", 0.40, barcode=barcode)
        )
        assert result.status == IdentityStatus.IDENTIFIED
        assert result.product_id == product.id


def test_device_auto_falls_back_and_explicit_cuda_fails_closed(monkeypatch):
    import torch
    from app.cv.detectors import resolve_device

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert resolve_device("auto") == ("cpu", False)
    try:
        resolve_device("cuda:0")
    except ValueError as exc:
        assert "cannot access an NVIDIA GPU" in str(exc)
    else:
        raise AssertionError("Explicit unavailable CUDA device was accepted")


def test_model_health_is_authenticated_and_read_only(client, auth_headers):
    response = client.get("/api/v1/video-jobs/model-health", headers=auth_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["detector"] == "ultralytics-yolov8"
    assert payload["actual_device"] in {"cpu", "cuda:0", "unavailable"}
    assert "model_path" in payload and "cuda_available" in payload
