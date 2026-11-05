"""HUNGR API: verified arithmetic, PostgreSQL persistence and optional AI."""
import os
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from psycopg.rows import dict_row

from backend.ai import propose_meals
from backend.planner import BudgetTooLow, build_fallback, minimum_budget, validate_suggestion

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
app = FastAPI(title="HUNGR API", version="0.1.0")


def connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(status_code=503, detail="DATABASE_URL not configured. See README.")
    return psycopg.connect(url, row_factory=dict_row, connect_timeout=5)


@app.exception_handler(psycopg.Error)
async def database_error(_request, _exc):
    return JSONResponse(status_code=503, content={"detail": "Database unavailable. Verify PostgreSQL and run the seed command."})


class CreatePlan(BaseModel):
    budget_kobo: int = Field(ge=10000, le=100000000)
    duration_days: int = Field(ge=1, le=7)
    location: str = Field(default="Yaba", min_length=1, max_length=80)
    preferences: str = Field(default="", max_length=300)


class SubmitPrice(BaseModel):
    food_id: int = Field(gt=0)
    price_kobo: int = Field(ge=10000, le=10000000)


class MealUpdate(BaseModel):
    status: str


def foods_for_location(conn, location: str):
    return conn.execute(
        """SELECT id, name, category, meal_type, location, price_kobo,
                  price_source, reported_at
           FROM foods WHERE lower(location) = lower(%s)
           ORDER BY meal_type, price_kobo, id""",
        (location.strip(),),
    ).fetchall()


def get_plan(conn, plan_id: UUID):
    plan = conn.execute("SELECT * FROM plans WHERE id = %s", (plan_id,)).fetchone()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    meals = conn.execute(
        """SELECT id, day_number, meal_type, food_id, food_name AS name,
                  unit_price_kobo AS price_kobo, status
           FROM plan_meals WHERE plan_id = %s
           ORDER BY day_number,
             CASE meal_type WHEN 'breakfast' THEN 1 WHEN 'lunch' THEN 2 ELSE 3 END""",
        (plan_id,),
    ).fetchall()
    planned = sum(m["price_kobo"] for m in meals if m["status"] != "skipped")
    spent = sum(m["price_kobo"] for m in meals if m["status"] == "eaten")
    return {
        "id": str(plan_id), "location": plan["location"],
        "duration_days": plan["duration_days"],
        "budget_kobo": plan["budget_kobo"],
        "generation_mode": plan["generation_mode"],
        "meals": meals,
        "total_planned_kobo": planned,
        "remaining_unallocated_kobo": plan["budget_kobo"] - planned,
        "spent_kobo": spent,
        "remaining_cash_kobo": plan["budget_kobo"] - spent,
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "HUNGR"}


@app.get("/api/foods")
def get_foods(location: str = Query(default="Yaba", min_length=1, max_length=80)):
    with connect() as conn:
        foods = foods_for_location(conn, location)
    return {"location": location, "foods": foods,
            "disclaimer": "Seed prices are illustrative until confirmed by local reports."}


@app.post("/api/plans", status_code=201)
async def create_plan(payload: CreatePlan):
    with connect() as conn:
        foods = foods_for_location(conn, payload.location)
        if not foods:
            raise HTTPException(404, detail="No food listings for this location yet.")
        try:
            minimum = minimum_budget(foods, payload.duration_days)
        except ValueError as exc:
            raise HTTPException(422, detail=str(exc)) from exc
        if payload.budget_kobo < minimum:
            raise HTTPException(
                422,
                detail={"code": "budget_too_low", "minimum_budget_kobo": minimum,
                        "message": "This budget cannot cover three listed meals each day."},
            )
        suggested = await propose_meals(foods, payload.duration_days,
                                       payload.budget_kobo, payload.preferences)
        meals = validate_suggestion(suggested, foods, payload.duration_days,
                                    payload.budget_kobo)
        mode = "ai" if meals is not None else "budget-safe fallback"
        if meals is None:
            try:
                meals = build_fallback(foods, payload.duration_days, payload.budget_kobo)
            except BudgetTooLow as exc:
                raise HTTPException(422, detail={"minimum_budget_kobo": exc.minimum_kobo}) from exc
        plan_id = uuid4()
        conn.execute(
            """INSERT INTO plans (id, budget_kobo, duration_days, location, generation_mode)
               VALUES (%s, %s, %s, %s, %s)""",
            (plan_id, payload.budget_kobo, payload.duration_days,
             payload.location.strip(), mode),
        )
        for meal in meals:
            conn.execute(
                """INSERT INTO plan_meals
                   (plan_id, day_number, meal_type, food_id, food_name, unit_price_kobo)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (plan_id, meal["day_number"], meal["meal_type"], meal["food_id"],
                 meal["name"], meal["price_kobo"]),
            )
        return get_plan(conn, plan_id)


@app.get("/api/plans/{plan_id}")
def read_plan(plan_id: UUID):
    with connect() as conn:
        return get_plan(conn, plan_id)


@app.patch("/api/plans/{plan_id}/meals/{meal_id}")
def update_meal(plan_id: UUID, meal_id: int, payload: MealUpdate):
    if payload.status not in {"planned", "eaten", "skipped"}:
        raise HTTPException(422, detail="Status must be planned, eaten, or skipped.")
    with connect() as conn:
        changed = conn.execute(
            """UPDATE plan_meals SET status = %s
               WHERE id = %s AND plan_id = %s RETURNING id""",
            (payload.status, meal_id, plan_id),
        ).fetchone()
        if not changed:
            raise HTTPException(404, detail="Meal not found in this plan.")
        return get_plan(conn, plan_id)


@app.post("/api/prices", status_code=201)
def submit_price(payload: SubmitPrice):
    with connect() as conn:
        food = conn.execute("SELECT id FROM foods WHERE id = %s", (payload.food_id,)).fetchone()
        if not food:
            raise HTTPException(404, detail="Food listing not found.")
        report = conn.execute(
            """INSERT INTO price_reports (food_id, price_kobo, status)
               VALUES (%s, %s, 'pending') RETURNING id, status, reported_at""",
            (payload.food_id, payload.price_kobo),
        ).fetchone()
        return {"report": report, "message": "Price report received for review; listing price unchanged."}


# Mount the frontend last so API routes take priority.
app.mount("/", StaticFiles(directory=str(ROOT / "frontend"), html=True), name="frontend")
