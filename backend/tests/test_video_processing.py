from __future__ import annotations

import os

import numpy as np

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.product import Product
from app.models.video_job import VideoDetection, VideoFrame, VideoJobStatus, VideoProcessingJob, VideoSourceKind
from app.services import video_processing
from app.services.video_processing import FrameSample, process_video_job
from app.services.video_storage import resolve_storage_key, storage_queue_stage
from app.api.video_jobs import _validate_camera_source
from app.workers.video_jobs import claim_next_job


def _user(role=UserRole.STAFF):
    with SessionLocal() as db:
        user = User(email=f"video-{os.urandom(6).hex()}@test.local",
                    username=f"video-{os.urandom(6).hex()}",
                    hashed_password=hash_password("video-test-password"), role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_access_token(user_id=user.id, username=user.username,
                                    email=user.email, role=user.role.value)
        return user.id, {"Authorization": f"Bearer {token}"}


def test_storage_keys_remain_inside_private_root(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "VIDEO_STORAGE_ROOT", str(tmp_path))
    assert resolve_storage_key("job/source.mp4").is_relative_to(tmp_path)
    for key in ("../secret.mp4", "job/../../secret.mp4", str(tmp_path / "absolute.mp4")):
        try:
            resolve_storage_key(key)
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe key was accepted: {key}")


def test_local_webcam_sources_are_bounded_and_explicit():
    _validate_camera_source("webcam://0")
    for source in ("webcam://10", "webcam://0?option=unsafe", "device://0"):
        try:
            _validate_camera_source(source)
        except Exception as exc:
            assert getattr(exc, "status_code", None) == 422
        else:
            raise AssertionError(f"invalid local camera source accepted: {source}")


def test_upload_validation_and_private_job_access(client, monkeypatch, tmp_path):
    owner_id, owner = _user()
    _other_id, other = _user()
    monkeypatch.setattr(settings, "VIDEO_STORAGE_ROOT", str(tmp_path))

    with SessionLocal() as db:
        jobs_before = db.query(VideoProcessingJob).count()
    rejected = client.post("/api/v1/video-jobs", headers=owner,
                           files={"video": ("payload.txt", b"not video", "text/plain")})
    assert rejected.status_code == 415
    with SessionLocal() as db:
        assert db.query(VideoProcessingJob).count() == jobs_before

    monkeypatch.setattr("app.api.video_jobs._inspect_video", lambda _path: (30.0, 90, 3000))
    accepted = client.post(
        "/api/v1/video-jobs", headers=owner,
        files={"video": ("aisle.mp4", b"validated by test double", "video/mp4")},
        data={"sample_interval_seconds": "0.5", "max_frames": "12"},
    )
    assert accepted.status_code == 202, accepted.text
    payload = accepted.json()
    assert payload["owner_user_id"] == owner_id
    assert payload["status"] == "queued"
    assert "storage_key" not in payload and "source_url" not in payload
    assert client.get(f"/api/v1/video-jobs/{payload['id']}", headers=other).status_code == 404
    assert client.get(f"/api/v1/video-jobs/{payload['id']}", headers=owner).status_code == 200

    import cv2
    ok, encoded = cv2.imencode(".png", np.zeros((32, 48, 3), dtype=np.uint8))
    assert ok
    picture = client.post(
        "/api/v1/video-jobs/images", headers=owner,
        files={"image": ("shelf.png", encoded.tobytes(), "image/png")},
        data={"confidence_threshold": "0.5"},
    )
    assert picture.status_code == 202, picture.text
    image_job = picture.json()
    assert image_job["total_frames"] == 1
    assert image_job["tracking_enabled"] is False
    assert image_job["summary"]["source_width"] == 48
    assert "storage_key" not in image_job

    ok, jpeg = cv2.imencode(".jpg", np.zeros((24, 36, 3), dtype=np.uint8))
    assert ok
    spaced_picture = client.post(
        "/api/v1/video-jobs/images", headers=owner,
        files={"image": ("download (2).jpg", jpeg.tobytes(), "image/jpeg")},
    )
    assert spaced_picture.status_code == 202, spaced_picture.text
    with SessionLocal() as db:
        row = db.get(VideoProcessingJob, spaced_picture.json()["id"])
        assert row.original_filename == "download (2).jpg"
        assert resolve_storage_key(row.storage_key).is_file()


def test_frame_sampler_reads_a_picture_once(tmp_path):
    import cv2
    path = tmp_path / "shelf.webp"
    assert cv2.imwrite(str(path), np.zeros((40, 60, 3), dtype=np.uint8))
    samples = list(video_processing.VideoFrameSampler(str(path), 1, 10, 10))
    assert len(samples) == 1
    assert samples[0].timestamp_ms == 0
    assert samples[0].frame.shape == (40, 60, 3)


def test_frame_sampler_reads_picture_with_spaces_and_parentheses(tmp_path):
    import cv2
    path = tmp_path / "download (2).jpg"
    assert cv2.imwrite(str(path), np.zeros((20, 30, 3), dtype=np.uint8))
    samples = list(video_processing.VideoFrameSampler(str(path), 1, 10, 10))
    assert len(samples) == 1
    assert samples[0].frame.shape == (20, 30, 3)


def test_missing_image_source_has_actionable_media_specific_failure(monkeypatch, tmp_path):
    owner_id, _headers = _user()
    monkeypatch.setattr(settings, "VIDEO_STORAGE_ROOT", str(tmp_path))
    with SessionLocal() as db:
        job = VideoProcessingJob(
            owner_user_id=owner_id,
            source_kind=VideoSourceKind.UPLOAD,
            storage_key="missing/source.jpg",
            content_type="image/jpeg",
            sample_interval_seconds=1,
            max_frames=1,
            confidence_threshold=.4,
            image_size=640,
            tracking_enabled=False,
        )
        db.add(job)
        db.commit()
        job_id = job.id

    with SessionLocal() as db:
        process_video_job(db, job_id)
    with SessionLocal() as db:
        failed = db.get(VideoProcessingJob, job_id)
        assert failed.status == VideoJobStatus.FAILED
        assert "Uploaded image source is unavailable" in failed.error_message
        assert "VIDEO_STORAGE_ROOT" in failed.error_message
        assert str(tmp_path) not in failed.error_message


def test_failed_job_retry_preserves_source_and_clears_partial_evidence(
    client, monkeypatch, tmp_path
):
    owner_id, owner = _user()
    monkeypatch.setattr(settings, "VIDEO_STORAGE_ROOT", str(tmp_path))
    source = tmp_path / "job-with-partial-evidence" / "source.jpg"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"preserved source")
    with SessionLocal() as db:
        job = VideoProcessingJob(
            owner_user_id=owner_id,
            source_kind=VideoSourceKind.UPLOAD,
            status=VideoJobStatus.FAILED,
            stage="failed",
            storage_key="job-with-partial-evidence/source.jpg",
            content_type="image/jpeg",
            sample_interval_seconds=1,
            max_frames=1,
            confidence_threshold=.4,
            image_size=640,
            tracking_enabled=False,
            frames_processed=1,
            detection_instances=1,
            frames_with_detections=1,
            error_message="Previous failure",
        )
        db.add(job)
        db.flush()
        frame = VideoFrame(
            job_id=job.id, sequence=0, source_frame_index=0, timestamp_ms=0,
            width=10, height=10, inference_ms=1, detection_count=1,
        )
        db.add(frame)
        db.flush()
        db.add(VideoDetection(
            job_id=job.id, frame_id=frame.id, class_id=0, class_name="old",
            confidence=.5, track_id=None, x1=0, y1=0, x2=1, y2=1,
            normalized_bbox={"x1": 0, "y1": 0, "x2": .1, "y2": .1},
        ))
        db.commit()
        job_id = job.id

    response = client.post(f"/api/v1/video-jobs/{job_id}/retry", headers=owner)
    assert response.status_code == 202, response.text
    assert response.json()["status"] == "queued"
    assert response.json()["stage"] == "queued"
    assert source.is_file()
    with SessionLocal() as db:
        retried = db.get(VideoProcessingJob, job_id)
        assert retried.frames_processed == 0
        assert retried.detection_instances == 0
        assert retried.error_message is None
        assert db.query(VideoFrame).filter_by(job_id=job_id).count() == 0
        assert db.query(VideoDetection).filter_by(job_id=job_id).count() == 0

    repeated = client.post(f"/api/v1/video-jobs/{job_id}/retry", headers=owner)
    assert repeated.status_code == 409


def test_worker_claims_only_jobs_for_its_media_volume(monkeypatch, tmp_path):
    owner_id, _headers = _user()
    monkeypatch.setattr(settings, "VIDEO_STORAGE_ROOT", str(tmp_path))
    with SessionLocal() as db:
        local = VideoProcessingJob(
            owner_user_id=owner_id, source_kind=VideoSourceKind.UPLOAD,
            status=VideoJobStatus.CANCELLED, stage=storage_queue_stage(),
            storage_key="local/source.jpg", sample_interval_seconds=1,
            max_frames=1, confidence_threshold=.4, image_size=640,
            tracking_enabled=False,
        )
        remote = VideoProcessingJob(
            owner_user_id=owner_id, source_kind=VideoSourceKind.UPLOAD,
            status=VideoJobStatus.CANCELLED, stage="storage_queued:remote-node",
            storage_key="remote/source.jpg", sample_interval_seconds=1,
            max_frames=1, confidence_threshold=.4, image_size=640,
            tracking_enabled=False,
        )
        db.add_all([remote, local])
        db.commit()
        local_id, remote_id = local.id, remote.id

    with SessionLocal() as db:
        assert claim_next_job(db) == local_id
    with SessionLocal() as db:
        assert db.get(VideoProcessingJob, local_id).status == VideoJobStatus.PROCESSING
        assert db.get(VideoProcessingJob, remote_id).status == VideoJobStatus.CANCELLED


class _Values:
    def __init__(self, value): self.value = value
    def cpu(self): return self
    def tolist(self): return self.value


class _Boxes:
    cls = _Values([2])
    conf = _Values([0.91])
    xyxy = _Values([[10, 20, 80, 90]])
    xyxyn = _Values([[0.1, 0.2, 0.8, 0.9]])
    id = _Values([7])
    def __len__(self): return 1


class _Result:
    boxes = _Boxes()
    names = {2: "sample-product"}


class _Sampler:
    fps = 30.0
    total_frames = 30
    duration_ms = 1000
    def __init__(self, *_args, **_kwargs): pass
    def __iter__(self):
        yield FrameSample(0, 0, 0, np.zeros((100, 100, 3), dtype=np.uint8))


def test_worker_persists_timestamped_detection_evidence(monkeypatch, tmp_path):
    owner_id, _headers = _user()
    monkeypatch.setattr(settings, "VIDEO_STORAGE_ROOT", str(tmp_path))
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    with SessionLocal() as db:
        job = VideoProcessingJob(owner_user_id=owner_id, source_kind=VideoSourceKind.UPLOAD,
                                 storage_key="source.mp4", sample_interval_seconds=1,
                                 max_frames=5, confidence_threshold=.4, image_size=640,
                                 tracking_enabled=True)
        db.add(job)
        db.commit()
        job_id = job.id

    monkeypatch.setattr(video_processing, "VideoFrameSampler", _Sampler)
    monkeypatch.setattr(video_processing.model_service, "_load", lambda: None)
    monkeypatch.setattr(video_processing.model_service, "reset_tracking", lambda: None)
    monkeypatch.setattr(video_processing.model_service, "infer",
                        lambda *_args, **_kwargs: (_Result(), np.zeros((100, 100, 3), dtype=np.uint8)))
    monkeypatch.setattr(video_processing.model_service, "_manifest", None)
    monkeypatch.setattr(video_processing, "_save_annotated", lambda *_args: "annotated/frame.jpg")

    with SessionLocal() as db:
        process_video_job(db, job_id)
    with SessionLocal() as db:
        job = db.get(VideoProcessingJob, job_id)
        frame = db.query(VideoFrame).filter_by(job_id=job_id).one()
        detection = db.query(VideoDetection).filter_by(job_id=job_id).one()
        assert job.status == VideoJobStatus.COMPLETED
        assert job.frames_processed == 1 and job.detection_instances == 1
        assert job.unique_tracked_objects == 1
        assert job.summary["inventory_effect"] == "review_only"
        assert frame.timestamp_ms == 0
        assert detection.class_name == "sample-product" and detection.track_id == 7
        assert detection.normalized_bbox == {"x1": .1, "y1": .2, "x2": .8, "y2": .9}
        assert detection.identity_status == "unknown"
        assert job.summary["identity_states"] == {"unknown": 1}


def test_worker_fuses_optional_ocr_evidence_without_changing_inventory(monkeypatch, tmp_path):
    from app.cv.identity_evidence import EnrichedIdentityEvidence, OCREvidence

    owner_id, _headers = _user()
    marker = os.urandom(4).hex()
    monkeypatch.setattr(settings, "VIDEO_STORAGE_ROOT", str(tmp_path))
    (tmp_path / "source.mp4").write_bytes(b"source")
    with SessionLocal() as db:
        product = Product(
            sku=f"ocr-{marker}", name=f"Aurum {marker} Masala 34gm",
            brand=f"Aurum {marker}", variant="Masala", package_size="34 gm",
            category="chips_snacks", low_stock_threshold=2, reorder_point=4,
        )
        job = VideoProcessingJob(
            owner_user_id=owner_id, source_kind=VideoSourceKind.UPLOAD,
            storage_key="source.mp4", sample_interval_seconds=1, max_frames=1,
            confidence_threshold=.4, image_size=640, tracking_enabled=False,
        )
        db.add_all([product, job])
        db.commit()
        job_id, product_id = job.id, product.id

    class _EvidenceRuntime:
        enabled = True

        @staticmethod
        def extract(_crop, _products):
            return EnrichedIdentityEvidence(ocr=OCREvidence(
                tokens=("Aurum", marker, "Masala", "34 gm"), confidence=.99
            ))

        @staticmethod
        def should_use_florence(_status, _confidence):
            return False

        @staticmethod
        def add_florence(evidence, _crop):
            return evidence

    monkeypatch.setattr(video_processing, "VideoFrameSampler", _Sampler)
    monkeypatch.setattr(video_processing.model_service, "_load", lambda: None)
    monkeypatch.setattr(video_processing.model_service, "reset_tracking", lambda: None)
    monkeypatch.setattr(
        video_processing.model_service, "infer",
        lambda *_args, **_kwargs: (_Result(), np.zeros((100, 100, 3), dtype=np.uint8)),
    )
    monkeypatch.setattr(video_processing.model_service, "_manifest", None)
    monkeypatch.setattr(video_processing, "_save_annotated", lambda *_args: "annotated/frame.jpg")
    monkeypatch.setattr(video_processing, "identity_evidence_runtime", _EvidenceRuntime())

    with SessionLocal() as db:
        process_video_job(db, job_id)
    with SessionLocal() as db:
        job = db.get(VideoProcessingJob, job_id)
        detection = db.query(VideoDetection).filter_by(job_id=job_id).one()
        assert job.status == VideoJobStatus.COMPLETED
        assert job.summary["identity_evidence"] == {"ocr": 1}
        assert job.summary["inventory_effect"] == "review_only"
        assert detection.product_id == product_id
        assert detection.identity_status == "identified"
        assert detection.identity_evidence["method"] == "paddleocr_catalog_match"


def test_manager_can_resolve_owned_detection_without_changing_inventory(client):
    owner_id, manager = _user(UserRole.MANAGER)
    _staff_id, staff = _user(UserRole.STAFF)
    with SessionLocal() as db:
        product = Product(sku=f"review-{os.urandom(5).hex()}", name="Reviewed product",
                          brand="Test brand", category="chips_snacks",
                          low_stock_threshold=2, reorder_point=4)
        db.add(product)
        db.flush()
        job = VideoProcessingJob(owner_user_id=owner_id, source_kind=VideoSourceKind.UPLOAD,
                                 sample_interval_seconds=1, max_frames=1,
                                 confidence_threshold=.4, image_size=640,
                                 tracking_enabled=False)
        db.add(job)
        db.flush()
        frame = VideoFrame(job_id=job.id, sequence=0, source_frame_index=0,
                           timestamp_ms=0, width=100, height=100, inference_ms=2,
                           detection_count=1)
        db.add(frame)
        db.flush()
        detection = VideoDetection(
            job_id=job.id, frame_id=frame.id, class_id=99,
            class_name="Unknown snack", confidence=.72, track_id=None,
            x1=1, y1=1, x2=50, y2=50,
            normalized_bbox={"x1": .01, "y1": .01, "x2": .5, "y2": .5},
            identity_status="category_only", identity_confidence=.72,
            category="chips_snacks",
        )
        db.add(detection)
        db.commit()
        detection_id, product_id = detection.id, product.id

    assert client.post(
        f"/api/v1/video-jobs/detections/{detection_id}/identify",
        headers=staff,
        json={"product_id": product_id},
    ).status_code == 403
    response = client.post(
        f"/api/v1/video-jobs/detections/{detection_id}/identify",
        headers=manager,
        json={"product_id": product_id},
    )
    assert response.status_code == 200, response.text
    assert response.json()["identity_status"] == "identified"
    assert response.json()["product_id"] == product_id
