# Spec: Edit Expense

## Overview
Step 8 replaces the placeholder `/expenses/<int:id>/edit` route with a real
form that lets a logged-in user update one of their own existing expenses.
Today the route just returns the string "Edit expense — coming in Step 8".
This step adds a GET form (pre-filled with the existing amount, category,
date, and description), a POST handler that validates the input and updates
the matching row in the `expenses` table, and a way to reach the form from
the transaction history on `/profile`. On success the user is redirected
back to `/profile` so the updated values are immediately visible.

## Depends on
- Step 1: Database setup (`expenses` table exists)
- Step 3: Login / Logout (`session["user_id"]` is set on login)
- Step 5: Backend routes for profile page (`database/queries.py` pattern,
  live `/profile` route to redirect back to)
- Step 7: Add expense (`add_expense.html` form layout and validation rules
  this step reuses; `CATEGORIES` import pattern in `app.py`)

## Routes
- `GET /expenses/<int:id>/edit` — renders the edit-expense form pre-filled
  with the expense's current amount, category, date, and description —
  access level: logged-in only (redirect to `/login` if not authenticated);
  redirect to `/profile` if the expense does not exist or does not belong
  to the logged-in user
- `POST /expenses/<int:id>/edit` — validates and updates the expense row
  (only if it belongs to `session["user_id"]`), then redirects to
  `/profile` — access level: logged-in only; same not-found/not-owned
  handling as GET

## Database changes
No database changes. The existing `expenses` table (`user_id`, `amount`,
`category`, `date`, `description`, `created_at`) already has every column
this feature needs.

## Templates
- **Create:** `templates/edit_expense.html`
  - Extends `base.html`
  - Same structure and CSS classes as `templates/add_expense.html`
    (`auth-section`, `auth-container`, `auth-header`, `auth-card`,
    `auth-error`, `form-group`, `form-input`, `btn-submit`, `btn-ghost`) —
    no new CSS classes needed
  - Form fields: `amount` (number, step 0.01, min 0.01, required, pre-filled),
    `category` (select, populated from `database.db.CATEGORIES`, pre-selects
    the current category, required), `date` (date input, pre-filled with the
    expense's current date, required), `description` (text, optional,
    pre-filled)
  - Submit button labeled "Save changes"
  - A "Cancel" link back to `/profile`
- **Modify:** `templates/profile.html`
  - In the transaction history table, add an "Edit" link per row (in a new
    table column, or appended to an existing cell) pointing to
    `{{ url_for('edit_expense', id=t.id) }}`, styled with an existing link
    class (e.g. `btn-ghost` or a plain text link — no new CSS classes)

## Files to change
- `app.py` — implement `edit_expense(id)` for both `GET` and `POST`,
  guarded by `session.get("user_id")` and ownership of the expense
- `templates/profile.html` — add the per-row "Edit" link in the transaction
  table
- `database/queries.py`:
  - add `get_expense_by_id(user_id, expense_id)` returning the raw row
    (`id`, `amount`, `category`, `date`, `description`) or `None` if it
    doesn't exist or doesn't belong to `user_id`
  - add `update_expense(user_id, expense_id, amount, category, date,
    description)` that updates the row only `WHERE id = ? AND user_id = ?`
  - extend `get_recent_transactions` to also select and return `id` (needed
    to build the per-row edit link) — keep the existing formatted fields
    unchanged

## Files to create
- `templates/edit_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Passwords hashed with werkzeug (unchanged in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- `amount` must be validated server-side as a positive number (> 0); reject
  with an error message re-rendering the form (do not update) if missing,
  non-numeric, or <= 0
- `category` must be one of `database.db.CATEGORIES`; reject with an error
  message if an unrecognised value is submitted
- `date` must be a well-formed `YYYY-MM-DD` string; reject with an error
  message if missing or malformed
- `description` is optional; store `NULL` when blank (matches existing
  `get_recent_transactions` handling of `NULL` descriptions as "—")
- Every lookup and update of an expense must be scoped to
  `session["user_id"]` (`WHERE id = ? AND user_id = ?`) so one user can
  never view or modify another user's expense by guessing an id
- On successful update, redirect (not render) to `/profile` so a page
  refresh does not re-submit the form
- `get_expense_by_id` and `update_expense` in `database/queries.py` must
  call `get_db()` internally and close the connection before returning;
  `update_expense` must commit before closing
- Unauthenticated requests to either `GET` or `POST
  /expenses/<int:id>/edit` redirect to `/login`
- Requests for a non-existent or not-owned expense id redirect to
  `/profile` (do not leak whether the id exists for another user)

## Definition of done
- [ ] Visiting `/expenses/<id>/edit` while logged out redirects to `/login`
- [ ] Visiting `/expenses/<id>/edit` for an expense that does not belong to
      the logged-in user redirects to `/profile`
- [ ] Visiting `/expenses/<id>/edit` for a non-existent id redirects to
      `/profile`
- [ ] Visiting `/expenses/<id>/edit` for a valid, owned expense shows a form
      pre-filled with its current amount, category, date, and description
- [ ] Each row in the transaction history table on `/profile` has a working
      "Edit" link to that expense's edit page
- [ ] Submitting the form with valid data redirects to `/profile`
- [ ] The updated values appear in the transaction history table on
      `/profile` immediately after redirect
- [ ] Total spent, transaction count, and category breakdown on `/profile`
      reflect the updated expense (not the old values)
- [ ] Submitting with a missing or non-numeric amount re-renders the form
      with an error message and does not update the row
- [ ] Submitting with amount <= 0 re-renders the form with an error message
      and does not update the row
- [ ] Submitting with a missing or malformed date re-renders the form with
      an error message and does not update the row
- [ ] Submitting with an empty description succeeds and the transaction
      history shows "—" for that row
- [ ] No hex colour values appear in the new markup — only CSS variables
