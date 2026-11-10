from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.dates import daterange, today_for
from app.services.errors import InvalidQuantity
from app.services.macros import Macros, scale_macros

D = Decimal


def food(kcal, p, c, f):
    return SimpleNamespace(
        kcal_per_100g=D(kcal),
        protein_per_100g=D(p),
        carbs_per_100g=D(c),
        fat_per_100g=D(f),
    )


CHICKEN = food("165", "31.0", "0", "3.6")  # roughly cooked chicken breast


def test_scales_linearly_from_per_100g():
    m = scale_macros(CHICKEN, D("150"))
    assert m == Macros(D("247.5"), D("46.5"), D("0.0"), D("5.4"))


def test_100g_returns_the_per_100g_values():
    m = scale_macros(CHICKEN, D("100"))
    assert (m.kcal, m.protein_g, m.fat_g) == (D("165.0"), D("31.0"), D("3.6"))


def test_rounds_half_up_not_bankers():
    # 25 g of a 1 g-fat/100 g food = 0.25 -> half-up gives 0.3 (banker's: 0.2)
    assert scale_macros(food(0, 0, 0, "1"), D("25")).fat_g == D("0.3")
    # 5 g -> 0.05 -> 0.1
    assert scale_macros(food(0, 0, 0, "1"), D("5")).fat_g == D("0.1")


def test_accepts_float_input_without_artefacts():
    assert scale_macros(CHICKEN, 150.0) == scale_macros(CHICKEN, D("150"))


@pytest.mark.parametrize("bad", [0, -5, D("10001")])
def test_rejects_nonsense_quantities(bad):
    with pytest.raises(InvalidQuantity):
        scale_macros(CHICKEN, bad)


def test_macros_add_subtract_total():
    a = Macros(D(100), D(10), D(5), D(2))
    b = Macros(D(50), D(1), D(1), D(1))
    assert a + b == Macros(D(150), D(11), D(6), D(3))
    assert a - b == Macros(D(50), D(9), D(4), D(1))
    assert Macros.total([a, b, b]) == Macros(D(200), D(12), D(7), D(4))
    assert Macros.total([]) == Macros()


def test_from_values_handles_null_sums():
    assert Macros.from_values(None, None, None, None) == Macros()


def test_as_columns_matches_entry_column_names():
    assert set(Macros().as_columns()) == {"kcal", "protein_g", "carbs_g", "fat_g"}


def test_daterange_is_inclusive():
    days = list(daterange(date(2026, 2, 27), date(2026, 3, 2)))
    assert days[0] == date(2026, 2, 27) and days[-1] == date(2026, 3, 2)
    assert len(days) == 4


def test_today_for_falls_back_on_bad_timezone():
    assert isinstance(today_for("Not/AZone"), date)
    assert isinstance(today_for(None), date)
    assert isinstance(today_for(""), date)
