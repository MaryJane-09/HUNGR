"""Integration tests require a seeded PostgreSQL database (CI provides one)."""
import os

import pytest
from fastapi.testclient import TestClient

from backend.main import app

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="Set DATABASE_URL to run database integration tests"
)
client = TestClient(app)


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


def test_food_board_and_price_report():
    foods = client.get("/api/foods?location=Yaba")
    assert foods.status_code == 200
    data = foods.json()["foods"]
    assert len(data) >= 15
    initial_price = data[0]["price_kobo"]
    response = client.post("/api/prices", json={
        "food_id": data[0]["id"], "price_kobo": 123400
    })
    assert response.status_code == 201
    assert response.json()["report"]["status"] == "pending"
    updated_food = client.get("/api/foods?location=Yaba").json()["foods"][0]
    assert updated_food["price_kobo"] == initial_price


def test_plan_and_tracking():
    response = client.post("/api/plans", json={
        "budget_kobo": 1500000, "duration_days": 5, "location": "Yaba"
    })
    assert response.status_code == 201, response.text
    plan = response.json()
    assert len(plan["meals"]) == 15
    assert plan["total_planned_kobo"] <= 1500000
    plan_id = plan["id"]
    assert client.get(f"/api/plans/{plan_id}").status_code == 200
    meal = plan["meals"][0]
    updated = client.patch(f"/api/plans/{plan_id}/meals/{meal['id']}",
                           json={"status": "eaten"})
    assert updated.status_code == 200
    assert updated.json()["spent_kobo"] == meal["price_kobo"]


def test_budget_shortfall_is_explicit():
    response = client.post("/api/plans", json={
        "budget_kobo": 10000, "duration_days": 7, "location": "Yaba"
    })
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "budget_too_low"
