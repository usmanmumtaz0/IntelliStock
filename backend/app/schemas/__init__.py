# Schemas package
from app.schemas.camera import CameraCreate, CameraUpdate, CameraResponse
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.schemas.inventory import InventoryResponse, InventoryListResponse

__all__ = [
    "CameraCreate",
    "CameraUpdate",
    "CameraResponse",
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    "InventoryResponse",
    "InventoryListResponse",
]

