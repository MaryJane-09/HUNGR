# HUNGR 🍲

**Eat smart. Stay ready.** HUNGR is a student food-budget planner that turns a budget and number of days into a practical meal schedule using a local food catalogue. An optional AI service proposes meals, but **the backend always checks food IDs, meal types, and costs** before saving a plan.

> **Competition MVP / prototype.** All 15 starting prices for Yaba are illustrative examples, **not confirmed vendor quotes**. Replace or verify them with up-to-date field research before using the app for real spending decisions. HUNGR does not assess nutritional adequacy.

## Stack

- **Frontend:** HTML, CSS, vanilla JavaScript (served by FastAPI)
- **Backend:** Python 3.11+ and FastAPI
- **Database:** PostgreSQL
- **AI:** optional OpenAI-compatible chat completions API
- **Tests:** pytest, including PostgreSQL integration checks in GitHub Actions

## Run locally on Linux

In a terminal at the **repository root**:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
```

Create a PostgreSQL user and database if they don't exist yet:

```bash
sudo -u postgres psql -c "CREATE USER hungr WITH PASSWORD 'change-me';"
sudo -u postgres psql -c "CREATE DATABASE hungr OWNER hungr;"
```

Replace `change-me` with a password you choose, and match it in the `DATABASE_URL` inside `.env`. (If the user/database already exist, configure your existing credentials instead.) Avoid special URL characters in passwords unless URL-encoded.

```bash
python -m backend.init_db
uvicorn backend.main:app --reload
```

Visit **http://127.0.0.1:8000** for the app or **http://127.0.0.1:8000/docs** for API docs. To run tests:

```bash
pytest -q
```

The database-backed tests run when `DATABASE_URL` is set. They are also run automatically in the GitHub Actions workflow with a temporary PostgreSQL service.

### AI API (optional)

Set `OPENAI_API_KEY` and `OPENAI_MODEL` in your local `.env`. If using another OpenAI-compatible provider, also set `OPENAI_BASE_URL`. Keep secrets on the server; **never commit your `.env`**. If AI is missing, fails, or suggests invalid/unaffordable meals, HUNGR uses the labelled budget-safe fallback rather than inventing prices. Avoid sending personal or sensitive information through the optional preferences field.

## MVP user journey

1. Enter food budget in **naira**, duration (1–7 days), and location (Yaba demo).
2. Backend reads food listings from PostgreSQL (prices stored as **integer kobo**).
3. AI optionally suggests food IDs for breakfast, lunch, and dinner; backend rejects any invented ID, mismatched meal type, or plan over budget.
4. If needed, deterministic fallback builds three listed meals per day, then tries to add variety without exceeding budget. If even the least-cost plan is over budget, HUNGR reports the shortfall and does **not** suggest skipping meals as the solution.
5. Saved plans preserve the listed price at creation time. Mark a meal **eaten**, **skipped**, or **planned** to track actual vs planned spending.
6. Submit new price sightings. Reports are stored as **pending**; they do not silently overwrite the displayed catalogue.

## Main API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Service health |
| GET | `/api/foods?location=Yaba` | Browse catalogue |
| POST | `/api/plans` | Build and save a price-checked plan |
| GET | `/api/plans/{id}` | Retrieve a plan |
| PATCH | `/api/plans/{id}/meals/{meal_id}` | Update meal tracking |
| POST | `/api/prices` | Submit an unverified price report |

## Project layout

```text
backend/
  ai.py          # Optional API integration
  init_db.py     # PostgreSQL schema + labelled example data
  main.py        # API, database calls, meal tracking
  planner.py     # Pure budget and AI validation logic
  requirements.txt
frontend/
  index.html
  style.css
  app.js
tests/
  test_planner.py
  test_api.py
.github/workflows/tests.yml
.env.example
```

## Next steps for competition polish

- Collect and label real local vendor prices, with timestamps and verification.
- Build a trusted review process for submitted price reports and add vendor attribution.
- Add plan recalculation/recovery when a food price changes or a student logs a different purchase.
- Improve the AI's preference matching, accessibility testing, and deployment.

**Important limitations:** No logins, payments, delivery, moderation panel, or nutrition analysis yet. Plan links are random IDs stored locally in the browser; do not treat them as secure private accounts. Demo food listings and community submissions should not be represented as verified prices.
