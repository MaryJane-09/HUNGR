"""Smoke checks for HUNGR's static frontend (no database required)."""
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_homepage_points_to_versioned_assets():
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert 'class="app-shell"' in html
    assert 'id="planner-form"' in html
    assert 'id="food-grid"' in html
    assert '/style.css?v=20261106-refined' in html
    assert '/app.js?v=20261106-refined' in html


def test_frontend_assets_are_served():
    stylesheet = client.get("/style.css?v=20261106-refined")
    assert stylesheet.status_code == 200
    assert "text/css" in stylesheet.headers["content-type"]
    assert ".app-shell" in stylesheet.text
    assert "--sidebar: #12182b" in stylesheet.text
    assert "--canvas: #f7f8fc" in stylesheet.text

    script = client.get("/app.js?v=20261106-refined")
    assert script.status_code == 200
    assert "javascript" in script.headers["content-type"]
    assert "updateBudgetPreview" in script.text
