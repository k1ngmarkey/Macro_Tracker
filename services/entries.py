# Markus Arcaro

"""Logging, editing, deleting and copying food entries.

Entries snapshot their macros at log time, so later corrections to a food
don't silently rewrite history. The one deliberate exception: editing an
entry's quantity re-reads the food and recomputes (see update_entry).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import aiosqlite

from app.models.entry import Entry
from app.schemas.entry import EntryCreate, EntryUpdate
from app.services import foods as foods_service
from app.services.errors import EntryNotFound, FoodNotFound, InvalidInput
from app.services.macros import scale_macros


def _entry_from_row(row: aiosqlite.Row) -> Entry:
    return Entry(
        id=row["id"],
        user_id=row["user_id"],
        food_id=row["food_id"],
        meal=row["meal"],
        logged_date=date.fromisoformat(row["logged_date"]),
        quantity_g=Decimal(row["quantity_g"]),
        kcal=Decimal(row["kcal"]),
        protein_g=Decimal(row["protein_g"]),
        carbs_g=Decimal(row["carbs_g"]),
        fat_g=Decimal(row["fat_g"]),
    )


async def create_entry(
    session: aiosqlite.Connection, user_id: int, data: EntryCreate
) -> Entry:
    food = await foods_service.get_food(session, user_id, data.food_id)
    macros = scale_macros(food, data.quantity_g)

    values = (
        user_id,
        food.id,
        data.meal,
        data.logged_date.isoformat(),
        str(data.quantity_g),
        *(str(value) for value in macros.as_columns().values()),
    )
    cursor = await session.execute(
        """
        INSERT INTO entries (
            user_id, food_id, meal, logged_date, quantity_g,
            kcal, protein_g, carbs_g, fat_g
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        values,
    )
    entry_id = cursor.lastrowid
    await cursor.close()
    if entry_id is None:
        raise RuntimeError("SQLite did not return the new entry ID")
    return Entry(
        id=entry_id,
        user_id=user_id,
        food_id=food.id,
        meal=data.meal,
        logged_date=data.logged_date,
        quantity_g=data.quantity_g,
        **macros.as_columns(),
    )


async def get_entry(
    session: aiosqlite.Connection, user_id: int, entry_id: int
) -> Entry:
    """Ownership is enforced in the query itself: someone else's entry looks
    exactly like one that doesn't exist."""
    cursor = await session.execute(
        "SELECT * FROM entries WHERE id = ? AND user_id = ?",
        (entry_id, user_id),
    )
    try:
        row = await cursor.fetchone()
    finally:
        await cursor.close()
    if row is None:
        raise EntryNotFound(entry_id)
    return _entry_from_row(row)


async def list_entries(
    session: aiosqlite.Connection, user_id: int, day: date
) -> list[Entry]:
    cursor = await session.execute(
        "SELECT * FROM entries WHERE user_id = ? AND logged_date = ? ORDER BY id",
        (user_id, day.isoformat()),
    )
    try:
        rows = await cursor.fetchall()
    finally:
        await cursor.close()
    return [_entry_from_row(row) for row in rows]


async def update_entry(
    session: aiosqlite.Connection, user_id: int, entry_id: int, data: EntryUpdate
) -> Entry:
    """Partial update (meal, logged_date, quantity_g).

    Changing quantity recomputes macros from the food's *current* values.
    The alternative, scaling the old snapshot by new/old, drifts through
    repeated rounding. Moving an entry to another meal or date never touches
    its macros.
    """
    entry = await get_entry(session, user_id, entry_id)
    changes = data.model_dump(exclude_unset=True)

    if any(value is None for value in changes.values()):
        raise InvalidInput("Fields can't be set to null")

    if "quantity_g" in changes:
        # Not get_food(): the user already logged this food, so editing must
        # keep working even if it's no longer in their visible set.
        cursor = await session.execute(
            "SELECT * FROM foods WHERE id = ?", (entry.food_id,)
        )
        try:
            row = await cursor.fetchone()
        finally:
            await cursor.close()
        if row is None:
            raise FoodNotFound(entry.food_id)
        food = foods_service.food_from_row(row)
        macros = scale_macros(food, changes["quantity_g"])
        changes.update(macros.as_columns())

    if not changes:
        return entry

    logged_date = changes.get("logged_date", entry.logged_date)
    column_values = {
        "meal": changes.get("meal", entry.meal),
        "logged_date": logged_date.isoformat()
        if isinstance(logged_date, date)
        else logged_date,
        "quantity_g": changes.get("quantity_g", entry.quantity_g),
        "kcal": changes.get("kcal", entry.kcal),
        "protein_g": changes.get("protein_g", entry.protein_g),
        "carbs_g": changes.get("carbs_g", entry.carbs_g),
        "fat_g": changes.get("fat_g", entry.fat_g),
    }
    cursor = await session.execute(
        """
        UPDATE entries
        SET meal = ?, logged_date = ?, quantity_g = ?, kcal = ?,
            protein_g = ?, carbs_g = ?, fat_g = ?
        WHERE id = ? AND user_id = ?
        """,
        (
            column_values["meal"],
            column_values["logged_date"],
            str(column_values["quantity_g"]),
            str(column_values["kcal"]),
            str(column_values["protein_g"]),
            str(column_values["carbs_g"]),
            str(column_values["fat_g"]),
            entry_id,
            user_id,
        ),
    )
    await cursor.close()
    return Entry(id=entry.id, user_id=user_id, food_id=entry.food_id, **column_values)


async def delete_entry(
    session: aiosqlite.Connection, user_id: int, entry_id: int
) -> None:
    await get_entry(session, user_id, entry_id)
    cursor = await session.execute(
        "DELETE FROM entries WHERE id = ? AND user_id = ?", (entry_id, user_id)
    )
    await cursor.close()


async def copy_entries(
    session: aiosqlite.Connection,
    user_id: int,
    from_day: date,
    to_day: date,
    *,
    meals: list[str] | None = None,
) -> list[Entry]:
    """Copy one day's entries (optionally only some meals) onto another day.

    Snapshots are copied as-is, so the copy matches the original exactly.
    Not idempotent: calling twice duplicates. Have the client confirm, or
    check list_entries(to_day) first.
    """
    if from_day == to_day:
        raise InvalidInput("Source and target dates must differ")

    query = "SELECT * FROM entries WHERE user_id = ? AND logged_date = ?"
    parameters: list[object] = [user_id, from_day.isoformat()]
    if meals:
        query += f" AND meal IN ({','.join('?' for _ in meals)})"
        parameters.extend(meals)
    query += " ORDER BY id"
    cursor = await session.execute(query, parameters)
    try:
        originals = await cursor.fetchall()
    finally:
        await cursor.close()

    copies: list[Entry] = []
    for row in originals:
        original = _entry_from_row(row)
        cursor = await session.execute(
            """
            INSERT INTO entries (
                user_id, food_id, meal, logged_date, quantity_g,
                kcal, protein_g, carbs_g, fat_g
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                original.food_id,
                original.meal,
                to_day.isoformat(),
                str(original.quantity_g),
                str(original.kcal),
                str(original.protein_g),
                str(original.carbs_g),
                str(original.fat_g),
            ),
        )
        entry_id = cursor.lastrowid
        await cursor.close()
        if entry_id is None:
            raise RuntimeError("SQLite did not return the copied entry ID")
        copies.append(
            Entry(
                id=entry_id,
                user_id=user_id,
                food_id=original.food_id,
                meal=original.meal,
                logged_date=to_day,
                quantity_g=original.quantity_g,
                kcal=original.kcal,
                protein_g=original.protein_g,
                carbs_g=original.carbs_g,
                fat_g=original.fat_g,
            )
        )
    return copies