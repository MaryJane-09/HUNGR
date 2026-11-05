"""Price-grounded HUNGR meal planning. All prices are authoritative server-side."""
from collections import defaultdict

MEAL_TYPES = ("breakfast", "lunch", "dinner")


class BudgetTooLow(ValueError):
    def __init__(self, minimum_kobo: int):
        self.minimum_kobo = minimum_kobo
        super().__init__("Budget cannot cover three listed meals per day")


def _catalogue(foods):
    by_slot = defaultdict(list)
    for food in foods:
        if food["price_kobo"] > 0 and food["meal_type"] in MEAL_TYPES:
            by_slot[food["meal_type"]].append(food)
    for slot in MEAL_TYPES:
        by_slot[slot].sort(key=lambda f: (f["price_kobo"], f["id"]))
        if not by_slot[slot]:
            raise ValueError(f"No foods listed for {slot}")
    return by_slot


def minimum_budget(foods, days: int) -> int:
    by_slot = _catalogue(foods)
    return days * sum(by_slot[slot][0]["price_kobo"] for slot in MEAL_TYPES)


def validate_suggestion(suggestion, foods, days: int, budget_kobo: int):
    """Accept only exact food IDs and all 3 slots/day; never trust AI-provided prices."""
    if not isinstance(suggestion, list) or len(suggestion) != days:
        return None
    by_id = {food["id"]: food for food in foods}
    meals, seen = [], set()
    for item in suggestion:
        if not isinstance(item, dict) or type(item.get("day")) is not int:
            return None
        day = item["day"]
        if day < 1 or day > days or day in seen:
            return None
        seen.add(day)
        for slot in MEAL_TYPES:
            food_id = item.get(slot)
            if type(food_id) is not int:
                return None
            food = by_id.get(food_id)
            if not food or food["meal_type"] != slot:
                return None
            meals.append({
                "day_number": day, "meal_type": slot, "food_id": food_id,
                "name": food["name"], "price_kobo": food["price_kobo"],
            })
    meals.sort(key=lambda m: (m["day_number"], MEAL_TYPES.index(m["meal_type"])))
    if sum(meal["price_kobo"] for meal in meals) > budget_kobo:
        return None
    return meals


def build_fallback(foods, days: int, budget_kobo: int):
    """Start with the least-cost 3-meal plan, then add affordable variety."""
    by_slot = _catalogue(foods)
    min_cost = minimum_budget(foods, days)
    if budget_kobo < min_cost:
        raise BudgetTooLow(min_cost)
    meals = []
    for day in range(1, days + 1):
        for slot in MEAL_TYPES:
            food = by_slot[slot][0]
            meals.append({
                "day_number": day, "meal_type": slot, "food_id": food["id"],
                "name": food["name"], "price_kobo": food["price_kobo"],
            })
    remaining = budget_kobo - min_cost
    # Upgrades only use money remaining AFTER every baseline meal is covered.
    for idx, meal in enumerate(meals):
        options = by_slot[meal["meal_type"]]
        rotation = ((idx // 3) + (MEAL_TYPES.index(meal["meal_type"]))) % len(options)
        candidate = options[rotation]
        extra = candidate["price_kobo"] - meal["price_kobo"]
        if 0 <= extra <= remaining:
            meal.update(food_id=candidate["id"], name=candidate["name"],
                        price_kobo=candidate["price_kobo"])
            remaining -= extra
    return meals
