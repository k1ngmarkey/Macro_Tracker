"""Daily macro goals with history.

A goal applies from `effective_from` until a later goal replaces it, so
looking back at March shows March's targets, not today's.
"""

from __future__ import annotations

from datetime import date

import aiosqlite

from app.models.goal import Goal
from app.schemas.goal import GoalSet
from app.services.errors import InvalidInput
from app.services.macros import to_decimal


def _goal_from_row(row: aiosqlite.Row) -> Goal:
    return Goal(
        id=row["id"],
        user_id=row["user_id"],
        effective_from=date.fromisoformat(row["effective_from"]),
        calories=to_decimal(row["calories"]),
        protein_g=to_decimal(row["protein_g"]),
        carbs_g=to_decimal(row["carbs_g"]),
        fat_g=to_decimal(row["fat_g"]),
    )


async def get_goal_for_date(
    session: aiosqlite.Connection, user_id: int, day: date
) -> Goal | None:
    """The goal in force on `day`, or None if the user hadn't set one yet."""
    cursor = await session.execute(
        """
        SELECT * FROM goals
        WHERE user_id = ? AND effective_from <= ?
        ORDER BY effective_from DESC
        LIMIT 1
        """,
        (user_id, day.isoformat()),
    )
    try:
        row = await cursor.fetchone()
    finally:
        await cursor.close()
    return _goal_from_row(row) if row is not None else None


async def set_goal(
    session: aiosqlite.Connection, user_id: int, data: GoalSet, effective_from: date
) -> Goal:
    """Set the goal starting `effective_from` (router passes the user's local
    today). Setting twice on the same date replaces rather than duplicates;
    the UNIQUE (user_id, effective_from) constraint backs this up."""
    if to_decimal(data.calories) <= 0:
        raise InvalidInput("Calories must be greater than 0")
    if any(to_decimal(v) < 0 for v in (data.protein_g, data.carbs_g, data.fat_g)):
        raise InvalidInput("Macro targets can't be negative")

    cursor = await session.execute(
        """
        INSERT INTO goals (
            user_id, effective_from, calories, protein_g, carbs_g, fat_g
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, effective_from) DO UPDATE SET
            calories = excluded.calories,
            protein_g = excluded.protein_g,
            carbs_g = excluded.carbs_g,
            fat_g = excluded.fat_g
        RETURNING *
        """,
        (
            user_id,
            effective_from.isoformat(),
            str(to_decimal(data.calories)),
            str(to_decimal(data.protein_g)),
            str(to_decimal(data.carbs_g)),
            str(to_decimal(data.fat_g)),
        ),
    )
    try:
        row = await cursor.fetchone()
    finally:
        await cursor.close()
    if row is None:
        raise RuntimeError("SQLite did not return the saved goal")
    return _goal_from_row(row)