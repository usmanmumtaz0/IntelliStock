"""Inventory query operations; reconciliation remains in the service layer."""
from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from app.models.inventory import Inventory, InventoryStatus


class InventoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(
        self,
        *,
        zone_id: str | None = None,
        product_id: str | None = None,
        inventory_status: InventoryStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Inventory], int]:
        query = self.db.query(Inventory).options(
            joinedload(Inventory.product),
            joinedload(Inventory.zone),
        )
        if zone_id:
            query = query.filter(Inventory.zone_id == zone_id)
        if product_id:
            query = query.filter(Inventory.product_id == product_id)
        if inventory_status:
            query = query.filter(Inventory.status == inventory_status)
        total = query.count()
        records = query.order_by(Inventory.updated_at.desc(), Inventory.id.asc()).offset(offset).limit(limit).all()
        return records, total

    def get(self, inventory_id: str) -> Inventory | None:
        return (
            self.db.query(Inventory)
            .options(joinedload(Inventory.product), joinedload(Inventory.zone))
            .filter(Inventory.id == inventory_id)
            .first()
        )

    def by_zone(self, zone_id: str) -> list[Inventory]:
        return (
            self.db.query(Inventory)
            .options(joinedload(Inventory.product), joinedload(Inventory.zone))
            .filter(Inventory.zone_id == zone_id)
            .all()
        )

    def by_product(self, product_id: str) -> list[Inventory]:
        return (
            self.db.query(Inventory)
            .options(joinedload(Inventory.product), joinedload(Inventory.zone))
            .filter(Inventory.product_id == product_id)
            .all()
        )

    def low_stock(self) -> list[Inventory]:
        return (
            self.db.query(Inventory)
            .options(joinedload(Inventory.product), joinedload(Inventory.zone))
            .filter(Inventory.status.in_([InventoryStatus.LOW_STOCK, InventoryStatus.OUT_OF_STOCK]))
            .all()
        )
