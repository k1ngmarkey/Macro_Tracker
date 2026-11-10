from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class FoodCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    brand: str | None = None
    barcode: str | None = None
    kcal_per_100g: Decimal
    protein_per_100g: Decimal
    carbs_per_100g: Decimal
    fat_per_100g: Decimal
