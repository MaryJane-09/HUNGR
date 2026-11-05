from backend.planner import BudgetTooLow, build_fallback, minimum_budget, validate_suggestion

FOODS = [
    {"id": 1, "name": "Oats", "meal_type": "breakfast", "price_kobo": 30000},
    {"id": 2, "name": "Egg sandwich", "meal_type": "breakfast", "price_kobo": 60000},
    {"id": 3, "name": "Beans", "meal_type": "lunch", "price_kobo": 70000},
    {"id": 4, "name": "Rice", "meal_type": "lunch", "price_kobo": 90000},
    {"id": 5, "name": "Yam", "meal_type": "dinner", "price_kobo": 65000},
    {"id": 6, "name": "Jollof", "meal_type": "dinner", "price_kobo": 95000},
]


def test_minimum_budget():
    assert minimum_budget(FOODS, 3) == 495000


def test_fallback_stays_inside_budget():
    plan = build_fallback(FOODS, 3, 650000)
    assert len(plan) == 9
    assert sum(m["price_kobo"] for m in plan) <= 650000


def test_rejects_unaffordable_budget():
    try:
        build_fallback(FOODS, 2, 100000)
        assert False, "Expected BudgetTooLow"
    except BudgetTooLow as exc:
        assert exc.minimum_kobo == 330000


def test_ai_cannot_invent_food_or_price():
    days = [{"day": 1, "breakfast": 1, "lunch": 3, "dinner": 999}]
    assert validate_suggestion(days, FOODS, 1, 200000) is None


def test_ai_plan_costed_by_backend():
    days = [{"day": 1, "breakfast": 1, "lunch": 3, "dinner": 5}]
    meals = validate_suggestion(days, FOODS, 1, 170000)
    assert sum(m["price_kobo"] for m in meals) == 165000
    assert validate_suggestion(days, FOODS, 1, 160000) is None


def test_duplicate_days_rejected():
    days = [{"day": 1, "breakfast": 1, "lunch": 3, "dinner": 5}] * 2
    assert validate_suggestion(days, FOODS, 2, 500000) is None
