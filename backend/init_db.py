"""Initialize schema and illustrative Yaba catalogue. Run: python -m backend.init_db"""
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SCHEMA = """
CREATE TABLE IF NOT EXISTS foods (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    meal_type TEXT NOT NULL CHECK (meal_type IN ('breakfast','lunch','dinner')),
    location TEXT NOT NULL,
    price_kobo INTEGER NOT NULL CHECK (price_kobo > 0),
    price_source TEXT NOT NULL DEFAULT 'illustrative_seed',
    reported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (name, location)
);
CREATE INDEX IF NOT EXISTS idx_food_location ON foods (location);

CREATE TABLE IF NOT EXISTS price_reports (
    id BIGSERIAL PRIMARY KEY,
    food_id INTEGER NOT NULL REFERENCES foods(id),
    price_kobo INTEGER NOT NULL CHECK (price_kobo > 0),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','verified','rejected')),
    reported_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS plans (
    id UUID PRIMARY KEY,
    budget_kobo INTEGER NOT NULL CHECK (budget_kobo > 0),
    duration_days INTEGER NOT NULL CHECK (duration_days BETWEEN 1 AND 7),
    location TEXT NOT NULL,
    generation_mode TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS plan_meals (
    id BIGSERIAL PRIMARY KEY,
    plan_id UUID NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    day_number INTEGER NOT NULL CHECK (day_number > 0),
    meal_type TEXT NOT NULL CHECK (meal_type IN ('breakfast','lunch','dinner')),
    food_id INTEGER NOT NULL REFERENCES foods(id),
    food_name TEXT NOT NULL,
    unit_price_kobo INTEGER NOT NULL CHECK (unit_price_kobo > 0),
    status TEXT NOT NULL DEFAULT 'planned'
        CHECK (status IN ('planned','eaten','skipped')),
    UNIQUE (plan_id, day_number, meal_type)
);
"""
# These are fictional demo prices, NOT claimed market prices. Replace after field verification.
FOODS = [
    ("Akara & pap", "Local", "breakfast", 45000),
    ("Oats & banana", "Quick", "breakfast", 50000),
    ("Bread & egg", "Local", "breakfast", 65000),
    ("Yam & egg", "Local", "breakfast", 85000),
    ("Tea & toast", "Quick", "breakfast", 55000),
    ("Beans & plantain", "Local", "lunch", 90000),
    ("Rice & stew", "Local", "lunch", 110000),
    ("Eba & egusi", "Swallow", "lunch", 140000),
    ("Jollof rice", "Local", "lunch", 120000),
    ("Noodles & egg", "Quick", "lunch", 100000),
    ("Beans porridge", "Local", "dinner", 85000),
    ("Yam porridge", "Local", "dinner", 105000),
    ("Spaghetti & sauce", "Quick", "dinner", 100000),
    ("Rice & beans", "Local", "dinner", 110000),
    ("Noodles & vegetables", "Quick", "dinner", 90000),
]


def main():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("Set DATABASE_URL in .env first (see .env.example).")
    with psycopg.connect(url) as conn:
        for statement in SCHEMA.strip().split(";"):
            if statement.strip():
                conn.execute(statement)
        for name, category, meal_type, price in FOODS:
            conn.execute(
                """INSERT INTO foods (name, category, meal_type, location, price_kobo)
                   VALUES (%s, %s, %s, 'Yaba', %s)
                   ON CONFLICT (name, location) DO NOTHING""",
                (name, category, meal_type, price),
            )
    print("HUNGR database initialized with 15 clearly labelled sample prices (Yaba).")


if __name__ == "__main__":
    main()
