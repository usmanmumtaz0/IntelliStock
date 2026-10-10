"""
Product endpoints for CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.core.security import require_roles
from sqlalchemy.exc import IntegrityError
from app.models.inventory import Inventory, InventoryStatus
from app.models.inventory_history import InventoryHistory
from app.models.delivery import ZoneProductMapping
from app.models.alert import Alert
from app.models.event import InventoryEvent
from app.services.operations import audit, stock_state, stock_changed
from app.services.outbox import enqueue

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.get("", response_model=List[ProductResponse])
def list_products(db: Session = Depends(get_db)):
    """List all products."""
    products = db.query(Product).all()
    return products


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: str, db: Session = Depends(get_db)):
    """Get a specific product by ID."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("admin", "manager"))],
)
def create_product(product: ProductCreate, db: Session = Depends(get_db), user=Depends(require_roles("admin", "manager"))):
    """Create a new product."""
    # Check for duplicate SKU
    existing = db.query(Product).filter(Product.sku == product.sku).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SKU already exists")
    
    db_product = Product(**product.dict())
    db.add(db_product)
    try:
        db.flush()
        audit(db, user, "create", "product", db_product.id, new=product.model_dump())
        enqueue(db, "configuration_updated", {"resource": "products"})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "SKU already exists")
    db.refresh(db_product)
    return db_product


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    dependencies=[Depends(require_roles("admin", "manager"))],
)
def update_product(product_id: str, product: ProductUpdate, db: Session = Depends(get_db), user=Depends(require_roles("admin", "manager"))):
    """Update a product."""
    db_product = db.query(Product).filter(Product.id == product_id).with_for_update().first()
    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    update_data = product.dict(exclude_unset=True)
    old = {field: getattr(db_product, field) for field in update_data}
    for field, value in update_data.items():
        setattr(db_product, field, value)
    
    if "low_stock_threshold" in update_data:
        for inv in db.query(Inventory).filter_by(product_id=product_id).order_by(Inventory.id).with_for_update().all():
            if inv.status in (InventoryStatus.ADEQUATE, InventoryStatus.LOW_STOCK, InventoryStatus.OUT_OF_STOCK):
                inv.status = stock_state(inv.quantity_estimate, db_product.low_stock_threshold)
                stock_changed(db, inv)
    audit(db, user, "update", "product", product_id, old, update_data)
    enqueue(db, "configuration_updated", {"resource": "products"})
    db.commit()
    db.refresh(db_product)
    return db_product


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("admin"))],
)
def delete_product(product_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    """Delete a product."""
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    for model in (Inventory, InventoryHistory, ZoneProductMapping, Alert, InventoryEvent):
        if db.query(model).filter_by(product_id=product_id).first():
            raise HTTPException(409, "Product has inventory, mappings or history and cannot be deleted")
    audit(db, user, "delete", "product", product_id, old={"sku": db_product.sku})
    db.delete(db_product)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Product is still referenced")
    return None
