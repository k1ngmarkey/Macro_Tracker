from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(slots=True)
class Goal:
    id: int
    user_id: int
    effective_from: date
    calories: Decimal
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal
