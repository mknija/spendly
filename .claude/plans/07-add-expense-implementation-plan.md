# Plan: Add Expense (Step 07)

## Context
Spec: `.claude/specs/07-add-expense.md`. Before this change, `/expenses/add` in `app.py` was a placeholder that returned the literal string `"Add expense — coming in Step 7"`. This step makes it a real form so a logged-in user can record a new expense, which then shows up immediately in `/profile`'s transaction history, summary stats, and category breakdown. The implementation follows the exact validation/error/redirect conventions `register()` and `login()` already use in `app.py`, and adds `insert_expense` to `database/queries.py` in the same style as its existing functions (own `get_db()` connection, commit, close before returning). No schema changes, no new dependencies, and — confirmed by reading `templates/register.html` and `static/css/style.css:340-539` directly — zero new CSS classes: `auth-section`, `auth-container`, `auth-header`, `auth-card`, `auth-error`, `form-group`, `form-input`, `btn-submit`, and `btn-ghost` all already existed and covered every element this form needed, including a plain `<select>` (styled generically via `.form-input`) and a `type="date"` input (already used unstyled in `templates/profile.html:67,71`).

Branch: `feature/add-expense`.

## Implementation

### 1. `database/queries.py` — add `insert_expense`
Appended at the end of the file, matching the existing functions' style exactly (no Flask imports, opens its own connection, closes before returning):

```python
def insert_expense(user_id, amount, category, date, description):
    """Insert a new expense row for user_id. description may be None."""
    db = get_db()
    db.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date, description),
    )
    db.commit()
    db.close()
```

### 2. `app.py` — imports
Added `CATEGORIES` to the `database.db` import and `insert_expense` to the `database.queries` import:

```python
from database.db import get_db, init_db, seed_db, CATEGORIES
from database.queries import (
    get_user_by_id,
    get_recent_transactions,
    get_summary_stats,
    get_category_breakdown,
    insert_expense,
)
```

No change to the `datetime` import — reused `datetime.today().strftime("%Y-%m-%d")` for today's date rather than adding a `date` import, keeping the diff minimal and consistent with `profile()`'s existing `_valid_date` helper style.

### 3. `app.py` — replaced the `add_expense()` placeholder
Replaced:
```python
@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"
```
with:
```python
@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]

    def _valid_date(s):
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return True
        except (ValueError, TypeError):
            return False

    if request.method == "POST":
        amount_raw = request.form.get("amount", "")
        category = request.form.get("category", "")
        date_raw = request.form.get("date", "")
        description_raw = request.form.get("description", "").strip()

        def _rerender(error):
            return render_template(
                "add_expense.html",
                error=error,
                categories=CATEGORIES,
                amount=amount_raw,
                category=category,
                date=date_raw,
                description=description_raw,
            )

        try:
            amount = float(amount_raw)
            valid_amount = amount > 0
        except (ValueError, TypeError):
            valid_amount = False

        if not valid_amount:
            return _rerender("Amount must be a number greater than 0.")

        if category not in CATEGORIES:
            return _rerender("Please select a valid category.")

        if not _valid_date(date_raw):
            return _rerender("Please enter a valid date.")

        description = description_raw if description_raw else None

        insert_expense(user_id, amount, category, date_raw, description)
        return redirect(url_for("profile"))

    today_str = datetime.today().strftime("%Y-%m-%d")
    return render_template("add_expense.html", categories=CATEGORIES, date=today_str)
```

Notes:
- `_valid_date` is a local nested helper, duplicated from `profile()`'s version rather than refactored into a shared module-level function — keeps this step's diff scoped to the files the spec lists as touched.
- `_rerender` is a small internal-only helper to avoid repeating a 6-kwarg `render_template` call three times.
- Validation order is amount → category → date (top-to-bottom form order), first failure wins — same short-circuit pattern as `register()`.
- On `GET`, `amount`/`category`/`description` are intentionally omitted from the template context; the template uses Jinja's `default('')` filter to handle their absence.

### 4. `templates/add_expense.html` — new file
```html
{% extends "base.html" %}

{% block title %}Add expense — Spendly{% endblock %}

{% block content %}

<section class="auth-section">
    <div class="auth-container">

        <div class="auth-header">
            <h1 class="auth-title">Add an expense</h1>
            <p class="auth-subtitle">Record a new transaction</p>
        </div>

        <div class="auth-card">
            {% if error %}
            <div class="auth-error">{{ error }}</div>
            {% endif %}

            <form method="POST" action="{{ url_for('add_expense') }}">
                <div class="form-group">
                    <label for="amount">Amount</label>
                    <input type="number" id="amount" name="amount"
                           class="form-input" step="0.01" min="0.01"
                           placeholder="0.00" value="{{ amount|default('') }}"
                           required autofocus>
                </div>
                <div class="form-group">
                    <label for="category">Category</label>
                    <select id="category" name="category" class="form-input" required>
                        {% for c in categories %}
                        <option value="{{ c }}" {% if category == c %}selected{% endif %}>{{ c }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="form-group">
                    <label for="date">Date</label>
                    <input type="date" id="date" name="date"
                           class="form-input" value="{{ date|default('') }}" required>
                </div>
                <div class="form-group">
                    <label for="description">Description (optional)</label>
                    <input type="text" id="description" name="description"
                           class="form-input" placeholder="e.g. Groceries"
                           value="{{ description|default('') }}">
                </div>
                <button type="submit" class="btn-submit">Add expense</button>
            </form>
            <a href="{{ url_for('profile') }}" class="btn-ghost">Cancel</a>
        </div>

    </div>
</section>

{% endblock %}
```
`.btn-submit` is `width: 100%` (style.css:520-521), so the `Cancel` link stacks below it naturally with no extra markup or CSS needed.

### 5. `templates/profile.html` — added the "Add expense" link
Inside the Summary `auth-card`, immediately after the closing `</div>` of `.hero-v2-stats`:

```html
<div class="auth-card">
    <h2 class="section-title">Summary</h2>
    <div class="hero-v2-stats">
        ... (unchanged) ...
    </div>
    <a href="{{ url_for('add_expense') }}" class="btn-ghost">Add expense</a>
</div>
```

## Files touched
- `app.py` — imported `CATEGORIES` + `insert_expense`; replaced `add_expense()` placeholder with full `GET`/`POST` implementation
- `database/queries.py` — added `insert_expense(user_id, amount, category, date, description)`
- `templates/profile.html` — added "Add expense" link in the Summary card
- `templates/add_expense.html` — **new file**

No changes to `database/db.py`, `static/css/style.css`, `templates/base.html`, or any other route.

## Verification (already performed)
1. Ran the app (`python app.py`) — booted and seeded the demo user (`demo@spendly.com` / `demo123`).
2. Logged out, `GET /expenses/add` — confirmed `302` redirect to `/login`.
3. Logged in, `GET /expenses/add` — form rendered with `date` pre-filled to today, category `<select>` populated with all 7 `CATEGORIES`, no error banner.
4. Submitted a valid expense (`12.50`, `Food`, today's date, `Coffee`) — confirmed `302` redirect to `/profile`, new row at top of Transaction history, and `Total spent`/`Transaction count`/`Top category`/category breakdown (still summing to 100%) all updated.
5. Submitted with amount `""`, `abc`, `0` — each re-rendered the form with `"Amount must be a number greater than 0."`, no row inserted.
6. Submitted with an invalid category (`Nope`) — `"Please select a valid category."`, no insert.
7. Submitted with a malformed date (`not-a-date`) — `"Please enter a valid date."`, no insert.
8. Submitted with description blank — succeeded, Transaction history showed `—` for that row.
9. Confirmed the "Add expense" link on `/profile` (`href="/expenses/add"`) and no new hardcoded hex colors were introduced (all reused existing CSS classes).

Verification was performed via `curl` against the running dev server (no browser automation tool was available in-session), covering every item in the Definition of Done except manual click-through of the "Cancel" link, which is a plain `<a href>` and needs no further verification.

## Outstanding
- Run `/test-feature 07-add-expense` to generate and run pytest coverage via the `spendly-test-writer`/`spendly-test-runner` subagents, following the existing convention in `tests/test_backend_connection.py` and `tests/test_06-date-filter-for-profile.py`.
- Optional: manual visual/browser check of the form layout (Cancel link stacking, select dropdown appearance) since only `curl`-level verification was performed this session.

## Status
Implemented and functionally verified. Not yet committed. Tests not yet written.
