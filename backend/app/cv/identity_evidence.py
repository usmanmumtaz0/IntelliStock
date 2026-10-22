"""Optional OCR and visual-retrieval evidence for product identity.

The providers are lazy and local-first. Missing optional packages or weights never
turn an observation into truth and never fail a vision job; they leave the result
for catalog review instead.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import importlib.util
import json
import logging
import os
from pathlib import Path
from threading import RLock
from typing import Any, Iterable

import numpy as np

from app.models.product import Product

logger = logging.getLogger(__name__)


def configure_model_cache(cache_root: Path) -> None:
    cache_root.mkdir(parents=True, exist_ok=True)
    values = {
        "PADDLE_HOME": cache_root / "paddle",
        "PADDLE_PDX_CACHE_HOME": cache_root / "paddlex",
        "HF_HOME": cache_root / "huggingface",
    }
    for name, path in values.items():
        path.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault(name, str(path))
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")


@dataclass(frozen=True)
class OCREvidence:
    tokens: tuple[str, ...] = ()
    confidence: float = 0.0


@dataclass(frozen=True)
class RetrievalEvidence:
    scores: tuple[tuple[str, float], ...] = ()


@dataclass(frozen=True)
class FlorenceEvidence:
    description: str | None = None
    task: str | None = None


@dataclass(frozen=True)
class EnrichedIdentityEvidence:
    ocr: OCREvidence = field(default_factory=OCREvidence)
    retrieval: RetrievalEvidence = field(default_factory=RetrievalEvidence)
    florence: FlorenceEvidence = field(default_factory=FlorenceEvidence)
    errors: tuple[str, ...] = ()


def _clean_token(value: Any) -> str | None:
    text = " ".join(str(value).split()).strip()
    return text[:160] if text else None


def parse_paddle_output(result: Any) -> OCREvidence:
    """Normalize PaddleOCR v3 result objects and legacy nested list output."""
    pairs: list[tuple[str, float]] = []

    def add(text: Any, score: Any) -> None:
        token = _clean_token(text)
        if token is None:
            return
        try:
            confidence = max(0.0, min(1.0, float(score)))
        except (TypeError, ValueError):
            confidence = 0.0
        pairs.append((token, confidence))

    def visit(value: Any) -> None:
        if value is None:
            return
        if hasattr(value, "res"):
            visit(value.res)
            return
        if hasattr(value, "json") and not isinstance(value, (dict, list, tuple)):
            payload = value.json
            payload = payload() if callable(payload) else payload
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    payload = None
            visit(payload)
            return
        if isinstance(value, dict):
            texts = value.get("rec_texts")
            scores = value.get("rec_scores")
            if isinstance(texts, (list, tuple)):
                score_values = scores if isinstance(scores, (list, tuple, np.ndarray)) else []
                for index, text in enumerate(texts):
                    add(text, score_values[index] if index < len(score_values) else 0.0)
                return
            for key in ("res", "result", "data"):
                if key in value:
                    visit(value[key])
            return
        if isinstance(value, (list, tuple)):
            # Legacy shape: [polygon, (text, confidence)]
            if (len(value) == 2 and isinstance(value[1], (list, tuple))
                    and len(value[1]) >= 2 and isinstance(value[1][0], str)):
                add(value[1][0], value[1][1])
                return
            for item in value:
                visit(item)

    visit(result)
    deduplicated: dict[str, tuple[str, float]] = {}
    for text, score in pairs:
        key = text.casefold()
        if key not in deduplicated or score > deduplicated[key][1]:
            deduplicated[key] = (text, score)
    ordered = sorted(deduplicated.values(), key=lambda item: item[1], reverse=True)[:32]
    if not ordered:
        return OCREvidence()
    return OCREvidence(
        tokens=tuple(item[0] for item in ordered),
        confidence=sum(item[1] for item in ordered) / len(ordered),
    )


class PaddleOCRProvider:
    def __init__(self, *, enabled: bool, language: str, version: str, device: str,
                 minimum_confidence: float, cache_root: str):
        self.enabled = enabled
        self.language = language
        self.version = version
        self.device = device
        self.minimum_confidence = minimum_confidence
        self.cache_root = Path(cache_root).expanduser().resolve()
        self._engine = None
        self._error: str | None = None
        self._lock = RLock()

    def _load(self) -> None:
        if self._engine is not None:
            return
        if not self.enabled:
            raise RuntimeError("OCR is disabled")
        try:
            configure_model_cache(self.cache_root)
            from paddleocr import PaddleOCR

            kwargs = {
                "lang": self.language,
                "ocr_version": self.version,
                "device": self.device,
                "use_doc_orientation_classify": False,
                "use_doc_unwarping": False,
                "use_textline_orientation": False,
            }
            try:
                self._engine = PaddleOCR(**kwargs)
            except TypeError:
                # Compatibility with the older API while deployments migrate.
                self._engine = PaddleOCR(
                    lang=self.language,
                    ocr_version=self.version,
                    use_angle_cls=False,
                    show_log=False,
                )
            self._error = None
        except Exception as exc:
            self._error = f"OCR unavailable: {type(exc).__name__}: {exc}"[:300]
            raise RuntimeError(self._error) from exc

    def extract(self, crop: np.ndarray) -> OCREvidence:
        if not self.enabled or crop.size == 0:
            return OCREvidence()
        with self._lock:
            self._load()
            if hasattr(self._engine, "predict"):
                result = self._engine.predict(crop)
            else:
                result = self._engine.ocr(crop, cls=False)
        parsed = parse_paddle_output(result)
        accepted = tuple(
            token for token in parsed.tokens
            if token and parsed.confidence >= self.minimum_confidence
        )
        return OCREvidence(tokens=accepted, confidence=parsed.confidence if accepted else 0.0)

    def health(self) -> dict[str, Any]:
        return {
            "provider": "paddleocr",
            "enabled": self.enabled,
            "package_available": importlib.util.find_spec("paddleocr") is not None,
            "loaded": self._engine is not None,
            "version": self.version,
            "language": self.language,
            "device": self.device,
            "error": self._error,
        }


class DinoV2Retriever:
    """DINOv2 catalog retrieval using an explicitly staged local model directory."""

    def __init__(self, *, enabled: bool, model_path: str, reference_root: str,
                 device: str, minimum_score: float, minimum_margin: float,
                 maximum_reference_images: int, cache_root: str):
        self.enabled = enabled
        self.model_path = Path(model_path).expanduser() if model_path else None
        self.reference_root = Path(reference_root).expanduser().resolve()
        self.device = device
        self.minimum_score = minimum_score
        self.minimum_margin = minimum_margin
        self.maximum_reference_images = maximum_reference_images
        self.cache_root = Path(cache_root).expanduser().resolve()
        self._processor = None
        self._model = None
        self._cache_signature: tuple[tuple[str, str, int, int], ...] = ()
        self._reference_vectors: tuple[tuple[str, np.ndarray], ...] = ()
        self._error: str | None = None
        self._lock = RLock()

    def _load(self) -> None:
        if self._model is not None:
            return
        if not self.enabled:
            raise RuntimeError("Visual retrieval is disabled")
        if self.model_path is None or not self.model_path.is_dir():
            raise RuntimeError("Configured local DINOv2 model directory is missing")
        try:
            configure_model_cache(self.cache_root)
            from transformers import AutoImageProcessor, AutoModel

            self._processor = AutoImageProcessor.from_pretrained(
                str(self.model_path), local_files_only=True
            )
            self._model = AutoModel.from_pretrained(
                str(self.model_path), local_files_only=True
            ).to(self.device)
            self._model.eval()
            self._error = None
        except Exception as exc:
            message = str(exc).replace(str(self.model_path), self.model_path.name) if self.model_path else str(exc)
            self._error = f"Visual retrieval unavailable: {type(exc).__name__}: {message}"[:300]
            raise RuntimeError(self._error) from exc

    def _safe_reference_path(self, value: str) -> Path | None:
        candidate = Path(value)
        if candidate.is_absolute() or "://" in value:
            return None
        resolved = (self.reference_root / candidate).resolve()
        try:
            resolved.relative_to(self.reference_root)
        except ValueError:
            return None
        return resolved if resolved.is_file() else None

    def _references(self, products: Iterable[Product]) -> list[tuple[str, Path]]:
        references: list[tuple[str, Path]] = []
        for product in products:
            for value in product.reference_images or []:
                if len(references) >= self.maximum_reference_images:
                    return references
                path = self._safe_reference_path(str(value))
                if path is not None:
                    references.append((product.id, path))
        return references

    def _embed(self, bgr_image: np.ndarray) -> np.ndarray:
        import torch
        from PIL import Image

        rgb = bgr_image[:, :, ::-1]
        inputs = self._processor(images=Image.fromarray(rgb), return_tensors="pt")
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with torch.inference_mode():
            output = self._model(**inputs)
            vector = getattr(output, "pooler_output", None)
            if vector is None:
                vector = output.last_hidden_state[:, 0]
            vector = torch.nn.functional.normalize(vector, dim=-1)
        return vector[0].detach().cpu().numpy().astype(np.float32)

    def _ensure_reference_cache(self, products: Iterable[Product]) -> None:
        import cv2

        references = self._references(products)
        signature = tuple(
            (product_id, str(path), path.stat().st_mtime_ns, path.stat().st_size)
            for product_id, path in references
        )
        if signature == self._cache_signature:
            return
        vectors: list[tuple[str, np.ndarray]] = []
        for product_id, path in references:
            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if image is None or image.size == 0:
                logger.warning("Skipping unreadable product reference image path=%s", path)
                continue
            vectors.append((product_id, self._embed(image)))
        self._cache_signature = signature
        self._reference_vectors = tuple(vectors)

    def retrieve(self, crop: np.ndarray, products: Iterable[Product]) -> RetrievalEvidence:
        if not self.enabled or crop.size == 0:
            return RetrievalEvidence()
        with self._lock:
            self._load()
            products = tuple(products)
            self._ensure_reference_cache(products)
            if not self._reference_vectors:
                return RetrievalEvidence()
            query = self._embed(crop)
        by_product: dict[str, float] = {}
        for product_id, reference in self._reference_vectors:
            score = float(np.dot(query, reference))
            by_product[product_id] = max(score, by_product.get(product_id, -1.0))
        ranked = sorted(by_product.items(), key=lambda item: item[1], reverse=True)
        return RetrievalEvidence(scores=tuple(ranked[:3]))

    def health(self) -> dict[str, Any]:
        model_present = bool(self.model_path and self.model_path.is_dir())
        return {
            "provider": "dinov2",
            "enabled": self.enabled,
            "package_available": importlib.util.find_spec("transformers") is not None,
            "model_present": model_present,
            "loaded": self._model is not None,
            "model_path": self.model_path.name if self.model_path else None,
            "reference_root": self.reference_root.name,
            "reference_embeddings": len(self._reference_vectors),
            "device": self.device,
            "error": self._error,
        }


def parse_florence_output(result: Any, task: str) -> FlorenceEvidence:
    """Normalize official Florence-2 caption post-processing output."""
    value = result.get(task, result) if isinstance(result, dict) else result
    if isinstance(value, dict):
        for key in ("caption", "description", "text"):
            if isinstance(value.get(key), str):
                value = value[key]
                break
        else:
            labels = value.get("labels")
            value = " ".join(str(item) for item in labels) if isinstance(labels, list) else ""
    text = _clean_token(value)
    return FlorenceEvidence(description=text[:500] if text else None, task=task if text else None)


class Florence2Provider:
    """Lazy optional Florence-2 caption evidence using an explicit model source."""

    def __init__(self, *, enabled: bool, model_id: str, model_path: str,
                 allow_remote_download: bool, trust_remote_code: bool, device: str,
                 task: str, policy: str, trigger_max_confidence: float,
                 max_new_tokens: int, num_beams: int, cache_root: str):
        self.enabled = enabled
        self.model_id = model_id.strip()
        self.model_path = Path(model_path).expanduser() if model_path else None
        self.allow_remote_download = allow_remote_download
        self.trust_remote_code = trust_remote_code
        self.requested_device = device
        self.task = task
        self.policy = policy
        self.trigger_max_confidence = trigger_max_confidence
        self.max_new_tokens = max_new_tokens
        self.num_beams = num_beams
        self.cache_root = Path(cache_root).expanduser().resolve()
        self._processor = None
        self._model = None
        self._actual_device = "unresolved"
        self._error: str | None = None
        self._lock = RLock()

    def _source(self) -> tuple[str, bool]:
        if self.model_path and self.model_path.is_dir():
            return str(self.model_path), True
        if self.allow_remote_download and self.model_id:
            return self.model_id, False
        raise RuntimeError(
            "Configured local Florence-2 model directory is missing; remote download is disabled"
        )

    def _load(self) -> None:
        if self._model is not None:
            return
        if not self.enabled:
            raise RuntimeError("Florence-2 is disabled")
        try:
            configure_model_cache(self.cache_root)
            import torch
            from transformers import AutoModelForCausalLM, AutoProcessor
            from app.cv.detectors import resolve_device

            source, local_only = self._source()
            self._actual_device, _cuda = resolve_device(self.requested_device)
            dtype = torch.float16 if self._actual_device.startswith("cuda") else torch.float32
            common = {
                "local_files_only": local_only,
                "trust_remote_code": self.trust_remote_code,
            }
            self._processor = AutoProcessor.from_pretrained(source, **common)
            self._model = AutoModelForCausalLM.from_pretrained(
                source,
                torch_dtype=dtype,
                use_safetensors=True,
                **common,
            ).to(self._actual_device)
            self._model.eval()
            self._error = None
        except Exception as exc:
            message = str(exc).replace(str(self.model_path), self.model_path.name) if self.model_path else str(exc)
            self._error = f"Florence-2 unavailable: {type(exc).__name__}: {message}"[:300]
            raise RuntimeError(self._error) from exc

    def describe(self, crop: np.ndarray) -> FlorenceEvidence:
        if not self.enabled or crop.size == 0:
            return FlorenceEvidence()
        with self._lock:
            self._load()
            import torch
            from PIL import Image

            image = Image.fromarray(crop[:, :, ::-1])
            inputs = self._processor(text=self.task, images=image, return_tensors="pt")
            prepared = {}
            dtype = torch.float16 if self._actual_device.startswith("cuda") else torch.float32
            for key, value in inputs.items():
                if torch.is_floating_point(value):
                    prepared[key] = value.to(device=self._actual_device, dtype=dtype)
                else:
                    prepared[key] = value.to(self._actual_device)
            with torch.inference_mode():
                generated = self._model.generate(
                    **prepared,
                    max_new_tokens=self.max_new_tokens,
                    num_beams=self.num_beams,
                    do_sample=False,
                )
            decoded = self._processor.batch_decode(generated, skip_special_tokens=False)[0]
            parsed = self._processor.post_process_generation(
                decoded, task=self.task, image_size=image.size
            )
            return parse_florence_output(parsed, self.task)

    def should_run(self, identity_status: str, detector_confidence: float) -> bool:
        if not self.enabled:
            return False
        ambiguous = identity_status in {"ambiguous", "unknown", "category_only"}
        low_confidence = detector_confidence <= self.trigger_max_confidence
        return {
            "ambiguous": ambiguous,
            "low_confidence": low_confidence,
            "ambiguous_or_low_confidence": ambiguous or low_confidence,
        }[self.policy]

    def health(self) -> dict[str, Any]:
        model_present = bool(self.model_path and self.model_path.is_dir())
        source = self.model_path.name if model_present else (
            self.model_id if self.allow_remote_download else None
        )
        return {
            "provider": "florence2",
            "enabled": self.enabled,
            "package_available": importlib.util.find_spec("transformers") is not None,
            "model_present": model_present,
            "loaded": self._model is not None,
            "model_source": source,
            "model_id": self.model_id,
            "remote_download_allowed": self.allow_remote_download,
            "trust_remote_code": self.trust_remote_code,
            "task": self.task,
            "policy": self.policy,
            "requested_device": self.requested_device,
            "actual_device": self._actual_device,
            "error": self._error,
        }


class IdentityEvidenceRuntime:
    def __init__(self, settings):
        self.ocr = PaddleOCRProvider(
            enabled=settings.CV_OCR_ENABLED,
            language=settings.CV_OCR_LANGUAGE,
            version=settings.CV_OCR_VERSION,
            device=settings.CV_OCR_DEVICE,
            minimum_confidence=settings.CV_OCR_MIN_CONFIDENCE,
            cache_root=settings.CV_IDENTITY_CACHE_ROOT,
        )
        self.retriever = DinoV2Retriever(
            enabled=settings.CV_EMBEDDING_ENABLED,
            model_path=settings.CV_EMBEDDING_MODEL_PATH,
            reference_root=settings.CV_REFERENCE_IMAGE_ROOT,
            device=settings.CV_EMBEDDING_DEVICE,
            minimum_score=settings.CV_RETRIEVAL_MIN_CONFIDENCE,
            minimum_margin=settings.CV_RETRIEVAL_MIN_MARGIN,
            maximum_reference_images=settings.CV_MAX_REFERENCE_IMAGES,
            cache_root=settings.CV_IDENTITY_CACHE_ROOT,
        )
        self.florence = Florence2Provider(
            enabled=settings.CV_FLORENCE_ENABLED,
            model_id=settings.CV_FLORENCE_MODEL_ID,
            model_path=settings.CV_FLORENCE_MODEL_PATH,
            allow_remote_download=settings.CV_FLORENCE_ALLOW_REMOTE_DOWNLOAD,
            trust_remote_code=settings.CV_FLORENCE_TRUST_REMOTE_CODE,
            device=settings.CV_FLORENCE_DEVICE,
            task=settings.CV_FLORENCE_TASK,
            policy=settings.CV_FLORENCE_POLICY,
            trigger_max_confidence=settings.CV_FLORENCE_TRIGGER_MAX_CONFIDENCE,
            max_new_tokens=settings.CV_FLORENCE_MAX_NEW_TOKENS,
            num_beams=settings.CV_FLORENCE_NUM_BEAMS,
            cache_root=settings.CV_IDENTITY_CACHE_ROOT,
        )

    @property
    def enabled(self) -> bool:
        return self.ocr.enabled or self.retriever.enabled or self.florence.enabled

    def extract(self, crop: np.ndarray, products: Iterable[Product]) -> EnrichedIdentityEvidence:
        errors: list[str] = []
        ocr = OCREvidence()
        retrieval = RetrievalEvidence()
        if self.ocr.enabled:
            try:
                ocr = self.ocr.extract(crop)
            except Exception as exc:
                logger.warning("OCR evidence unavailable: %s", exc)
                errors.append("ocr_unavailable")
        if self.retriever.enabled:
            try:
                retrieval = self.retriever.retrieve(crop, products)
            except Exception as exc:
                logger.warning("Visual retrieval evidence unavailable: %s", exc)
                errors.append("retrieval_unavailable")
        return EnrichedIdentityEvidence(ocr=ocr, retrieval=retrieval, errors=tuple(errors))

    def should_use_florence(self, identity_status: str, detector_confidence: float) -> bool:
        return self.florence.should_run(identity_status, detector_confidence)

    def add_florence(self, evidence: EnrichedIdentityEvidence,
                     crop: np.ndarray) -> EnrichedIdentityEvidence:
        try:
            florence = self.florence.describe(crop)
            return EnrichedIdentityEvidence(
                ocr=evidence.ocr, retrieval=evidence.retrieval, florence=florence,
                errors=evidence.errors,
            )
        except Exception as exc:
            logger.warning("Florence-2 evidence unavailable: %s", exc)
            return EnrichedIdentityEvidence(
                ocr=evidence.ocr, retrieval=evidence.retrieval, florence=evidence.florence,
                errors=(*evidence.errors, "florence_unavailable"),
            )

    def health(self) -> dict[str, Any]:
        return {
            "ocr": self.ocr.health(),
            "retrieval": self.retriever.health(),
            "florence": self.florence.health(),
        }


def crop_detection(frame: np.ndarray, xyxy: Iterable[float], padding_ratio: float = 0.04) -> np.ndarray:
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = (float(value) for value in xyxy)
    pad_x = max(2, int((x2 - x1) * padding_ratio))
    pad_y = max(2, int((y2 - y1) * padding_ratio))
    left = max(0, int(x1) - pad_x)
    top = max(0, int(y1) - pad_y)
    right = min(width, int(x2 + 0.999) + pad_x)
    bottom = min(height, int(y2 + 0.999) + pad_y)
    return frame[top:bottom, left:right].copy()


def image_sharpness(image: np.ndarray) -> float:
    if image.size == 0:
        return 0.0
    import cv2
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())
