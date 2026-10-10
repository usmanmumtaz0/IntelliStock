"""Explicit synthetic Pakistani supermarket fixture; never overwrites existing data."""
import argparse
import json

from sqlalchemy import func
from app.core.config import settings
from app.database import SessionLocal
from app.models import Product, Camera, ShelfZone, Inventory
from app.models.user import User, UserRole
from app.models.inventory import InventoryStatus
from app.api.inventory import CorrectionRequest
from app.services.operations import audit, correct_inventory

# Illustrative names/pack sizes, not a real retailer's catalog or sales data.
CATALOG = {
    "Grocery": [
        ("Atta 5 kg", 24, 5), ("Basmati Rice 1 kg", 36, 8),
        ("Sugar 1 kg", 4, 6), ("Iodized Salt 800 g", 0, 5),
        ("Cooking Oil 1 L", 18, 5), ("Daal Chana 1 kg", 3, 5),
        ("Daal Masoor 1 kg", 16, 4), ("Tea 190 g", 22, 6),
    ],
    "Dairy": [
        ("UHT Milk 1 L", 32, 8), ("Yogurt 400 g", 4, 5),
        ("Butter 200 g", 0, 3), ("Cheese Slices 200 g", 12, 3),
        ("Cream 200 ml", 15, 4), ("Milk Powder 390 g", 2, 4),
        ("Lassi 250 ml", 20, 5),
    ],
    "Beverages and Snacks": [
        ("Cola 1.5 L", 30, 8), ("Mango Juice 1 L", 5, 6),
        ("Mineral Water 1.5 L", 48, 10), ("Orange Drink 250 ml", 0, 6),
        ("Glucose Biscuits 100 g", 40, 10), ("Cream Biscuits 120 g", 6, 8),
        ("Potato Chips 50 g", 35, 10), ("Instant Noodles 65 g", 25, 6),
    ],
    "Household": [
        ("Laundry Powder 1 kg", 18, 5), ("Dishwashing Bar 200 g", 3, 5),
        ("Bath Soap 125 g", 28, 6), ("Shampoo 180 ml", 0, 4),
        ("Toothpaste 100 g", 16, 4), ("Tissue Box 200 sheets", 2, 5),
        ("Floor Cleaner 1 L", 14, 4),
    ],
}
MARKER = "Synthetic PK demo v1; not real stock or camera evidence."


def seed(db, admin_email: str) -> dict:
    """Caller owns transaction; lock the administrator to serialize repeated runs."""
    admin = db.query(User).filter_by(email=admin_email).with_for_update().one()
    if admin.role != UserRole.ADMIN or not admin.is_active or admin.signup_pending:
        raise ValueError("An active approved administrator is required")
    skus = [f"DEMO-PK-{i:03d}" for i in range(1, 31)]
    camera_names = [f"DEMO PK - {section} Camera" for section in CATALOG]
    zone_names = [f"DEMO PK - {section} Shelf" for section in CATALOG]
    if (db.query(Product).filter(func.lower(Product.sku).in_([s.lower() for s in skus])).first()
            or db.query(Camera).filter(Camera.name.in_(camera_names)).first()
            or db.query(ShelfZone).filter(ShelfZone.name.in_(zone_names)).first()):
        raise ValueError("Demo identifiers already exist; no records overwritten")
    counts = {"adequate": 0, "low_stock": 0, "out_of_stock": 0}
    index = 0
    for section, products in CATALOG.items():
        camera = Camera(name=f"DEMO PK - {section} Camera", location=f"Synthetic store / {section}",
                        source_url=None, is_active=False, calibration_notes=MARKER)
        db.add(camera); db.flush()
        zone = ShelfZone(camera_id=camera.id, name=f"DEMO PK - {section} Shelf",
                         description=MARKER + " Placeholder ROI, not calibrated.",
                         roi_polygon="[[0,0],[100,0],[100,100],[0,100]]")
        db.add(zone); db.flush()
        for kind, row in (("camera", camera), ("zone", zone)):
            audit(db, admin, "create_demo", kind, row.id, new={"synthetic": True, "dataset": "pk-demo-v1"})
        for name, quantity, threshold in products:
            product = Product(sku=skus[index], name=f"{name} [DEMO]", description=MARKER,
                              low_stock_threshold=threshold, reorder_point=threshold * 3)
            index += 1
            db.add(product); db.flush()
            inventory = Inventory(zone_id=zone.id, product_id=product.id, quantity_estimate=0,
                                  status=InventoryStatus.UNKNOWN, confidence=0, observations_count=0)
            db.add(inventory); db.flush()
            audit(db, admin, "create_demo", "product", product.id, new={"synthetic": True, "sku": product.sku})
            correct_inventory(db, inventory.id, CorrectionRequest(
                quantity=quantity, expected_updated_at=inventory.updated_at,
                reason="Synthetic PK supermarket demo starting count; not camera evidence."), admin)
            counts[inventory.status.value] += 1
    return {"products": index, "cameras": 4, "shelves": 4, "states": counts}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Explicitly insert demo records")
    parser.add_argument("--admin-email", required=True)
    args = parser.parse_args()
    if not args.apply:
        print("Preview: 30 products, 4 disabled cameras, 4 shelves, 30 manual history entries. Use --apply to insert.")
        return 0
    if settings.NOTIFICATIONS_ENABLED or settings.APP_ENV == "production":
        print("Refusing demo setup: use a non-production environment with email notifications disabled.")
        return 1
    try:
        with SessionLocal() as db, db.begin():
            result = seed(db, args.admin_email.strip().lower())
        print(json.dumps({"created": True, **result}))
        return 0
    except Exception as exc:
        print(json.dumps({"created": False, "error_type": type(exc).__name__,
                          "note": "Transaction rolled back. Check account and demo identifier collisions."}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
