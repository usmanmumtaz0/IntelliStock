"""
Database seeding script — populates realistic test data.
Run once to initialize database with zones, products, cameras, and inventory.
"""
import sys
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# Add backend to path
sys.path.insert(0, 'd:\intellistock 1\backend')

from app.database import SessionLocal, engine
from app.models.base import BaseModel
from app.models.camera import Camera
from app.models.product import Product
from app.models.zone import ShelfZone
from app.models.inventory import Inventory, InventoryStatus

# Create all tables
BaseModel.metadata.create_all(bind=engine)

def seed_cameras(db: Session):
    """Add 8 cameras for different aisles."""
    cameras_data = [
        {"name": "Aisle A · North", "location": "Floor 1 · Aisle A · Bay 1–2", "fps": 24},
        {"name": "Aisle A · South", "location": "Floor 1 · Aisle A · Bay 3–4", "fps": 12},
        {"name": "Aisle B · North", "location": "Floor 1 · Aisle B · Bay 1–2", "fps": 24},
        {"name": "Aisle B · South", "location": "Floor 1 · Aisle B · Bay 3–4", "fps": 24},
        {"name": "Dairy Cooler", "location": "Floor 1 · Aisle C · Cooler 1", "fps": 0, "inactive": True},
        {"name": "Aisle C · Freezers", "location": "Floor 1 · Aisle C · Bay 2–4", "fps": 18},
        {"name": "Aisle D · North", "location": "Floor 1 · Aisle D · Bay 1–2", "fps": 24},
        {"name": "Aisle D · South", "location": "Floor 1 · Aisle D · Bay 3–4", "fps": 24},
    ]
    
    for i, cam_data in enumerate(cameras_data):
        inactive = cam_data.pop("inactive", False)
        cam = Camera(
            id=f"CAM-{i+1:02d}",
            **cam_data,
            is_active=not inactive,
        )
        db.add(cam)
    
    db.commit()
    print(f"✅ Added {len(cameras_data)} cameras")
    return {cam.id: cam for cam in db.query(Camera).all()}


def seed_zones(db: Session, cameras: dict):
    """Add 16 zones (4 per aisle)."""
    zones_data = [
        # Aisle A
        {"id": "A-1", "camera_id": "CAM-01", "name": "A-1", "description": "Beverages · Water & Soda"},
        {"id": "A-2", "camera_id": "CAM-01", "name": "A-2", "description": "Beverages · Energy & Tea"},
        {"id": "A-3", "camera_id": "CAM-02", "name": "A-3", "description": "Snacks · Chips"},
        {"id": "A-4", "camera_id": "CAM-02", "name": "A-4", "description": "Snacks · Confectionery"},
        # Aisle B
        {"id": "B-1", "camera_id": "CAM-03", "name": "B-1", "description": "Dry · Rice & Pasta"},
        {"id": "B-2", "camera_id": "CAM-03", "name": "B-2", "description": "Dry · Breakfast & Coffee"},
        {"id": "B-3", "camera_id": "CAM-04", "name": "B-3", "description": "Dry · Tea & Condiments"},
        {"id": "B-4", "camera_id": "CAM-04", "name": "B-4", "description": "Dry · Spices"},
        # Aisle C
        {"id": "C-1", "camera_id": "CAM-05", "name": "C-1", "description": "Dairy · Milk & Butter"},
        {"id": "C-2", "camera_id": "CAM-06", "name": "C-2", "description": "Dairy · Yogurt & Cheese"},
        {"id": "C-3", "camera_id": "CAM-06", "name": "C-3", "description": "Frozen · Ready Meals"},
        {"id": "C-4", "camera_id": "CAM-06", "name": "C-4", "description": "Frozen · Desserts"},
        # Aisle D
        {"id": "D-1", "camera_id": "CAM-07", "name": "D-1", "description": "Household · Laundry"},
        {"id": "D-2", "camera_id": "CAM-07", "name": "D-2", "description": "Personal · Oral & Hair"},
        {"id": "D-3", "camera_id": "CAM-08", "name": "D-3", "description": "Personal · Bath"},
        {"id": "D-4", "camera_id": "CAM-08", "name": "D-4", "description": "Personal · Hand Care"},
    ]
    
    for zone_data in zones_data:
        zone = ShelfZone(
            id=zone_data["id"],
            camera_id=zone_data["camera_id"],
            name=zone_data["name"],
            description=zone_data["description"],
            roi_polygon="[[0,0],[100,0],[100,100],[0,100]]",  # Dummy polygon
            detection_confidence_threshold=0.6,
        )
        db.add(zone)
    
    db.commit()
    print(f"✅ Added {len(zones_data)} zones")
    return {zone.id: zone for zone in db.query(ShelfZone).all()}


def seed_products(db: Session):
    """Add 24 products across categories."""
    products_data = [
        # Beverages
        {"sku": "BEV-1042", "name": "Coca-Cola Classic 330ml Can", "category": "Beverages"},
        {"sku": "BEV-1077", "name": "Nestlé Pure Life 1.5L", "category": "Beverages"},
        {"sku": "BEV-1103", "name": "Red Bull Energy 250ml", "category": "Beverages"},
        {"sku": "BEV-1130", "name": "Lipton Iced Tea Peach 500ml", "category": "Beverages"},
        # Snacks
        {"sku": "SNK-2011", "name": "Lay's Classic Salted 52g", "category": "Snacks"},
        {"sku": "SNK-2034", "name": "Pringles Sour Cream 165g", "category": "Snacks"},
        {"sku": "SNK-2058", "name": "Oreo Original 133g", "category": "Snacks"},
        {"sku": "SNK-2090", "name": "KitKat 4-Finger 41.5g", "category": "Snacks"},
        # Dry
        {"sku": "DRY-3005", "name": "Basmati Rice Premium 5kg", "category": "Dry Goods"},
        {"sku": "DRY-3021", "name": "Barilla Spaghetti No.5 500g", "category": "Dry Goods"},
        {"sku": "DRY-3044", "name": "Quaker Oats Rolled 1kg", "category": "Dry Goods"},
        {"sku": "DRY-3067", "name": "Nescafé Classic Jar 200g", "category": "Dry Goods"},
        # Dairy
        {"sku": "DAI-4012", "name": "Olper's Full Cream Milk 1L", "category": "Dairy"},
        {"sku": "DAI-4033", "name": "Nurpur Butter Salted 200g", "category": "Dairy"},
        {"sku": "DAI-4050", "name": "Activia Yogurt Strawberry 4pk", "category": "Dairy"},
        {"sku": "DAI-4071", "name": "Kraft Cheddar Slices 200g", "category": "Dairy"},
        # Household
        {"sku": "HHC-5008", "name": "Ariel Matic Detergent 2kg", "category": "Household"},
        {"sku": "HHC-5026", "name": "Dettol Antiseptic Liquid 500ml", "category": "Household"},
        {"sku": "HHC-5049", "name": "Colgate Max Fresh 150g", "category": "Personal"},
        {"sku": "HHC-5063", "name": "Head & Shoulders Shampoo 400ml", "category": "Personal"},
        {"sku": "HHC-5081", "name": "Safeguard Soap Pure White 3pk", "category": "Personal"},
        {"sku": "HHC-5097", "name": "Lifebuoy Hand Wash 200ml", "category": "Personal"},
        # Add more for variety
        {"sku": "DRY-3089", "name": "Tapal Danedar Tea 950g", "category": "Dry Goods"},
        {"sku": "DRY-3102", "name": "Heinz Tomato Ketchup 570g", "category": "Dry Goods"},
    ]
    
    for prod_data in products_data:
        prod = Product(
            id=f"prod-{prod_data['sku']}",
            **prod_data,
        )
        db.add(prod)
    
    db.commit()
    print(f"✅ Added {len(products_data)} products")
    return {prod.sku: prod for prod in db.query(Product).all()}


def seed_inventory(db: Session, zones: dict, products: dict):
    """Add inventory state for all zone/product combinations."""
    zone_product_map = {
        "A-1": ["BEV-1042", "BEV-1077"],
        "A-2": ["BEV-1103", "BEV-1130"],
        "A-3": ["SNK-2011", "SNK-2034"],
        "A-4": ["SNK-2058", "SNK-2090"],
        "B-1": ["DRY-3005", "DRY-3021"],
        "B-2": ["DRY-3044", "DRY-3067"],
        "B-3": ["DRY-3089", "DRY-3102"],
        "B-4": ["DRY-3005", "DRY-3021"],
        "C-1": ["DAI-4012", "DAI-4033"],
        "C-2": ["DAI-4050", "DAI-4071"],
        "C-3": ["SNK-2058", "SNK-2090"],
        "C-4": ["BEV-1042", "BEV-1103"],
        "D-1": ["HHC-5008", "HHC-5026"],
        "D-2": ["HHC-5049", "HHC-5063"],
        "D-3": ["HHC-5081", "HHC-5097"],
        "D-4": ["DAI-4012", "DRY-3089"],
    }
    
    count = 0
    for zone_id, skus in zone_product_map.items():
        for sku in skus:
            product = products.get(sku)
            if not product:
                continue
            
            # Random quantities
            import random
            qty = random.randint(5, 50)
            confidence = random.uniform(0.85, 0.99)
            
            # Determine status
            if qty == 0:
                status = InventoryStatus.OUT_OF_STOCK
            elif qty < 10:
                status = InventoryStatus.LOW_STOCK
            else:
                status = InventoryStatus.ADEQUATE
            
            inv = Inventory(
                id=f"inv-{zone_id}-{sku}",
                zone_id=zone_id,
                product_id=product.id,
                quantity_estimate=qty,
                confidence=confidence,
                status=status,
                last_observation_time=datetime.utcnow().isoformat(),
                observations_count=random.randint(10, 200),
            )
            db.add(inv)
            count += 1
    
    db.commit()
    print(f"✅ Added {count} inventory records")


def main():
    """Run all seed functions."""
    db = SessionLocal()
    
    try:
        print("\n🌱 Seeding IntelliStock database...\n")
        
        # Check if already seeded
        if db.query(Camera).count() > 0:
            print("⚠️  Database already seeded. Skipping.")
            return
        
        cameras = seed_cameras(db)
        zones = seed_zones(db, cameras)
        products = seed_products(db)
        seed_inventory(db, zones, products)
        
        print("\n✅ Database seeding complete!\n")
        print(f"   Cameras: {len(cameras)}")
        print(f"   Zones: {len(zones)}")
        print(f"   Products: {len(products)}")
        print(f"   Inventory records: {db.query(Inventory).count()}\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
