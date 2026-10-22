"""Real local inference on an image; reads catalog only, never changes inventory.

Run from backend using the project's virtual environment:
python -m scripts.test_product_evidence --image path/to/product.jpg
Pass --florence-model ../models/florence-2-base --trust-florence-code to test
an explicitly trusted, complete local Florence snapshot even if disabled in .env.
"""
import argparse
import json
import time
from pathlib import Path
import cv2
from app.core.config import settings
from app.cv.detectors import UltralyticsYOLODetector
from app.cv.identity_evidence import IdentityEvidenceRuntime
from app.services.product_identity import ProductIdentityService, IdentityEvidence
from app.database import SessionLocal
from app.models.product import Product


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--florence-model")
    parser.add_argument("--trust-florence-code", action="store_true")
    args = parser.parse_args()
    image = cv2.imread(str(Path(args.image).resolve()))
    if image is None:
        parser.error("Image could not be opened")
    config = settings.model_copy()
    if args.florence_model:
        config.CV_FLORENCE_ENABLED = True
        config.CV_FLORENCE_MODEL_PATH = str(Path(args.florence_model).resolve())
        config.CV_FLORENCE_TRUST_REMOTE_CODE = args.trust_florence_code
        config.CV_FLORENCE_ALLOW_REMOTE_DOWNLOAD = False
    runtime = IdentityEvidenceRuntime(config)
    result = {"inventory_changed": False, "providers": {}, "detections": []}
    for name, provider, run in [
        ("ocr", runtime.ocr, lambda: runtime.ocr.extract(image)),
        ("florence", runtime.florence, lambda: runtime.florence.describe(image)),
    ]:
        started = time.perf_counter()
        if not provider.enabled:
            result["providers"][name] = {"status": "disabled"}
            continue
        try:
            value = run()
            result["providers"][name] = {"status": "passed", "output": vars(value), "seconds": round(time.perf_counter()-started, 2)}
        except Exception as exc:
            result["providers"][name] = {"status": "failed", "error_type": type(exc).__name__}
    detector = UltralyticsYOLODetector(config.CV_MODEL_PATH, config.CV_MODEL_MANIFEST, config.CV_DEVICE,
        iou_threshold=0.5, max_detections=100, default_image_size=640)
    prediction = detector.predict_image(image, confidence=0.4, image_size=640)
    with SessionLocal() as db:
        service = ProductIdentityService(db, config.CV_IDENTITY_MIN_CONFIDENCE)
        products = tuple(db.query(Product).all())
        skus = {item.class_id: item.sku for item in detector.manifest.classes} if detector.manifest else {}
        for box in prediction.boxes:
            label = prediction.names[int(box.cls.item())]
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            crop = image[max(0,y1):min(image.shape[0],y2), max(0,x1):min(image.shape[1],x2)]
            evidence = runtime.extract(crop, products)
            # Explicit smoke test exercises Florence on every detection, regardless of production policy.
            if runtime.florence.enabled:
                evidence = runtime.add_florence(evidence, crop)
            identity = service.identify(IdentityEvidence(
                detector_label=label, detector_confidence=float(box.conf.item()),
                manifest_sku=skus.get(int(box.cls.item())),
                ocr_tokens=evidence.ocr.tokens, ocr_confidence=evidence.ocr.confidence,
                retrieval_scores=evidence.retrieval.scores,
                florence_description=evidence.florence.description, provider_errors=evidence.errors))
            result["detections"].append({"label": label, "status": identity.status.value, "product_id": identity.product_id, "evidence": identity.evidence})
    print(json.dumps(result, indent=2))
    if any(p["status"] == "failed" for p in result["providers"].values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
