from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class EntryCreate(BaseModel):
    food_id: int
    meal: str
    logged_date: date
    quantity_g: Decimal


class EntryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meal: str | None = None
    logged_date: date | None = None
    quantity_g: Decimal | None = None
