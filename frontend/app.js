const foodGrid = document.querySelector("#food-grid");
const foodsStatus = document.querySelector("#foods-status");
const planMessage = document.querySelector("#plan-message");
const reportMessage = document.querySelector("#report-message");
const mealDays = document.querySelector("#meal-days");
const planPanel = document.querySelector("#plan-panel");
let foods = [];

const money = kobo => new Intl.NumberFormat("en-NG", {
  style: "currency", currency: "NGN", maximumFractionDigits: 0
}).format(kobo / 100);

function el(tag, className, value) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value !== undefined) node.textContent = value;
  return node;
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options, headers: {"Content-Type": "application/json", ...options.headers}
  });
  const data = await response.json();
  if (!response.ok) {
    if (data.detail?.code === "budget_too_low") {
      throw new Error(`This budget cannot cover three listed meals a day. The lowest listed total is ${money(data.detail.minimum_budget_kobo)}. Try adjusting the budget or number of days.`);
    }
    throw new Error(typeof data.detail === "string" ? data.detail : "Something went wrong. Try again.");
  }
  return data;
}

const icons = {breakfast: "☀️", lunch: "🍚", dinner: "🌙"};

function renderFoods(list) {
  foodGrid.replaceChildren();
  const selector = document.querySelector("#report-food");
  selector.replaceChildren(el("option", "", "Select from the food board"));
  selector.firstChild.value = "";
  for (const food of list) {
    const card = el("article", "food-card");
    const art = el("div", "food-symbol", icons[food.meal_type] || "🍽️");
    const meta = el("div", "food-meta", food.meal_type.toUpperCase());
    const name = el("h3", "", food.name);
    const detail = el("p", "", `${food.category} · ${food.location}`);
    const bottom = el("div", "food-bottom");
    bottom.append(el("strong", "", money(food.price_kobo)), el("span", "", "DEMO PRICE"));
    card.append(art, meta, name, detail, bottom);
    foodGrid.append(card);
    const opt = el("option", "", food.name);
    opt.value = String(food.id);
    selector.append(opt);
  }
  foodsStatus.textContent = list.length ? "" : "No foods have been added to this location.";
}

async function loadFoods() {
  try {
    const data = await request("/api/foods?location=Yaba");
    foods = data.foods;
    renderFoods(foods);
  } catch (error) {
    foodsStatus.textContent = `Could not load food board: ${error.message}`;
  }
}

function renderPlan(plan) {
  document.querySelector("#stat-budget").textContent = money(plan.budget_kobo);
  document.querySelector("#stat-cost").textContent = money(plan.total_planned_kobo);
  document.querySelector("#stat-spent").textContent = money(plan.spent_kobo);
  document.querySelector("#stat-left").textContent = money(plan.remaining_cash_kobo);
  document.querySelector("#plan-mode").textContent =
    plan.generation_mode === "ai" ? "AI-suggested and checked against our food-price data." :
    "Budget-safe plan built from our food-price data. AI suggestions were unavailable or did not pass validation.";
  document.querySelector("#plan-summary").textContent =
    `${money(plan.remaining_unallocated_kobo)} not allocated to active meals. Mark meals eaten to track actual spending; skipped meals are removed from planned costs.`;
  mealDays.replaceChildren();
  for (let day = 1; day <= plan.duration_days; day++) {
    const card = el("article", "day-card");
    const top = el("div", "day-top");
    top.append(el("span", "", `DAY ${String(day).padStart(2, "0")}`),
               el("strong", "", money(plan.meals.filter(m => m.day_number === day && m.status !== "skipped").reduce((total, m) => total + m.price_kobo, 0))));
    card.append(top);
    for (const meal of plan.meals.filter(m => m.day_number === day)) {
      const row = el("div", `meal-row ${meal.status}`);
      const copy = el("div", "meal-copy");
      copy.append(el("small", "", `${icons[meal.meal_type] || "🍽️"} ${meal.meal_type.toUpperCase()}`),
                  el("strong", "", meal.name),
                  el("span", "", money(meal.price_kobo)));
      const actions = el("div", "meal-actions");
      const eaten = el("button", "meal-toggle", meal.status === "eaten" ? "✓ Eaten" : "Mark eaten");
      eaten.type = "button";
      eaten.setAttribute("aria-label", `${meal.status === "eaten" ? "Undo eaten" : "Mark eaten"}: ${meal.name}, day ${day}`);
      eaten.addEventListener("click", () => changeMeal(plan.id, meal.id, meal.status === "eaten" ? "planned" : "eaten", eaten));
      const skipped = el("button", "meal-skip", meal.status === "skipped" ? "Undo skip" : "Skip");
      skipped.type = "button";
      skipped.addEventListener("click", () => changeMeal(plan.id, meal.id, meal.status === "skipped" ? "planned" : "skipped", skipped));
      actions.append(eaten, skipped);
      row.append(copy, actions);
      card.append(row);
    }
    mealDays.append(card);
  }
  planPanel.hidden = false;
}

async function changeMeal(planId, mealId, status, button) {
  button.disabled = true;
  try {
    const plan = await request(`/api/plans/${planId}/meals/${mealId}`, {
      method: "PATCH", body: JSON.stringify({status})
    });
    renderPlan(plan);
    planMessage.textContent = "";
  } catch (error) {
    planMessage.textContent = error.message;
    button.disabled = false;
  }
}

document.querySelector("#planner-form").addEventListener("submit", async event => {
  event.preventDefault();
  const button = document.querySelector("#plan-submit");
  planMessage.textContent = "Finding affordable combinations…";
  button.disabled = true;
  try {
    const budget = Number(document.querySelector("#budget").value);
    if (!Number.isSafeInteger(budget) || budget < 100 || budget > 1000000) {
      throw new Error("Please enter a whole-naira amount between ₦100 and ₦1,000,000.");
    }
    const plan = await request("/api/plans", {
      method: "POST", body: JSON.stringify({
        budget_kobo: budget * 100,
        duration_days: Number(document.querySelector("#days").value),
        location: document.querySelector("#location").value,
        preferences: document.querySelector("#preferences").value
      })
    });
    localStorage.setItem("hungr-plan-id", plan.id);
    renderPlan(plan);
    planMessage.textContent = "Your plan is ready below.";
    planPanel.scrollIntoView({behavior: "smooth", block: "start"});
  } catch (error) {
    planMessage.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

document.querySelector("#report-form").addEventListener("submit", async event => {
  event.preventDefault();
  const button = document.querySelector("#report-submit");
  button.disabled = true;
  reportMessage.textContent = "Sending your report…";
  try {
    const price = Number(document.querySelector("#report-price").value);
    if (!Number.isSafeInteger(price) || price < 100 || price > 100000) {
      throw new Error("Enter a valid whole-naira food price.");
    }
    const data = await request("/api/prices", {
      method: "POST", body: JSON.stringify({
        food_id: Number(document.querySelector("#report-food").value),
        price_kobo: price * 100
      })
    });
    reportMessage.textContent = data.message;
    document.querySelector("#report-price").value = "";
  } catch (error) {
    reportMessage.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

async function restorePlan() {
  const id = localStorage.getItem("hungr-plan-id");
  if (!id) return;
  try {
    renderPlan(await request(`/api/plans/${encodeURIComponent(id)}`));
  } catch (_error) {
    localStorage.removeItem("hungr-plan-id");
  }
}
loadFoods();
restorePlan();
