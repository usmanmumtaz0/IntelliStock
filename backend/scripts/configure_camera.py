"""Admin CLI: validate and configure a camera and SKU-mapped shelf regions."""
import argparse
import json
from pathlib import Path
from pydantic import BaseModel, Field, model_validator
from app.database import SessionLocal
from app.models import Camera, Product, ShelfZone, ZoneProductMapping
from app.schemas.zone import validate_polygon


class Mapping(BaseModel):
    class_id: int = Field(ge=0)
    sku: str = Field(min_length=1)
    allow_empty: bool = False


class Region(BaseModel):
    name: str = Field(min_length=1)
    polygon: list[tuple[float, float]] = Field(min_length=3)
    products: list[Mapping] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_region(self):
        validate_polygon(self.polygon)
        if any(not 0 <= v <= 1 for point in self.polygon for v in point):
            raise ValueError("Polygon coordinates must be normalized to [0, 1]")
        if len({p.class_id for p in self.products}) != len(self.products):
            raise ValueError("Duplicate class IDs in region")
        if len({p.sku for p in self.products}) != len(self.products):
            raise ValueError("One class per SKU per region is required")
        area = sum(x * self.polygon[(i+1) % len(self.polygon)][1] -
                   y * self.polygon[(i+1) % len(self.polygon)][0]
                   for i, (x, y) in enumerate(self.polygon))
        if abs(area) < 0.0001:
            raise ValueError("Polygon has zero area")
        return self


class Configuration(BaseModel):
    name: str = Field(min_length=1)
    location: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    fps: int = Field(default=2, ge=1, le=30)
    zones: list[Region] = Field(min_length=1)


def configure(db, config):
    if len({z.name for z in config.zones}) != len(config.zones):
        raise ValueError("Duplicate zone names")
    # Create-only: never replace an existing camera or mapping implicitly.
    if db.query(Camera).filter_by(name=config.name).first():
        raise ValueError("Camera name already exists; use a new name")
    camera = Camera(name=config.name, location=config.location, source_url=config.source_url, fps=config.fps)
    db.add(camera)
    db.flush()
    for region in config.zones:
        zone = ShelfZone(camera_id=camera.id, name=region.name, roi_polygon=json.dumps(region.polygon))
        db.add(zone)
        db.flush()
        for mapping in region.products:
            product = db.query(Product).filter_by(sku=mapping.sku).first()
            if not product:
                raise ValueError(f"Unknown SKU: {mapping.sku}; create the product first")
            db.add(ZoneProductMapping(zone_id=zone.id, product_id=product.id,
                class_id=mapping.class_id, allow_empty=mapping.allow_empty))
    db.flush()
    return camera.id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    config = Configuration.model_validate_json(args.config.read_text(encoding="utf-8"))
    with SessionLocal() as db:
        with db.begin():
            camera_id = configure(db, config)
    print(f"Camera configured: {camera_id}")


if __name__ == "__main__":
    main()
