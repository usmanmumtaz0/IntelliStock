import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models import Base, Product, Camera, Inventory
from app.models.inventory_history import InventoryHistory
from app.models.user import User, UserRole
from scripts.seed_demo_store import seed


def test_demo_seed_is_audited_disabled_and_cannot_overwrite():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(User(email="demo@example.com", username="demo", hashed_password="unused", role=UserRole.ADMIN,
                    is_active=True, signup_pending=False))
        db.add(Product(sku="existing", name="Preserve me"))
        db.commit()
        with db.begin():
            result = seed(db, "demo@example.com")
        assert result["products"] == 30
        assert sum(result["states"].values()) == 30
        assert all(result["states"].values())
        assert db.query(Product).count() == 31
        assert db.query(Camera).count() == 4
        assert all(not c.is_active and c.source_url is None for c in db.query(Camera))
        assert db.query(InventoryHistory).count() == 30
        assert all(i.confidence == 0 and i.observations_count == 0 for i in db.query(Inventory))
        with pytest.raises(ValueError, match="already exist"):
            seed(db, "demo@example.com")
        db.rollback()
        assert db.query(Product).count() == 31
    engine.dispose()
