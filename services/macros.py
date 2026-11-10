"""Pure macro math. No database, no I/O: the easiest code here to test.

Foods store nutrients per 100 g. An entry's macros are
    per_100g * quantity_g / 100
rounded half-up to one decimal place, then snapshotted onto the entry.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from app.services.errors import InvalidQuantity

if TYPE_CHECKING:
    from app.models.food import Food

_ONE_DP = Decimal("0.1")
_HUNDRED = Decimal(100)
ZERO = Decimal(0)

# Sanity ceiling for one entry. A typo like 5000 instead of 500 g should fail
# loudly instead of silently adding 10,000 kcal to someone's day.
MAX_QUANTITY_G = Decimal(10_000)


def to_decimal(value: object) -> Decimal:
    """Coerce int/float/str/Decimal to Decimal without float artefacts."""
    return value if isinstance(value, Decimal) else Decimal(str(value))


def round_1dp(value: Decimal) -> Decimal:
    return value.quantize(_ONE_DP, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class Macros:
    kcal: Decimal = ZERO
    protein_g: Decimal = ZERO
    carbs_g: Decimal = ZERO
    fat_g: Decimal = ZERO

    def __add__(self, other: Macros) -> Macros:
        return Macros(
            self.kcal + other.kcal,
            self.protein_g + other.protein_g,
            self.carbs_g + other.carbs_g,
            self.fat_g + other.fat_g,
        )

    def __sub__(self, other: Macros) -> Macros:
        return Macros(
            self.kcal - other.kcal,
            self.protein_g - other.protein_g,
            self.carbs_g - other.carbs_g,
            self.fat_g - other.fat_g,
        )

    @classmethod
    def from_values(cls, *values: object) -> Macros:
        """Build from DB row values (None -> 0, float/int -> Decimal)."""
        return cls(*(ZERO if v is None else to_decimal(v) for v in values))

    @classmethod
    def total(cls, items: Iterable[Macros]) -> Macros:
        result = cls()
        for item in items:
            result = result + item
        return result

    def as_columns(self) -> dict[str, Decimal]:
        """Keys match the Entry columns, so `Entry(**macros.as_columns())` works."""
        return asdict(self)


def scale_macros(food: Food, quantity_g: object) -> Macros:
    """Macros for `quantity_g` grams of `food`."""
    qty = to_decimal(quantity_g)
    if qty <= 0:
        raise InvalidQuantity("Quantity must be greater than 0 g")
    if qty > MAX_QUANTITY_G:
        raise InvalidQuantity(f"Quantity can't exceed {MAX_QUANTITY_G} g")

    factor = qty / _HUNDRED
    return Macros(
        kcal=round_1dp(to_decimal(food.kcal_per_100g) * factor),
        protein_g=round_1dp(to_decimal(food.protein_per_100g) * factor),
        carbs_g=round_1dp(to_decimal(food.carbs_per_100g) * factor),
        fat_g=round_1dp(to_decimal(food.fat_per_100g) * factor),
    )