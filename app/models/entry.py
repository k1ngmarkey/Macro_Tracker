from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(slots=True)
class Entry:
    id: int
    user_id: int
    food_id: int
    meal: str
    logged_date: date
    quantity_g: Decimal
    kcal: Decimal
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal
