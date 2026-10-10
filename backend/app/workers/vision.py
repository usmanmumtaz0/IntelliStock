"""Run one worker per camera: python -m app.workers.vision --help."""
import argparse
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from app.database import SessionLocal
from app.core.config import settings
from app.models import Camera, ShelfZone, Inventory, InventoryStatus, ZoneProductMapping, Product
from app.cv.model_artifact import verify_artifact, verify_model_metadata, verify_zone_mappings
from app.cv.runtime import ShelfPipeline, Zone, YOLOTracker, frame_healthy
from app.cv.capture import FrameSource
from app.services.reconciliation import ReconciliationEngine
from app.services.observation_window import get_observation_window
from app.services.camera_heartbeat import get_heartbeat_service
from app.services.outbox import enqueue

logger = logging.getLogger(__name__)


def camera_configuration_current(db, camera_id, revision):
    camera = db.get(Camera, camera_id)
    return bool(camera and camera.is_active and camera.updated_at == revision)


def load_zones(db, camera_id):
    zones = []
    for row in db.query(ShelfZone).filter_by(camera_id=camera_id).all():
        mappings = db.query(ZoneProductMapping).filter_by(zone_id=row.id).all()
        if not mappings:
            continue
        zones.append(Zone(row.id, json.loads(row.roi_polygon),
            {m.class_id: m.product_id for m in mappings},
            frozenset(m.class_id for m in mappings if m.allow_empty), row.detection_confidence_threshold))
    if not zones:
        raise ValueError("Configure shelf polygons and product mappings before starting CV")
    return zones


def apply_observations(db, camera_id, zones, observations, offline=False):
    """Missing observations invalidate consensus without overwriting trusted counts."""
    observed = {(z, p) for z, p, _, _ in observations}
    for zone in zones:
        for product_id in zone.products.values():
            if (zone.id, product_id) in observed:
                continue
            get_observation_window(camera_id, zone.id, product_id).clear()
            inv = db.query(Inventory).filter_by(zone_id=zone.id, product_id=product_id).first()
            state = InventoryStatus.CAMERA_OFFLINE if offline else InventoryStatus.DETECTION_UNCERTAIN
            if inv and inv.status != state:
                inv.status = state
                enqueue(db, "camera_offline" if offline else "detection_uncertain",
                        {"camera_id": camera_id, "zone_id": zone.id, "product_id": product_id})
    db.commit()
    results = []
    for zone_id, product_id, quantity, confidence in observations:
        results.append(ReconciliationEngine(db).reconcile_observation(
            camera_id, zone_id, product_id, quantity, confidence))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera-id", required=True)
    parser.add_argument("--model", default=settings.CV_MODEL_PATH, help="Trusted trained .pt file; defaults to CV_MODEL_PATH in .env")
    parser.add_argument("--manifest", default=settings.CV_MODEL_MANIFEST,
                        help="Reviewed model identity/class-to-SKU manifest JSON")
    parser.add_argument("--source", help="Override configured source with a local recorded video")
    parser.add_argument("--device", default=settings.CV_DEVICE)
    args = parser.parse_args()
    if not args.model:
        parser.error("Training pending: set CV_MODEL_PATH in .env or supply --model when trained weights are ready")
    if not args.manifest:
        parser.error("Set CV_MODEL_MANIFEST or supply --manifest before activating trained weights")
    manifest = verify_artifact(args.model, args.manifest)
    logging.basicConfig(level=logging.INFO)
    with SessionLocal() as db:
        camera = db.get(Camera, args.camera_id)
        if not camera or not camera.is_active:
            raise ValueError("Camera missing or disabled")
        zones = load_zones(db, camera.id)
        product_ids = {product_id for zone in zones for product_id in zone.products.values()}
        product_skus = {row.id: row.sku for row in db.query(Product).filter(Product.id.in_(product_ids)).all()}
        verify_zone_mappings(manifest, zones, product_skus)
        source = args.source or camera.source_url
        fps = camera.fps
        camera_revision = camera.updated_at
    if not source or fps <= 0:
        raise ValueError("A camera source and positive FPS are required")
    replay = Path(source).is_file() if "://" not in source else False
    tracker = YOLOTracker(args.model, args.device)
    verify_model_metadata(manifest, tracker.model)
    logger.info("Validated model version=%s sha256=%s", manifest.model_version, manifest.sha256)
    pipeline = ShelfPipeline(zones)
    capture = None
    sequence = 0
    try:
        while True:
            with SessionLocal() as db:
                if not camera_configuration_current(db, args.camera_id, camera_revision):
                    logger.warning("Camera disabled or configuration changed; restart the vision worker")
                    break
            if capture is None:
                capture = FrameSource(source, replay=replay)
            started = time.monotonic()
            ok, frame, captured = capture.read()
            if not ok:
                with SessionLocal() as db:
                    apply_observations(db, args.camera_id, zones, [], offline=True)
                pipeline.reset()
                capture.close()
                capture = None
                if replay:
                    break
                time.sleep(2)
                continue
            healthy = frame_healthy(frame)
            try:
                detections = tracker.detect(frame) if healthy else []
            except Exception:
                logger.warning("Inference failed; preserving last trusted quantities")
                detections, healthy = [], False
            observations = pipeline.observe(detections, sequence, captured, healthy=healthy)
            with SessionLocal() as db:
                # Disabled cameras stop the worker rather than continue writing.
                if not camera_configuration_current(db, args.camera_id, camera_revision):
                    break
                apply_observations(db, args.camera_id, zones, observations)
            try:
                get_heartbeat_service().record_heartbeat(args.camera_id)
            except Exception:
                logger.warning("Heartbeat unavailable; Redis must be restored")
            sequence += 1
            time.sleep(max(0, 1 / fps - (time.monotonic() - started)))
    except KeyboardInterrupt:
        pass
    finally:
        if capture is not None:
            capture.close()


if __name__ == "__main__":
    main()
