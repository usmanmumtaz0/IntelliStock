"""Validated normalized shelf geometry and model-class assignments."""
import math
from pydantic import BaseModel, ConfigDict, Field, model_validator


class MappingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    class_id: int = Field(ge=0, strict=True)
    product_id: str = Field(min_length=1, max_length=36)
    allow_empty: bool = False


def validate_polygon(points):
    if any(not math.isfinite(v) or not 0 <= v <= 1 for point in points for v in point):
        raise ValueError("ROI coordinates must be finite and normalized to [0, 1]")
    if len(set(points)) != len(points):
        raise ValueError("ROI points must be distinct; do not repeat the first point")
    area = sum(x * points[(i+1) % len(points)][1] - y * points[(i+1) % len(points)][0]
               for i, (x, y) in enumerate(points))
    if abs(area) < 0.0001:
        raise ValueError("ROI must have non-zero area")
    def cross(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
    def on_segment(a, b, c):
        return min(a[0], b[0]) <= c[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= c[1] <= max(a[1], b[1])
    for i in range(len(points)):
        a, b = points[i], points[(i+1) % len(points)]
        for j in range(i+1, len(points)):
            if j == i+1 or (i == 0 and j == len(points)-1):
                continue
            c, d = points[j], points[(j+1) % len(points)]
            x, y, z, w = cross(a,b,c), cross(a,b,d), cross(c,d,a), cross(c,d,b)
            if (x*y < 0 and z*w < 0) or any((v == 0 and on_segment(p,q,r)) for v,p,q,r in
                    ((x,a,b,c), (y,a,b,d), (z,c,d,a), (w,c,d,b))):
                raise ValueError("ROI edges cannot intersect")
    return points


class ZoneInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    camera_id: str = Field(min_length=1, max_length=36)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=512)
    polygon: list[tuple[float, float]] = Field(min_length=3, max_length=32)
    detection_confidence_threshold: float = Field(default=0.6, ge=0.6, le=1, allow_inf_nan=False)
    products: list[MappingInput] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_region(self):
        validate_polygon(self.polygon)
        if len({p.class_id for p in self.products}) != len(self.products):
            raise ValueError("Duplicate model class IDs")
        if len({p.product_id for p in self.products}) != len(self.products):
            raise ValueError("Only one model class per product per zone is allowed")
        return self
