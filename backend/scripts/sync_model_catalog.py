"""Create reviewed model classes in the product catalog without overwriting products."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.cv.model_artifact import ModelManifest
from app.database import SessionLocal
from app.models import Product
from app.models.user import User, UserRole
from app.services.operations import audit
from app.services.outbox import enqueue


DEFAULT_MANIFEST = Path(__file__).resolve().parents[2] / "models" / "model-manifest.json"
DESCRIPTION = "Catalog product mapped to the reviewed 25-class Pakistani-products detector."


@dataclass(frozen=True)
class CatalogMetadata:
    brand: str
    category: str
    variant: str | None
    package_size: str


CATALOG_METADATA = {
    0: CatalogMetadata("Bisconni", "biscuits_bakery", "Chocolate Chip Cookies", "46.8 gm"),
    1: CatalogMetadata("Coca-Cola", "juice_beverages", "Can", "250 ml"),
    2: CatalogMetadata("Colgate", "personal_care", "Maximum Cavity Protection", "75 gm"),
    3: CatalogMetadata("Fanta", "juice_beverages", None, "500 ml"),
    4: CatalogMetadata("Fresher", "juice_beverages", "Guava Nectar", "500 ml"),
    5: CatalogMetadata("Fruita Vitals", "juice_beverages", "Red Grapes", "200 ml"),
    6: CatalogMetadata("Islamabad Tea", "tea", None, "238 gm"),
    7: CatalogMetadata("Kolson", "chips_snacks", "Slanty Jalapeno", "18 gm"),
    8: CatalogMetadata("Kurkure", "chips_snacks", "Chutney Chaska", "62 gm"),
    9: CatalogMetadata("LU", "biscuits_bakery", "Candi", "60 gm"),
    10: CatalogMetadata("LU", "biscuits_bakery", "Oreo", "19 gm"),
    11: CatalogMetadata("LU", "biscuits_bakery", "Prince", "55.2 gm"),
    12: CatalogMetadata("Lay's", "chips_snacks", "Masala", "34 gm"),
    13: CatalogMetadata("Lay's", "chips_snacks", "Wavy Mexican Chili", "34 gm"),
    14: CatalogMetadata("Lifebuoy", "personal_care", "Total Protect", "96 gm"),
    15: CatalogMetadata("Lipton", "tea", "Yellow Label", "95 gm"),
    16: CatalogMetadata("Meezan", "tea", "Ultra Rich", "190 gm"),
    17: CatalogMetadata("Peek Freans", "biscuits_bakery", "Sooper", "13.2 gm"),
    18: CatalogMetadata("Safeguard", "personal_care", "Pure White", "175 gm"),
    19: CatalogMetadata("Shezan", "juice_beverages", "Apple", "250 ml"),
    20: CatalogMetadata("Sunsilk", "personal_care", "Soft & Smooth", "160 ml"),
    21: CatalogMetadata("Super Crisp", "chips_snacks", "BBQ", "30 gm"),
    22: CatalogMetadata("Supreme", "tea", None, "95 gm"),
    23: CatalogMetadata("Tapal", "tea", "Danedar", "95 gm"),
    24: CatalogMetadata("Vaseline", "personal_care", "Healthy White", "100 ml"),
}


def read_catalog_manifest(path: str | Path) -> ModelManifest:
    manifest = ModelManifest.model_validate_json(Path(path).read_text(encoding="utf-8"))
    blank_skus = [item.class_id for item in manifest.classes if not item.sku]
    if blank_skus:
        raise ValueError(f"Manifest classes require reviewed SKUs: {blank_skus}")
    if {item.class_id for item in manifest.classes} != set(CATALOG_METADATA):
        raise ValueError("Catalog metadata must exactly cover the reviewed model classes")
    return manifest


def sync_catalog(db: Session, admin_email: str, manifest_path: str | Path) -> dict:
    """Caller owns the transaction; repeated runs validate and preserve existing rows."""
    admin = (
        db.query(User)
        .filter(func.lower(User.email) == admin_email.strip().lower())
        .with_for_update()
        .one_or_none()
    )
    if not admin or admin.role != UserRole.ADMIN or not admin.is_active or admin.signup_pending:
        raise ValueError("An active approved administrator is required")

    manifest = read_catalog_manifest(manifest_path)
    existing_by_sku = {row.sku.casefold(): row for row in db.query(Product).all()}
    created = 0
    existing = 0
    for item in sorted(manifest.classes, key=lambda value: value.class_id):
        metadata = CATALOG_METADATA[item.class_id]
        product = existing_by_sku.get(item.sku.casefold())
        expected = {
            "name": item.label,
            "brand": metadata.brand,
            "category": metadata.category,
            "variant": metadata.variant,
            "package_size": metadata.package_size,
        }
        if product:
            mismatched = [name for name, value in expected.items() if getattr(product, name) != value]
            if mismatched:
                raise ValueError(
                    f"Existing SKU {item.sku} differs in reviewed fields: {', '.join(mismatched)}"
                )
            existing += 1
            continue

        product = Product(sku=item.sku, description=DESCRIPTION, **expected)
        db.add(product)
        db.flush()
        existing_by_sku[item.sku.casefold()] = product
        audit(
            db,
            admin,
            "create_model_catalog",
            "product",
            product.id,
            new={
                "class_id": item.class_id,
                "model_version": manifest.model_version,
                "sku": item.sku,
            },
        )
        created += 1

    if created:
        enqueue(db, "configuration_updated", {"resource": "products"})
    return {
        "model_version": manifest.model_version,
        "classes": len(manifest.classes),
        "created": created,
        "existing": existing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--admin-email", required=True)
    parser.add_argument("--apply", action="store_true", help="Insert missing reviewed products")
    args = parser.parse_args()
    try:
        manifest = read_catalog_manifest(args.manifest)
        if not args.apply:
            print(json.dumps({
                "preview": True,
                "model_version": manifest.model_version,
                "classes": len(manifest.classes),
                "note": "Use --apply to create missing catalog products.",
            }))
            return 0
        with SessionLocal() as db, db.begin():
            result = sync_catalog(db, args.admin_email, args.manifest)
        print(json.dumps({"applied": True, **result}))
        return 0
    except Exception as exc:
        print(json.dumps({
            "applied": False,
            "error_type": type(exc).__name__,
            "note": "No partial catalog changes were committed.",
        }))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
