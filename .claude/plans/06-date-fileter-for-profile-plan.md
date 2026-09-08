# Plan: Date Filter For Profile (Step 6)

## Context
The `/profile` page currently always shows all-time data (spec:
`.claude/specs/06-date-filter-for-profile.md`). This step adds an optional
date-range filter — `start_date`/`end_date` query params on `GET /profile`
— that narrows the transaction list, summary stats, and category breakdown
to an inclusive date range, with no new routes, tables, or dependencies.
The filter must be shareable via URL, degrade gracefully on bad input, and
match the existing form/error-message conventions already used on
login/register.

## Implementation

### 1. `database/queries.py` — add optional date-range params
Add a small private helper to avoid repeating the same WHERE-clause logic
three times:

```python
def _date_clause(start_date, end_date):
    if start_date and end_date:
        return " AND date >= ? AND date <= ?", [start_date, end_date]
    return "", []
```

Update each function's signature and query:
- `get_recent_transactions(user_id, limit=10, start_date=None, end_date=None)`
  — build `where = "WHERE user_id = ?" + clause`, `params = [user_id] + extra`,
  append `limit` last.
- `get_summary_stats(user_id, start_date=None, end_date=None)` — apply the
  same `where`/`params` to all three internal queries (`total_spent`,
  `transaction_count`, `top_category`).
- `get_category_breakdown(user_id, start_date=None, end_date=None)` — apply
  to the single grouped query. The existing rounding/remainder logic is
  untouched since it just operates on whatever rows come back.

Filter only applies when **both** dates are present (app.py guarantees
both-or-neither reach these functions).

### 2. `app.py` — `profile()` view
Add `from datetime import datetime` (or import at top with existing
imports). Inside `profile()`, after the auth check:

```python
def _valid_date(s):
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False

start_raw = request.args.get("start_date", "")
end_raw = request.args.get("end_date", "")

start_date = start_raw if _valid_date(start_raw) else None
end_date = end_raw if _valid_date(end_raw) else None

filter_error = None
if start_date and end_date and start_date > end_date:
    filter_error = "Start date is after end date — showing all-time data instead."
    start_date, end_date = None, None
```
(`YYYY-MM-DD` strings compare correctly with `>`.)

Pass `start_date=start_date, end_date=end_date` into `get_recent_transactions`,
`get_summary_stats`, `get_category_breakdown`. Pass `filter_error`,
`start_raw`, `end_raw` to `render_template` — pre-fill the form with the
raw submitted values (not the sanitized ones) so a malformed date isn't
silently erased from the input.

### 3. `templates/profile.html` — filter UI
Insert a new `.auth-card` between the Summary card and the Transaction
history card:

```html
<div class="auth-card">
    <h2 class="section-title">Filter by date</h2>
    {% if filter_error %}
    <div class="auth-error">{{ filter_error }}</div>
    {% endif %}
    <form method="GET" action="{{ url_for('profile') }}" class="filter-form">
        <div class="form-group">
            <label for="start_date">From</label>
            <input class="form-input" type="date" id="start_date" name="start_date" value="{{ start_raw }}">
        </div>
        <div class="form-group">
            <label for="end_date">To</label>
            <input class="form-input" type="date" id="end_date" name="end_date" value="{{ end_raw }}">
        </div>
        <button type="submit" class="btn-submit">Apply</button>
        <a href="{{ url_for('profile') }}" class="btn-ghost">Clear filter</a>
    </form>
</div>
```

This reuses the exact form pattern from `login.html`/`register.html`
(`.form-group`, `.form-input`, `.btn-submit`) and the existing `.auth-error`
class for the validation message.

Empty states — wrap the existing loops:
- Transaction table: `{% if transactions %}` ... existing `{% for t in
  transactions %}` ... `{% else %}<p class="empty-state">No transactions
  found for this date range.</p>{% endif %}`
- Category breakdown: same pattern with "No category data for this date
  range."

### 4. `static/css/style.css` — minimal additions
`.form-group`/`.form-input`/`.btn-submit` are full-width block elements by
default, unsuitable for an inline row, so add a small scoped layout block
using only existing CSS variables:

```css
.filter-form { display: flex; flex-wrap: wrap; align-items: flex-end; gap: 1rem; }
.filter-form .form-group { margin-bottom: 0; flex: 1 1 160px; }
.filter-form .btn-submit,
.filter-form .btn-ghost { width: auto; margin-top: 0; padding: 0.7rem 1.25rem; }

.empty-state { color: var(--ink-muted); padding: 1rem 0; font-size: 0.9rem; }
```

`.empty-state` is a neutral tone (distinct from the red `.auth-error`) for
the "no results" messages — a better semantic fit than reusing the error
banner for a non-error state, while still only using existing CSS
variables.

## Files touched
- `database/queries.py` — add `_date_clause` helper + optional params on 3 functions
- `app.py` — date parsing/validation in `profile()`, pass params through
- `templates/profile.html` — filter form, pre-filled values, empty states
- `static/css/style.css` — `.filter-form` layout + `.empty-state` class

No new files, no new routes, no database/schema changes, no new
dependencies — matches the spec exactly.

## Verification
1. Run the app (`python app.py`), log in as `demo@spendly.com` / `demo123`.
2. Visit `/profile` with no params — confirm it looks identical to current
   behavior (all 8 seed transactions, ₹346.24 total).
3. Submit a narrow date range covering only some seed expenses (e.g. the
   first few days of the current month) — confirm transaction list, total
   spent, transaction count, top category, and category breakdown all
   narrow to match, and category percentages still sum to 100%.
4. Submit a range with zero matches — confirm the empty-state messages
   appear instead of an error.
5. Submit `start_date` after `end_date` — confirm the validation message
   appears and all-time data is shown.
6. Type a malformed value directly in the URL (e.g.
   `/profile?start_date=not-a-date&end_date=2026-09-01`) — confirm it's
   treated as no filter, no crash.
7. Click "Clear filter" — confirm it returns to unfiltered `/profile`.
8. Confirm no hex colors were introduced (grep the diff for `#`).
9. After implementation, recommend running `/test-feature
   06-date-filter-for-profile` to generate and run pytest coverage via the
   existing `spendly-test-writer`/`spendly-test-runner` subagents,
   consistent with how prior steps were tested
   (`tests/test_backend_connection.py`).

## Status
Implemented and manually verified against the running dev server (see
Verification steps 1–7, all passed). Not yet committed.
