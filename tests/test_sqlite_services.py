import unittest
from datetime import date
from decimal import Decimal

from app.schemas.entry import EntryCreate, EntryUpdate
from app.schemas.food import FoodCreate
from app.schemas.goal import GoalSet
from core.db import connect, initialize_database
from services.entries import (
    copy_entries,
    create_entry,
    delete_entry,
    get_entry,
    list_entries,
    update_entry,
)
from services.errors import EntryNotFound
from services.foods import create_custom_food, search_foods
from services.goals import get_goal_for_date, set_goal


class SQLiteServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.db = await connect(":memory:")
        await initialize_database(self.db)

    async def asyncTearDown(self) -> None:
        await self.db.close()

    async def test_food_visibility_and_search(self) -> None:
        await self.db.execute(
            """
            INSERT INTO foods (
                name, source, kcal_per_100g, protein_per_100g,
                carbs_per_100g, fat_per_100g
            ) VALUES ('Chicken breast', 'usda', '165', '31', '0', '3.6')
            """
        )
        await create_custom_food(
            self.db,
            1,
            FoodCreate(
                name="Chicken wrap",
                kcal_per_100g=Decimal("190"),
                protein_per_100g=Decimal("12"),
                carbs_per_100g=Decimal("22"),
                fat_per_100g=Decimal("5"),
            ),
        )
        await create_custom_food(
            self.db,
            2,
            FoodCreate(
                name="Chicken soup",
                kcal_per_100g=Decimal("80"),
                protein_per_100g=Decimal("7"),
                carbs_per_100g=Decimal("9"),
                fat_per_100g=Decimal("2"),
            ),
        )

        foods = await search_foods(self.db, 1, "chicken")
        self.assertEqual([food.name for food in foods], ["Chicken wrap", "Chicken breast"])
        typo_matches = await search_foods(self.db, 1, "chiken breast")
        self.assertEqual([food.name for food in typo_matches], ["Chicken breast"])

    async def test_entry_crud_copy_and_ownership(self) -> None:
        food = await create_custom_food(
            self.db,
            1,
            FoodCreate(
                name="Oats",
                kcal_per_100g=Decimal("380"),
                protein_per_100g=Decimal("13"),
                carbs_per_100g=Decimal("68"),
                fat_per_100g=Decimal("7"),
            ),
        )
        logged = await create_entry(
            self.db,
            1,
            EntryCreate(
                food_id=food.id,
                meal="breakfast",
                logged_date=date(2026, 11, 4),
                quantity_g=Decimal("50"),
            ),
        )
        self.assertEqual(logged.kcal, Decimal("190.0"))
        with self.assertRaises(EntryNotFound):
            await get_entry(self.db, 2, logged.id)

        updated = await update_entry(
            self.db,
            1,
            logged.id,
            EntryUpdate(quantity_g=Decimal("100"), meal="lunch"),
        )
        self.assertEqual(updated.kcal, Decimal("380.0"))
        self.assertEqual(updated.meal, "lunch")

        copies = await copy_entries(
            self.db,
            1,
            date(2026, 11, 4),
            date(2026, 11, 5),
            meals=["lunch"],
        )
        self.assertEqual(len(copies), 1)
        self.assertEqual(copies[0].logged_date, date(2026, 11, 5))
        self.assertEqual(len(await list_entries(self.db, 1, date(2026, 11, 5))), 1)

        await delete_entry(self.db, 1, logged.id)
        with self.assertRaises(EntryNotFound):
            await get_entry(self.db, 1, logged.id)

    async def test_goal_upsert_and_date_lookup(self) -> None:
        first = GoalSet(
            calories=Decimal("2000"),
            protein_g=Decimal("120"),
            carbs_g=Decimal("220"),
            fat_g=Decimal("70"),
        )
        goal = await set_goal(self.db, 1, first, date(2026, 11, 1))
        replacement = GoalSet(
            calories=Decimal("2100"),
            protein_g=Decimal("125"),
            carbs_g=Decimal("230"),
            fat_g=Decimal("72"),
        )
        updated = await set_goal(self.db, 1, replacement, date(2026, 11, 1))

        self.assertEqual(goal.id, updated.id)
        self.assertEqual(updated.calories, Decimal("2100"))
        self.assertIsNone(await get_goal_for_date(self.db, 1, date(2026, 10, 31)))
        self.assertEqual(
            (await get_goal_for_date(self.db, 1, date(2026, 11, 4))).id,
            goal.id,
        )
