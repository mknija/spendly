# Plan: Edit Expense (Step 08)

## Context
`/expenses/<int:id>/edit` in `app.py` was a placeholder that returned the literal string `"Edit expense — coming in Step 8"`. Per `.claude/specs/08-edit-expense.md`, this step makes it a real form so a logged-in user can edit one of their own existing expenses, then redirects back to `/profile` where the change is immediately visible in the transaction history, summary stats, and category breakdown.

This closely mirrors Step 7 (Add Expense, `.claude/plans/07-add-expense-implementation-plan.md`) — same `auth-*`/`form-*`/`btn-*` CSS classes, same validation order/messages, same `_rerender(error)` closure pattern. Two things differ from Step 7:
1. **Ownership scoping** — every lookup/update is `WHERE id = ? AND user_id = ?`. A nonexistent id and an id owned by another user both redirect to `/profile` (not 404, not leaking whether the id exists).
2. **Pre-filled forms** — unlike `add_expense.html` (which defaults `amount`/`category`/`description` to blank via Jinja `|default('')`), every render path of `edit_expense()` supplies real values (either the expense's current DB values, or the just-submitted-but-invalid values) — never blank.

Branch: `feature/edit-expense`.

## Implementation

### 1. `database/queries.py` — extend `get_recent_transactions`, add `get_expense_by_id` and `update_expense`

**Extended `get_recent_transactions`** to also select/return `id` (needed so `profile.html` can build a per-row edit link):
```python
def get_recent_transactions(user_id, limit=10, start_date=None, end_date=None):
    """Return list of dicts {id, date, description, category, amount}, newest
    first, date formatted "%b %d, %Y", description "—" if NULL.
    Empty list if no expenses.
    """
    db = get_db()
    clause, extra_params = _date_clause(start_date, end_date)
    rows = db.execute(
        "SELECT id, date, description, category, amount FROM expenses "
        f"WHERE user_id = ?{clause} ORDER BY date DESC, created_at DESC LIMIT ?",
        [user_id] + extra_params + [limit],
    ).fetchall()
    db.close()

    transactions = []
    for row in rows:
        display_date = datetime.strptime(row["date"], "%Y-%m-%d").strftime("%b %d, %Y")
        transactions.append(
            {
                "id": row["id"],
                "date": display_date,
                "description": row["description"] or "—",
                "category": row["category"],
                "amount": row["amount"],
            }
        )
    return transactions
```

**Appended two new functions** after `insert_expense`, following its exact style (no Flask imports, own `get_db()` connection, close before returning, commit for writes):
```python
def get_expense_by_id(user_id, expense_id):
    """Return the expense row (id, amount, category, date, description) for
    user_id, or None if it doesn't exist / isn't owned by user_id."""
    db = get_db()
    row = db.execute(
        "SELECT id, amount, category, date, description FROM expenses "
        "WHERE id = ? AND user_id = ?",
        (expense_id, user_id),
    ).fetchone()
    db.close()
    return row


def update_expense(user_id, expense_id, amount, category, date, description):
    """Update an existing expense row owned by user_id. description may be None."""
    db = get_db()
    db.execute(
        "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? "
        "WHERE id = ? AND user_id = ?",
        (amount, category, date, description, expense_id, user_id),
    )
    db.commit()
    db.close()
```
`get_expense_by_id` returning `None` for both "doesn't exist" and "not owned" gives the route its no-leak behavior for free — a wrong-owner row and a nonexistent row are indistinguishable to the caller.

### 2. `app.py` — imports
Added `get_expense_by_id, update_expense` to the existing `database.queries` import block (`database.db` import already had `CATEGORIES` since Step 7):
```python
from database.queries import (
    get_user_by_id,
    get_recent_transactions,
    get_summary_stats,
    get_category_breakdown,
    insert_expense,
    get_expense_by_id,
    update_expense,
)
```

### 3. `app.py` — replaced the `edit_expense()` placeholder
Replaced:
```python
@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"
```
with:
```python
@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    expense = get_expense_by_id(user_id, id)
    if expense is None:
        return redirect(url_for("profile"))

    if request.method == "POST":
        amount_raw = request.form.get("amount", "")
        category = request.form.get("category", "")
        date_raw = request.form.get("date", "")
        description_raw = request.form.get("description", "").strip()

        def _rerender(error):
            return render_template(
                "edit_expense.html",
                error=error,
                categories=CATEGORIES,
                expense_id=id,
                amount=amount_raw,
                category=category,
                date=date_raw,
                description=description_raw,
            )

        try:
            amount = float(amount_raw)
            valid_amount = math.isfinite(amount) and amount > 0
        except (ValueError, TypeError):
            valid_amount = False

        if not valid_amount:
            return _rerender("Amount must be a number greater than 0.")

        if category not in CATEGORIES:
            return _rerender("Please select a valid category.")

        if not _valid_date(date_raw):
            return _rerender("Please enter a valid date.")

        description = description_raw if description_raw else None

        update_expense(user_id, id, amount, category, date_raw, description)
        return redirect(url_for("profile"))

    return render_template(
        "edit_expense.html",
        categories=CATEGORIES,
        expense_id=id,
        amount=expense["amount"],
        category=expense["category"],
        date=expense["date"],
        description=expense["description"] or "",
    )
```

Notes:
- The ownership guard runs once, before branching on `request.method`, so it protects GET and POST identically and doubles as the GET pre-fill data source.
- Validation order/messages/short-circuit (`amount` → `category` → `date`, with the `math.isfinite` guard) is copied verbatim from `add_expense()`.
- Uses the existing module-level `_valid_date` helper (`app.py:29-34`) directly — no nested duplicate needed.
- Both `_rerender` and the GET `render_template` pass identical keys (`categories`, `expense_id`, `amount`, `category`, `date`, `description`) with real values on every path — the template never needs `|default(...)`.
- `expense["date"]` is already `YYYY-MM-DD`, so it goes straight into the date input's `value`.

### 4. `templates/edit_expense.html` — new file
`add_expense.html` with four changes: title/heading copy, form `action` parameterized by `expense_id`, submit label "Save changes", and values rendered directly (no `|default('')`, since the view always supplies them):
```html
{% extends "base.html" %}

{% block title %}Edit expense — Spendly{% endblock %}

{% block content %}

<section class="auth-section">
    <div class="auth-container">

        <div class="auth-header">
            <h1 class="auth-title">Edit expense</h1>
            <p class="auth-subtitle">Update this transaction</p>
        </div>

        <div class="auth-card">
            {% if error %}
            <div class="auth-error">{{ error }}</div>
            {% endif %}

            <form method="POST" action="{{ url_for('edit_expense', id=expense_id) }}">
                <div class="form-group">
                    <label for="amount">Amount</label>
                    <input type="number" id="amount" name="amount"
                           class="form-input" step="0.01" min="0.01"
                           placeholder="0.00" value="{{ amount }}"
                           required autofocus>
                </div>
                <div class="form-group">
                    <label for="category">Category</label>
                    <select id="category" name="category" class="form-input" required>
                        {% for category_option in categories %}
                        <option value="{{ category_option }}"
                                {% if category == category_option %}selected{% endif %}>
                            {{ category_option }}
                        </option>
                        {% endfor %}
                    </select>
                </div>
                <div class="form-group">
                    <label for="date">Date</label>
                    <input type="date" id="date" name="date"
                           class="form-input" value="{{ date }}" required>
                </div>
                <div class="form-group">
                    <label for="description">Description (optional)</label>
                    <input type="text" id="description" name="description"
                           class="form-input" placeholder="e.g. Groceries"
                           value="{{ description }}">
                </div>
                <button type="submit" class="btn-submit">Save changes</button>
            </form>
            <a href="{{ url_for('profile') }}" class="btn-ghost">Cancel</a>
        </div>

    </div>
</section>

{% endblock %}
```

### 5. `templates/profile.html` — added an "Edit" column to the transaction history table
Added a header and per-row link, reusing `.btn-ghost` (the only existing link-styling class — no new CSS):
```html
<thead>
    <tr>
        <th>Date</th>
        <th>Description</th>
        <th>Category</th>
        <th>Amount</th>
        <th>Edit</th>
    </tr>
</thead>
<tbody>
    {% for t in transactions %}
    <tr>
        <td>{{ t.date }}</td>
        <td>{{ t.description }}</td>
        <td><span class="badge {{ badge_class[t.category] }}">{{ t.category }}</span></td>
        <td class="txn-amount">₹{{ "%.2f"|format(t.amount) }}</td>
        <td><a href="{{ url_for('edit_expense', id=t.id) }}" class="btn-ghost">Edit</a></td>
    </tr>
    {% endfor %}
</tbody>
```
Relies on `get_recent_transactions` now returning `id` (item 1) — no other change to `profile()` in `app.py`.

## Files touched
- `app.py` — imported `get_expense_by_id, update_expense`; replaced `edit_expense()` placeholder with full `GET`/`POST` implementation
- `database/queries.py` — extended `get_recent_transactions` to select/return `id`; added `get_expense_by_id(user_id, expense_id)` and `update_expense(user_id, expense_id, amount, category, date, description)`
- `templates/profile.html` — added an "Edit" column to the transaction history table
- `templates/edit_expense.html` — **new file**

No changes to `database/db.py` (no schema change needed), `static/css/style.css`, `templates/base.html`, `add_expense()`, or `delete_expense()` (still Step 9's placeholder).

## Verification (already performed)
Verified via `curl` against the running dev server (`python app.py`), with a fresh seeded DB:
1. Logged out, `GET /expenses/1/edit` and `GET /expenses/999999/edit` — both `302` to `/login`.
2. Logged in as the seeded demo user, `GET /expenses/3/edit` — form pre-filled correctly (`89.99`, `Bills` selected, `2026-09-05`, `Electricity bill`).
3. Logged in, `GET /expenses/999999/edit` (nonexistent id) — `302` to `/profile`.
4. Registered a second user, `GET /expenses/3/edit` (owned by the demo user) — `302` to `/profile`, no data leak.
5. Submitted a valid edit (amount `150.00`, category `Shopping`, date `2026-09-06`, description `Updated bill`) — `302` to `/profile`; the row reflected the new values immediately; Total spent updated to `₹340.75`, category breakdown percentages still summed to 100.
6. Submitted invalid amount (`abc`, `0`) — both re-rendered with `"Amount must be a number greater than 0."`, DB row unchanged.
7. Submitted invalid category (`Nope`) — `"Please select a valid category."`, no DB change.
8. Submitted malformed date (`not-a-date`) — `"Please enter a valid date."`, no DB change.
9. Submitted with description cleared to blank — succeeded (`302`), Transaction history showed `—` for that row.
10. On `/profile`, confirmed every transaction row (ids 1–8) had a distinct, correctly-targeted "Edit" link.
11. Confirmed no hex color values were introduced in `edit_expense.html` or the `profile.html` diff — only existing CSS classes reused.
12. Checked the dev server log for tracebacks during the full test run — none found.

Test artifacts (`spendly.db`, cookie jars, server log) were cleaned up after verification; `spendly.db` is not git-tracked so no repo state was affected.

## Outstanding
- Run `/test-feature 08-edit-expense` to generate and run pytest coverage via the `spendly-test-writer`/`spendly-test-runner` subagents, following the existing convention in `tests/test_07-add-expense.py` (`_register_and_login`/`logged_in_client` fixture, `_user_id()`/`_expense_count()`/`_fetch_expenses()` DB helpers).
- No "second user" fixture exists in `tests/conftest.py` (it only defines `app`; `client` comes from `pytest-flask`) — the ownership test will need an inline second registration in whichever test file covers Step 8.
- Optional: manual/browser check of the new Edit link placement and column alignment in `.txn-table`, since this session's verification was `curl`/route-level, not visual.

## Status
Implemented and functionally verified. Not yet committed. Tests not yet written.
