from __future__ import annotations

import os
from pathlib import Path
from typing import Final

import aiosqlite

_PROJECT_ROOT: Final = Path(__file__).resolve().parent.parent
_SCHEMA_VERSION: Final = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS foods (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    brand TEXT,
    barcode TEXT,
    source TEXT NOT NULL,
    created_by INTEGER,
    kcal_per_100g TEXT NOT NULL,
    protein_per_100g TEXT NOT NULL,
    carbs_per_100g TEXT NOT NULL,
    fat_per_100g TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_foods_barcode ON foods(barcode);
CREATE INDEX IF NOT EXISTS ix_foods_created_by ON foods(created_by);
CREATE INDEX IF NOT EXISTS ix_foods_name ON foods(name COLLATE NOCASE);

CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    food_id INTEGER NOT NULL REFERENCES foods(id),
    meal TEXT NOT NULL,
    logged_date TEXT NOT NULL,
    quantity_g TEXT NOT NULL,
    kcal TEXT NOT NULL,
    protein_g TEXT NOT NULL,
    carbs_g TEXT NOT NULL,
    fat_g TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_entries_user_date ON entries(user_id, logged_date);
CREATE INDEX IF NOT EXISTS ix_entries_food_id ON entries(food_id);

CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    effective_from TEXT NOT NULL,
    calories TEXT NOT NULL,
    protein_g TEXT NOT NULL,
    carbs_g TEXT NOT NULL,
    fat_g TEXT NOT NULL,
    UNIQUE(user_id, effective_from)
);
"""


def _trigrams(value: str) -> set[str]:
    text = f"  {value.casefold()} "
    return {text[index : index + 3] for index in range(len(text) - 2)}


def _trigram_similarity(left: str, right: str) -> float:
    left_grams = _trigrams(left)
    right_grams = _trigrams(right)
    if not left_grams or not right_grams:
        return 0.0
    return len(left_grams & right_grams) / len(left_grams | right_grams)


def database_path() -> Path:
    configured = os.environ.get("DATABASE_PATH", "macro_tracker.db")
    if configured == ":memory:":
        return Path(configured)
    path = Path(configured).expanduser()
    return path if path.is_absolute() else _PROJECT_ROOT / path


async def connect(path: str | Path | None = None) -> aiosqlite.Connection:
    database = Path(path) if path is not None else database_path()
    if str(database) != ":memory:":
        database.parent.mkdir(parents=True, exist_ok=True)

    connection = await aiosqlite.connect(str(database))
    connection.row_factory = aiosqlite.Row
    for statement in ("PRAGMA foreign_keys = ON", "PRAGMA busy_timeout = 5000"):
        cursor = await connection.execute(statement)
        await cursor.close()
    await connection.create_function(
        "trigram_similarity", 2, _trigram_similarity, deterministic=True
    )
    return connection


async def initialize_database(connection: aiosqlite.Connection) -> None:
    cursor = await connection.execute("PRAGMA user_version")
    try:
        row = await cursor.fetchone()
    finally:
        await cursor.close()
    if row is None:
        raise RuntimeError("SQLite did not return the schema version")
    version = row[0]

    if version >= _SCHEMA_VERSION:
        return

    await connection.executescript(SCHEMA)
    await connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
    await connection.commit()
