"""Food search, lookup and custom-food creation.

Visibility rule: a user sees global foods (created_by IS NULL) plus their own.
"""

from __future__ import annotations

import re
from decimal import Decimal

import aiosqlite

from app.models.food import Food
from app.schemas.food import FoodCreate
from app.services.errors import FoodNotFound, InvalidInput
from app.services.macros import to_decimal

MIN_QUERY_LEN = 2
MAX_RESULTS = 50
MAX_TOKENS = 6
MAX_KCAL_PER_100G = Decimal(900)  # pure fat is ~884; above this is a typo
MAX_MACRO_G_PER_100G = Decimal(100)  # can't have >100 g of nutrient in 100 g


def food_from_row(row: aiosqlite.Row) -> Food:
    return Food(
        id=row["id"],
        name=row["name"],
        brand=row["brand"],
        barcode=row["barcode"],
        source=row["source"],
        created_by=row["created_by"],
        kcal_per_100g=to_decimal(row["kcal_per_100g"]),
        protein_per_100g=to_decimal(row["protein_per_100g"]),
        carbs_per_100g=to_decimal(row["carbs_per_100g"]),
        fat_per_100g=to_decimal(row["fat_per_100g"]),
    )


def normalize_barcode(raw: str) -> str:
    """Digits only, zero-padded to 13 (UPC-A and EAN-13 then compare equal).

    Use the same function when importing foods, or lookups will miss.
    """
    digits = re.sub(r"\D", "", raw or "")
    if not 8 <= len(digits) <= 14:
        raise InvalidInput("Barcode must be 8-14 digits")
    return digits.zfill(13)


async def search_foods(
    session: aiosqlite.Connection, user_id: int, query: str, *, limit: int = 20
) -> list[Food]:
    """Search by name.

    Matching: every word must appear somewhere in the name (so "chicken
    breast" finds USDA's "Chicken, breast, raw"), OR the whole query is
    trigram-similar (typo tolerance; registered by the SQLite connection).

    Ranking: exact name, then prefix, then the rest; within a tier your own
    foods first, then USDA, then everything else; then trigram similarity;
    then shorter names (generic "Banana" before "Banana bread, frosted").
    """
    q = query.strip().lower()
    if len(q) < MIN_QUERY_LEN:
        return []
    limit = max(1, min(limit, MAX_RESULTS))

    tokens = q.split()[:MAX_TOKENS]
    all_tokens = " AND ".join("instr(lower(name), ?) > 0" for _ in tokens)
    sql = f"""
        SELECT * FROM foods
        WHERE (created_by IS NULL OR created_by = ?)
          AND (({all_tokens}) OR trigram_similarity(name, ?) >= 0.3)
        ORDER BY
          CASE
            WHEN lower(name) = ? THEN 0
            WHEN substr(lower(name), 1, length(?)) = ? THEN 1
            ELSE 2
          END,
          CASE
            WHEN created_by = ? THEN 0
            WHEN source = 'usda' THEN 1
            ELSE 2
          END,
          trigram_similarity(name, ?) DESC,
          length(name),
          id
        LIMIT ?
    """
    parameters = (
        user_id,
        *tokens,
        q,
        q,
        q,
        q,
        user_id,
        q,
        limit,
    )
    cursor = await session.execute(sql, parameters)
    try:
        rows = await cursor.fetchall()
    finally:
        await cursor.close()
    return [food_from_row(row) for row in rows]


async def get_food(
    session: aiosqlite.Connection, user_id: int, food_id: int
) -> Food:
    cursor = await session.execute(
        """
        SELECT * FROM foods
        WHERE id = ? AND (created_by IS NULL OR created_by = ?)
        """,
        (food_id, user_id),
    )
    try:
        row = await cursor.fetchone()
    finally:
        await cursor.close()
    if row is None:
        raise FoodNotFound(food_id)
    return food_from_row(row)


async def find_by_barcode(
    session: aiosqlite.Connection, user_id: int, barcode: str
) -> Food | None:
    """Local lookup only. On None, the router can fall back to Open Food Facts
    and insert the result via an import function so the next scan is local."""
    code = normalize_barcode(barcode)
    cursor = await session.execute(
        """
        SELECT * FROM foods
        WHERE barcode = ? AND (created_by IS NULL OR created_by = ?)
        ORDER BY (created_by IS NULL) DESC, id
        LIMIT 1
        """,
        (code, user_id),
    )
    try:
        row = await cursor.fetchone()
    finally:
        await cursor.close()
    return food_from_row(row) if row is not None else None


def _validate_nutrition(food: FoodCreate) -> None:
    kcal = to_decimal(food.kcal_per_100g)
    macros = [
        to_decimal(food.protein_per_100g),
        to_decimal(food.carbs_per_100g),
        to_decimal(food.fat_per_100g),
    ]
    if kcal < 0 or any(m < 0 for m in macros):
        raise InvalidInput("Nutrition values can't be negative")
    if kcal > MAX_KCAL_PER_100G:
        raise InvalidInput(
            f"{kcal} kcal per 100 g is implausible (max {MAX_KCAL_PER_100G}). "
            "Did you enter per-serving values?"
        )
    if any(m > MAX_MACRO_G_PER_100G for m in macros) or sum(macros) > MAX_MACRO_G_PER_100G:
        raise InvalidInput(
            "Protein + carbs + fat can't exceed 100 g per 100 g of food. "
            "Did you enter per-serving values?"
        )


async def create_custom_food(
    session: aiosqlite.Connection, user_id: int, data: FoodCreate
) -> Food:
    """Create a food visible only to this user. Values are per 100 g."""
    _validate_nutrition(data)

    name = data.name.strip()
    if not name:
        raise InvalidInput("Name is required")

    brand = (data.brand or "").strip() or None
    barcode = normalize_barcode(data.barcode) if data.barcode else None
    nutrition = {
        "kcal_per_100g": to_decimal(data.kcal_per_100g),
        "protein_per_100g": to_decimal(data.protein_per_100g),
        "carbs_per_100g": to_decimal(data.carbs_per_100g),
        "fat_per_100g": to_decimal(data.fat_per_100g),
    }
    cursor = await session.execute(
        """
        INSERT INTO foods (
            name, brand, barcode, source, created_by,
            kcal_per_100g, protein_per_100g, carbs_per_100g, fat_per_100g
        ) VALUES (?, ?, ?, 'user', ?, ?, ?, ?, ?)
        """,
        (
            name,
            brand,
            barcode,
            user_id,
            *(str(value) for value in nutrition.values()),
        ),
    )
    food_id = cursor.lastrowid
    await cursor.close()
    if food_id is None:
        raise RuntimeError("SQLite did not return the new food ID")
    return Food(
        id=food_id,
        name=name,
        brand=brand,
        barcode=barcode,
        source="user",
        created_by=user_id,
        **nutrition,
    )