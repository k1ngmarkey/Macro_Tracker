from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class GoalSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calories: Decimal
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal
