"""Catalog-constrained product identification with evidence fusion.

Detector labels, OCR text, barcodes and visual retrieval are evidence. Only an
unambiguous catalog match becomes an exact product identity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum
import re

from sqlalchemy.orm import Session

from app.models.product import Product


class IdentityStatus(str, Enum):
    IDENTIFIED = "identified"
    CATEGORY_ONLY = "category_only"
    UNKNOWN = "unknown"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class IdentityEvidence:
    detector_label: str
    detector_confidence: float
    manifest_sku: str | None = None
    barcode: str | None = None
    ocr_tokens: tuple[str, ...] = ()
    ocr_confidence: float = 0.0
    retrieval_scores: tuple[tuple[str, float], ...] = ()
    florence_description: str | None = None
    provider_errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class IdentityResult:
    status: IdentityStatus
    product_id: str | None
    category: str | None
    brand: str | None
    variant: str | None
    package_size: str | None
    barcode: str | None
    confidence: float
    evidence: dict = field(default_factory=dict)


CATEGORY_RULES = (
    ("biscuits_bakery", ("biscuit", "cookie", "bakery", "oreo", "sooper", "candi", "prince")),
    ("chips_snacks", ("chips", "lays", "kurkure", "slanty", "crisp", "snack")),
    ("juice_beverages", ("juice", "nectar", "coca cola", "fanta", "shezan", "fruita")),
    ("tea", ("tea", "lipton", "tapal")),
    ("personal_care", ("soap", "shampoo", "lotion", "toothpaste", "colgate")),
    ("milk_dairy", ("milk", "dairy", "yogurt", "cheese")),
    ("bottled_water", ("water",)),
    ("cooking_oil", ("cooking oil", "oil bottle")),
    ("packaged_staples", ("rice", "flour", "sugar")),
    ("cereal", ("cereal",)),
    ("canned_jarred", ("canned", "jar", "tin")),
)

IGNORED_OCR_WORDS = {"the", "and", "new", "original", "pack", "product", "ml", "gm", "g"}


def normalize(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").casefold()).strip()


def category_for(label: str) -> str | None:
    normalized = normalize(label)
    for category, terms in CATEGORY_RULES:
        if any(term in normalized for term in terms):
            return category
    return None


def _catalog_text(product: Product) -> str:
    return " ".join(filter(None, (
        product.name, product.brand, product.variant, product.package_size
    )))


def _ocr_score(product: Product, tokens: tuple[str, ...]) -> float:
    observed = normalize(" ".join(tokens))
    if not observed:
        return 0.0
    expected = normalize(_catalog_text(product))
    expected_tokens = {
        token for token in expected.split()
        if len(token) > 1 and token not in IGNORED_OCR_WORDS
    }
    observed_tokens = set(observed.split())
    recall = len(expected_tokens & observed_tokens) / max(1, len(expected_tokens))
    name_similarity = SequenceMatcher(None, normalize(product.name), observed).ratio()
    brand_tokens = set(normalize(product.brand).split()) if product.brand else set()
    brand_coverage = (
        len(brand_tokens & observed_tokens) / len(brand_tokens) if brand_tokens else 0.0
    )
    base_score = max(name_similarity, recall * 0.82)
    # A partially matching multi-word brand must not outrank an exact brand;
    # this is common among near-identical package variants.
    if brand_tokens and brand_coverage < 1.0:
        base_score *= 0.65
    brand_bonus = 0.12 * brand_coverage
    variant_bonus = 0.08 if product.variant and normalize(product.variant) in observed else 0.0
    size_bonus = 0.08 if product.package_size and normalize(product.package_size) in observed else 0.0
    return min(1.0, base_score + brand_bonus + variant_bonus + size_bonus)


class ProductIdentityService:
    def __init__(self, db: Session, minimum_confidence: float,
                 *, ocr_minimum_confidence: float = 0.72,
                 ocr_minimum_margin: float = 0.10,
                 retrieval_minimum_confidence: float = 0.82,
                 retrieval_minimum_margin: float = 0.05,
                 florence_minimum_confidence: float = 0.72,
                 florence_minimum_margin: float = 0.10):
        self.db = db
        self.minimum_confidence = minimum_confidence
        self.ocr_minimum_confidence = ocr_minimum_confidence
        self.ocr_minimum_margin = ocr_minimum_margin
        self.retrieval_minimum_confidence = retrieval_minimum_confidence
        self.retrieval_minimum_margin = retrieval_minimum_margin
        self.florence_minimum_confidence = florence_minimum_confidence
        self.florence_minimum_margin = florence_minimum_margin

    @staticmethod
    def _result(product: Product, confidence: float, method: str, details: dict) -> IdentityResult:
        return IdentityResult(
            status=IdentityStatus.IDENTIFIED,
            product_id=product.id,
            category=product.category,
            brand=product.brand,
            variant=product.variant,
            package_size=product.package_size,
            barcode=product.barcode,
            confidence=max(0.0, min(1.0, confidence)),
            evidence={"method": method, "catalog_sku": product.sku, "catalog_name": product.name, **details},
        )

    def identify(self, evidence: IdentityEvidence) -> IdentityResult:
        products = self.db.query(Product).all()
        by_id = {product.id: product for product in products}
        details = {
            "detector_label": evidence.detector_label,
            "ocr_tokens": list(evidence.ocr_tokens[:16]),
            "ocr_confidence": round(evidence.ocr_confidence, 4),
            "retrieval_candidates": [
                {"product_id": product_id, "score": round(float(score), 4)}
                for product_id, score in evidence.retrieval_scores[:3]
                if product_id in by_id
            ],
            "florence_description": (evidence.florence_description or "")[:500] or None,
            "provider_errors": list(evidence.provider_errors),
            "confidence_semantics": "heuristic evidence score; not a calibrated probability",
        }

        if evidence.barcode:
            matches = [product for product in products if product.barcode == evidence.barcode]
            if len(matches) == 1:
                return self._result(matches[0], 1.0, "catalog_barcode", details)
            if len(matches) > 1:
                return self._ambiguous(evidence, "catalog_barcode", len(matches), details)

        manifest_choice = None
        if evidence.manifest_sku:
            matches = [product for product in products if product.sku == evidence.manifest_sku]
            if len(matches) == 1 and evidence.detector_confidence >= self.minimum_confidence:
                manifest_choice = matches[0]

        label = normalize(evidence.detector_label)
        exact = [product for product in products if normalize(product.name) == label]
        if len(exact) > 1:
            return self._ambiguous(evidence, "exact_catalog_name", len(exact), details)

        ranked_retrieval = [
            (by_id[product_id], float(score))
            for product_id, score in evidence.retrieval_scores
            if product_id in by_id
        ]
        ranked_retrieval.sort(key=lambda item: item[1], reverse=True)
        retrieval_choice = None
        if ranked_retrieval:
            top_product, top_score = ranked_retrieval[0]
            second_score = ranked_retrieval[1][1] if len(ranked_retrieval) > 1 else -1.0
            if (top_score >= self.retrieval_minimum_confidence
                    and top_score - second_score >= self.retrieval_minimum_margin):
                retrieval_choice = (top_product, top_score)

        ranked_ocr = sorted(
            ((product, _ocr_score(product, evidence.ocr_tokens) * evidence.ocr_confidence)
             for product in products),
            key=lambda item: item[1], reverse=True,
        )
        ocr_choice = None
        if ranked_ocr:
            top_product, top_score = ranked_ocr[0]
            second_score = ranked_ocr[1][1] if len(ranked_ocr) > 1 else 0.0
            if (top_score >= self.ocr_minimum_confidence
                    and top_score - second_score >= self.ocr_minimum_margin):
                ocr_choice = (top_product, top_score)

        ranked_florence = sorted(
            ((product, _ocr_score(product, (evidence.florence_description or "",)))
             for product in products),
            key=lambda item: item[1], reverse=True,
        )
        florence_choice = None
        if evidence.florence_description and ranked_florence:
            top_product, top_score = ranked_florence[0]
            second_score = ranked_florence[1][1] if len(ranked_florence) > 1 else 0.0
            if (top_score >= self.florence_minimum_confidence
                    and top_score - second_score >= self.florence_minimum_margin):
                florence_choice = (top_product, top_score)

        choices = [
            ("retrieval", retrieval_choice),
            ("ocr", ocr_choice),
            ("florence", florence_choice),
        ]
        accepted = [(name, choice[0], choice[1]) for name, choice in choices if choice]
        details["candidate_catalog_products"] = [
            {"source": name, "product_id": product.id, "score": round(score, 4)}
            for name, product, score in accepted
        ]
        selected_ids = {product.id for _name, product, _score in accepted}
        if manifest_choice and selected_ids and selected_ids != {manifest_choice.id}:
            return self._ambiguous(
                evidence, "conflicting_detector_and_multimodal_evidence",
                len(selected_ids | {manifest_choice.id}), details,
            )
        if len(selected_ids) > 1:
            method = ("conflicting_ocr_and_visual" if not florence_choice
                      else "conflicting_multimodal_evidence")
            return self._ambiguous(evidence, method, len(selected_ids), details)
        if accepted:
            names = {name for name, _product, _score in accepted}
            product = accepted[0][1]
            # This conservative rule is explicit and intentionally not presented as calibration.
            confidence = min(score for _name, _product, score in accepted)
            if names == {"retrieval", "ocr"}:
                method = "ocr_visual_consensus"
            elif len(names) > 1:
                method = "multimodal_consensus"
            elif "retrieval" in names:
                method = "dinov2_catalog_retrieval"
            elif "ocr" in names:
                method = "paddleocr_catalog_match"
            else:
                method = "florence_catalog_match"
            details["supporting_evidence"] = sorted(names)
            return self._result(product, confidence, method, details)
        if manifest_choice:
            return self._result(
                manifest_choice, evidence.detector_confidence, "reviewed_manifest_sku", details
            )
        if len(exact) == 1 and evidence.detector_confidence >= self.minimum_confidence:
            return self._result(exact[0], evidence.detector_confidence, "exact_catalog_name", details)

        category = category_for(evidence.detector_label)
        return IdentityResult(
            status=IdentityStatus.CATEGORY_ONLY if category else IdentityStatus.UNKNOWN,
            product_id=None,
            category=category,
            brand=None,
            variant=None,
            package_size=None,
            barcode=evidence.barcode,
            confidence=evidence.detector_confidence,
            evidence={
                "method": "detector_category" if category else "insufficient_evidence",
                "catalog_match": False,
                **details,
            },
        )

    @staticmethod
    def _ambiguous(evidence: IdentityEvidence, method: str, count: int,
                   details: dict) -> IdentityResult:
        return IdentityResult(
            status=IdentityStatus.AMBIGUOUS,
            product_id=None,
            category=category_for(evidence.detector_label),
            brand=None,
            variant=None,
            package_size=None,
            barcode=evidence.barcode,
            confidence=evidence.detector_confidence,
            evidence={"method": method, "candidate_count": count, **details},
        )
