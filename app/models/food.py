from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class Food:
    id: int
    name: str
    source: str
    kcal_per_100g: Decimal
    protein_per_100g: Decimal
    carbs_per_100g: Decimal
    fat_per_100g: Decimal
    brand: str | None = None
    barcode: str | None = None
    created_by: int | None = None
