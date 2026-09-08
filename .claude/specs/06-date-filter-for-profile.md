# Spec: Date Filter For Profile

## Overview
Step 6 adds a date-range filter to the `/profile` page. Today the page always
shows all-time data — every transaction, the all-time summary stats, and the
all-time category breakdown. This step lets a logged-in user narrow all three
of those sections to a specific date range (e.g. "this month", a custom
range) via a simple form, without introducing any new tables or routes. The
filter is read from the query string so the resulting URL is shareable and
bookmarkable.

## Depends on
- Step 1: Database setup (`expenses` table with a `date` column)
- Step 3: Login / Logout (`session["user_id"]` is set on login)
- Step 5: Backend routes for profile page (`database/queries.py` helpers and
  the live `/profile` route already exist)

## Routes
- `GET /profile` — modified (not new). Now also accepts optional query
  string parameters `start_date` and `end_date` (format `YYYY-MM-DD`) and
  filters transactions, summary stats, and category breakdown to that
  inclusive range. Access level: logged-in only (unchanged).

## Database changes
No database changes. The existing `expenses.date` column (stored as
`YYYY-MM-DD` text) is sufficient for range filtering with plain string
comparison.

## Templates
- **Modify:** `templates/profile.html`
  - Add a date-range filter form above the transaction history section:
    two `<input type="date">` fields (`start_date`, `end_date`) and a
    submit button, using `method="GET"` action `/profile` so the filter is
    expressed entirely in the URL.
  - Pre-fill both inputs with the currently applied filter values (if any)
    so the form reflects what's being shown.
  - Add a "Clear filter" link that points to `/profile` with no query
    string.
  - Add an empty-state message inside the transaction table (and category
    breakdown section) for when the selected range has zero matching
    transactions, e.g. "No transactions found for this date range."
  - Add a validation message shown when `start_date` is after `end_date`,
    explaining that the filter was ignored and all-time data is shown
    instead.

## Files to change
- `app.py` — `profile()` view reads `start_date`/`end_date` from
  `request.args`, validates them, and passes them through to the three
  query helpers and back to the template (so the form can be pre-filled).
- `database/queries.py` — `get_recent_transactions`, `get_summary_stats`,
  and `get_category_breakdown` each gain optional `start_date=None,
  end_date=None` parameters that add a parameterised `date >= ? AND date
  <= ?` condition to their existing `WHERE user_id = ?` clause when
  provided.
- `templates/profile.html` — add the filter form, pre-filled values, clear
  link, and empty/validation states described above.

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format dates into SQL
- Passwords hashed with werkzeug (unchanged in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- `start_date`/`end_date` must be validated as well-formed `YYYY-MM-DD`
  strings before being used in a query; malformed values are ignored
  (treated as if no filter was supplied) rather than raising an error
- When `start_date` is after `end_date`, ignore both and fall back to
  all-time data, and surface a validation message on the page
- When no filter params are present, behavior must be identical to the
  current unfiltered `/profile` page
- Query helpers must remain pure (no Flask imports) and continue to call
  `get_db()` internally and close the connection before returning
- Category breakdown percentages must still sum to 100 for the filtered
  set, using the same largest-category-absorbs-remainder rounding rule
  already implemented

## Definition of done
- [ ] Visiting `/profile` with no query params shows all-time data exactly
      as before this change
- [ ] Submitting the filter form with a valid `start_date` and `end_date`
      updates the URL and shows only transactions within that inclusive
      range
- [ ] Summary stats (total spent, transaction count, top category) reflect
      only the filtered date range
- [ ] Category breakdown reflects only the filtered date range, with
      percentages still summing to 100%
- [ ] A date range with zero matching transactions shows an empty-state
      message instead of an error or a blank table
- [ ] Submitting `start_date` after `end_date` shows a validation message
      and falls back to displaying all-time data
- [ ] The "Clear filter" link returns to `/profile` with no query string
      and restores all-time data
- [ ] After submitting a filter, the date inputs still show the submitted
      values (the form reflects the current filter state)
- [ ] No hex colour values appear in the new markup — only CSS variables
