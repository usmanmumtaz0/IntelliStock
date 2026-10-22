import json

import pytest

from app.models import AuditLog, Product
from app.database import SessionLocal
from app.models.user import User, UserRole
from scripts.sync_model_catalog import CATALOG_METADATA, sync_catalog


@pytest.fixture
def db_session():
    with SessionLocal() as db:
        yield db
        db.rollback()


def _admin(db, email="catalog-admin@example.com"):
    user = User(
        username="catalog-admin",
        email=email,
        hashed_password="test-hash",
        role=UserRole.ADMIN,
        is_active=True,
        signup_pending=False,
    )
    db.add(user)
    db.flush()
    return user


def _manifest(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "model_version": "catalog-test",
        "sha256": "a" * 64,
        "task": "detect",
        "classes": [
            {"class_id": class_id, "label": f"Product {class_id}", "sku": f"MODEL-{class_id}"}
            for class_id in sorted(CATALOG_METADATA)
        ],
    }), encoding="utf-8")
    return path


def test_model_catalog_sync_is_complete_audited_and_idempotent(db_session, tmp_path):
    admin = _admin(db_session)
    manifest = _manifest(tmp_path)

    first = sync_catalog(db_session, admin.email, manifest)
    db_session.flush()
    assert first == {
        "model_version": "catalog-test",
        "classes": 25,
        "created": 25,
        "existing": 0,
    }
    assert db_session.query(Product).filter(Product.sku.like("MODEL-%")).count() == 25
    assert db_session.query(AuditLog).filter_by(action="create_model_catalog").count() == 25

    second = sync_catalog(db_session, admin.email, manifest)
    assert second["created"] == 0
    assert second["existing"] == 25


def test_model_catalog_sync_rejects_collisions_without_overwriting(db_session, tmp_path):
    admin = _admin(db_session, "collision-admin@example.com")
    db_session.add(Product(sku="MODEL-0", name="Existing retailer product"))
    db_session.flush()

    with pytest.raises(ValueError, match="differs in reviewed fields"):
        sync_catalog(db_session, admin.email, _manifest(tmp_path))
    assert db_session.query(Product).filter_by(sku="MODEL-0").one().name == "Existing retailer product"
