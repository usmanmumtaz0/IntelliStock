from __future__ import annotations

import os

import numpy as np

from app.cv.identity_evidence import (
    EnrichedIdentityEvidence,
    FlorenceEvidence,
    IdentityEvidenceRuntime,
    crop_detection,
    parse_florence_output,
    parse_paddle_output,
)
from app.database import SessionLocal
from app.models.product import Product
from app.services.product_identity import IdentityEvidence, IdentityStatus, ProductIdentityService


def _product(name: str, **values) -> Product:
    return Product(
        sku=f"evidence-{os.urandom(5).hex()}",
        name=name,
        low_stock_threshold=2,
        reorder_point=5,
        **values,
    )


def test_paddle_output_parser_supports_current_and_legacy_shapes():
    current = parse_paddle_output({
        "rec_texts": ["Lays", "Masala 34 gm"],
        "rec_scores": [0.97, 0.91],
    })
    assert current.tokens == ("Lays", "Masala 34 gm")
    assert 0.93 < current.confidence < 0.95

    legacy = parse_paddle_output([
        [[[0, 0], [1, 0], [1, 1], [0, 1]], ("Lays", 0.96)],
        [[[0, 0], [1, 0], [1, 1], [0, 1]], ("Masala", 0.90)],
    ])
    assert legacy.tokens == ("Lays", "Masala")


def test_ocr_and_visual_consensus_identifies_one_catalog_product():
    with SessionLocal() as db:
        marker = os.urandom(4).hex()
        product = _product(
            f"Aurum {marker} Masala 34gm", brand=f"Aurum {marker}", variant="Masala",
            package_size="34 gm", category="chips_snacks",
        )
        other = _product("Surf Excel 500gm", brand="Surf Excel")
        db.add_all([product, other])
        db.commit()
        result = ProductIdentityService(db, 0.65).identify(IdentityEvidence(
            detector_label="snack packet",
            detector_confidence=0.78,
            ocr_tokens=("Aurum", marker, "Masala", "34 gm"),
            ocr_confidence=0.97,
            retrieval_scores=((product.id, 0.94), (other.id, 0.40)),
        ))
        assert result.status == IdentityStatus.IDENTIFIED
        assert result.product_id == product.id
        assert result.evidence["method"] == "ocr_visual_consensus"


def test_conflicting_strong_ocr_and_visual_evidence_requires_review():
    with SessionLocal() as db:
        marker = os.urandom(4).hex()
        lays = _product(
            f"Aurum {marker} Masala 34gm", brand=f"Aurum {marker}", variant="Masala"
        )
        surf = _product("Surf Excel 500gm", brand="Surf Excel")
        db.add_all([lays, surf])
        db.commit()
        result = ProductIdentityService(db, 0.65).identify(IdentityEvidence(
            detector_label="package",
            detector_confidence=0.82,
            ocr_tokens=("Aurum", marker, "Masala", "34 gm"),
            ocr_confidence=0.98,
            retrieval_scores=((surf.id, 0.96), (lays.id, 0.50)),
        ))
        assert result.status == IdentityStatus.AMBIGUOUS
        assert result.product_id is None
        assert result.evidence["method"] == "conflicting_ocr_and_visual"


def test_disabled_evidence_runtime_has_no_optional_dependency_requirement(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "CV_OCR_ENABLED", False)
    monkeypatch.setattr(settings, "CV_EMBEDDING_ENABLED", False)
    monkeypatch.setattr(settings, "CV_FLORENCE_ENABLED", False)
    runtime = IdentityEvidenceRuntime(settings)
    evidence = runtime.extract(np.zeros((20, 20, 3), dtype=np.uint8), [])
    assert evidence.ocr.tokens == ()
    assert evidence.retrieval.scores == ()


def test_detection_crop_is_clamped_to_frame():
    frame = np.zeros((20, 30, 3), dtype=np.uint8)
    crop = crop_detection(frame, (-10, -5, 40, 25))
    assert crop.shape == frame.shape

def test_florence_output_parser_supports_caption_and_label_shapes():
    caption = parse_florence_output(
        {"<DETAILED_CAPTION>": "A Lays Masala 34 gm packet"},
        "<DETAILED_CAPTION>",
    )
    assert caption.description == "A Lays Masala 34 gm packet"
    assert caption.task == "<DETAILED_CAPTION>"

    labels = parse_florence_output(
        {"<DENSE_REGION_CAPTION>": {"labels": ["Lays", "Masala"]}},
        "<DENSE_REGION_CAPTION>",
    )
    assert labels.description == "Lays Masala"


def test_florence_policy_is_conditional_and_missing_weights_fail_open(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "CV_FLORENCE_ENABLED", True)
    monkeypatch.setattr(settings, "CV_FLORENCE_MODEL_PATH", "")
    monkeypatch.setattr(settings, "CV_FLORENCE_ALLOW_REMOTE_DOWNLOAD", False)
    monkeypatch.setattr(settings, "CV_FLORENCE_POLICY", "ambiguous_or_low_confidence")
    runtime = IdentityEvidenceRuntime(settings)
    assert runtime.should_use_florence("identified", 0.95) is False
    assert runtime.should_use_florence("ambiguous", 0.95) is True
    result = runtime.add_florence(
        EnrichedIdentityEvidence(), np.zeros((20, 20, 3), dtype=np.uint8)
    )
    assert result.florence == FlorenceEvidence()
    assert result.errors == ("florence_unavailable",)
    health = runtime.health()["florence"]
    assert health["enabled"] is True
    assert health["loaded"] is False
    assert health["remote_download_allowed"] is False


def test_florence_always_policy_runs_for_confident_matches_and_requires_weights(tmp_path):
    from app.core.config import settings
    config = settings.model_copy(update={"CV_FLORENCE_ENABLED": True,
        "CV_FLORENCE_POLICY": "always", "CV_FLORENCE_MODEL_PATH": str(tmp_path)})
    runtime = IdentityEvidenceRuntime(config)
    assert runtime.should_use_florence("identified", 0.99) is True
    (tmp_path / "config.json").write_text("{}")
    assert runtime.florence.health()["model_present"] is False
    (tmp_path / "model.safetensors").write_bytes(b"test-fixture")
    assert runtime.florence.health()["model_present"] is True
    runtime.florence.enabled = False
    assert runtime.should_use_florence("identified", 0.99) is False


def test_florence_caption_preserves_more_than_an_ocr_token():
    caption = "A product with readable packaging. " * 12
    result = parse_florence_output({"<DETAILED_CAPTION>": caption}, "<DETAILED_CAPTION>")
    assert result.description == caption.strip()
    assert parse_florence_output(None, "<DETAILED_CAPTION>").description is None
