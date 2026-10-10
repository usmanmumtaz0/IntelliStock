import hashlib
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.cv.model_artifact import (
    ModelManifest, verify_artifact, verify_model_metadata, verify_zone_mappings,
)
from app.cv.count_evaluation import evaluate_counts, read_counts


@pytest.fixture
def artifact(tmp_path):
    model = tmp_path / "trusted.pt"
    model.write_bytes(b"synthetic-test-not-a-model")
    data = {"schema_version": 1, "model_version": "test-run", "task": "detect",
            "sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
            "classes": [{"class_id": 0, "label": "milk", "sku": "MILK-1"}]}
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    return model, manifest, data


def test_checksum_verified_without_deserializing(artifact):
    model, path, _ = artifact
    manifest = verify_artifact(model, path)
    assert manifest.model_version == "test-run"
    model.write_bytes(b"changed")
    with pytest.raises(ValueError, match="SHA-256"):
        verify_artifact(model, path)


@pytest.mark.parametrize("field,value", [("class_id", True), ("class_id", -1), ("sku", " ")])
def test_invalid_manifest_classes(artifact, field, value):
    data = artifact[2]
    data["classes"][0][field] = value
    with pytest.raises(ValidationError):
        ModelManifest.model_validate(data)


def test_duplicate_classes_rejected(artifact):
    data = artifact[2]
    data["classes"].append(data["classes"][0].copy())
    with pytest.raises(ValidationError):
        ModelManifest.model_validate(data)


def test_metadata_and_sku_mismatch_rejected(artifact):
    manifest = verify_artifact(*artifact[:2])
    verify_model_metadata(manifest, SimpleNamespace(task="detect", names={0: "milk"}))
    for model in [SimpleNamespace(task="classify", names={0: "milk"}),
                  SimpleNamespace(task="detect", names={0: "other"})]:
        with pytest.raises(ValueError):
            verify_model_metadata(manifest, model)
    zones = [SimpleNamespace(products={0: "product-id"})]
    verify_zone_mappings(manifest, zones, {"product-id": "MILK-1"})
    with pytest.raises(ValueError, match="SKU"):
        verify_zone_mappings(manifest, zones, {"product-id": "WRONG-SKU"})


def test_worker_requires_manifest_before_db_or_model(monkeypatch):
    from app.core.config import settings
    from app.workers.vision import main
    monkeypatch.setattr(settings, "CV_MODEL_MANIFEST", "")
    monkeypatch.setattr("sys.argv", ["vision", "--camera-id", "unused", "--model", "pending.pt"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2


def test_counts_report_abstention_and_false_empty():
    truth = {("1", "shelf", "milk"): 3, ("2", "shelf", "milk"): 0,
             ("3", "shelf", "milk"): 2}
    predictions = {("1", "shelf", "milk"): 0, ("2", "shelf", "milk"): 1}
    report = evaluate_counts(truth, predictions)
    result = report["overall"]
    assert result["abstained_samples"] == 1
    assert result["coverage"] == pytest.approx(2 / 3)
    assert result["mae_on_predictions"] == 2
    assert result["signed_bias_on_predictions"] == -1
    assert result["false_empty_predictions"] == 1
    assert result["false_nonempty_predictions"] == 1
    assert report["acceptance"] == "not_assessed"
    assert report["by_sku"]["milk"] == result


def test_missing_predictions_never_count_as_correct_zero():
    result = evaluate_counts({("1", "z", "sku"): 0}, {})["overall"]
    assert result["coverage"] == 0
    assert result["mae_on_predictions"] is None
    assert result["exact_match_rate_on_predictions"] is None


def test_empty_truth_or_unpaired_prediction_rejected():
    with pytest.raises(ValueError):
        evaluate_counts({}, {})
    with pytest.raises(ValueError):
        evaluate_counts({("1", "z", "sku"): 0}, {("2", "z", "sku"): 0})


@pytest.mark.parametrize("rows", ["1,z,sku,-1\n", "1,z,sku,1.5\n", "1,z,sku,NaN\n",
                                  "1,z,sku,2\n1,z,sku,2\n", "1,z,sku\n", "1,z,sku,1,extra\n"])
def test_bad_count_csv_rejected(tmp_path, rows):
    path = tmp_path / "counts.csv"
    path.write_text("sample_id,zone_id,sku,quantity\n" + rows, encoding="utf-8")
    with pytest.raises(ValueError):
        read_counts(path)


def test_count_csv_accepts_bom_and_zero(tmp_path):
    path = tmp_path / "counts.csv"
    path.write_text("sample_id,zone_id,sku,quantity\n1,z,sku,0\n", encoding="utf-8-sig")
    assert read_counts(path) == {("1", "z", "sku"): 0}


def test_read_only_replay_warms_tracks_and_preserves_abstentions(monkeypatch):
    from datetime import datetime, timezone
    from scripts.replay_counts import collect_predictions
    from app.cv.runtime import Detection, Zone
    monkeypatch.setattr("scripts.replay_counts.frame_healthy", lambda frame: True)
    source = SimpleNamespace(read=lambda: (True, object(), datetime.now(timezone.utc)))
    tracker = SimpleNamespace(detect=lambda frame: [Detection(0, 1, 0.9, (0.2, 0.2, 0.4, 0.4))])
    zones = [Zone("z", [(0, 0), (1, 0), (1, 1), (0, 1)], {0: "milk"})]
    truth = {(str(i), "z", "milk"): 1 for i in range(3)}
    predictions, frames = collect_predictions(source, tracker, zones, truth, 3)
    assert frames == 3
    assert predictions == {("2", "z", "milk"): 1}
    assert evaluate_counts(truth, predictions)["overall"]["abstained_samples"] == 2


def test_replay_does_not_silently_score_unread_frames(monkeypatch):
    from scripts.replay_counts import collect_predictions
    source = SimpleNamespace(read=lambda: (False, None, None))
    with pytest.raises(ValueError, match="No video frames"):
        collect_predictions(source, None, [], {("0", "z", "sku"): 0}, 1)


def test_replay_config_requires_matching_labels(artifact):
    from scripts.replay_counts import ReplayConfig, replay_zones
    manifest = verify_artifact(*artifact[:2])
    config = ReplayConfig.model_validate({"zones": [{"zone_id": "z", "class_ids": [0],
        "polygon": [[0, 0], [1, 0], [1, 1], [0, 1]]}]})
    assert replay_zones(config, manifest, {("0", "z", "MILK-1"): 1})[0].products == {0: "MILK-1"}
    for truth in [{("0", "z", "wrong"): 1}, {("00", "z", "MILK-1"): 1}]:
        with pytest.raises(ValueError):
            replay_zones(config, manifest, truth)
