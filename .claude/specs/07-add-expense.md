# Spec: Add Expense

## Overview
Step 7 replaces the placeholder `/expenses/add` route with a real form that
lets a logged-in user record a new expense. Today the route just returns the
string "Add expense — coming in Step 7". This step adds a GET form (amount,
category, date, description) and a POST handler that validates the input,
inserts a row into the `expenses` table for the current user, and redirects
back to `/profile` so the new expense is immediately visible in the
transaction history, summary stats, and category breakdown.

## Depends on
- Step 1: Database setup (`expenses` table exists)
- Step 3: Login / Logout (`session["user_id"]` is set on login)
- Step 5: Backend routes for profile page (`database/queries.py` pattern,
  live `/profile` route to redirect back to)

## Routes
- `GET /expenses/add` — renders the add-expense form, pre-filling date with
  today's date — access level: logged-in only (redirect to `/login` if not
  authenticated)
- `POST /expenses/add` — validates and inserts the new expense for
  `session["user_id"]`, then redirects to `/profile` — access level:
  logged-in only

## Database changes
No database changes. The existing `expenses` table (`user_id`, `amount`,
`category`, `date`, `description`, `created_at`) already has every column
this feature needs.

## Templates
- **Create:** `templates/add_expense.html`
  - Extends `base.html`
  - Form fields: `amount` (number, step 0.01, min 0.01, required), `category`
    (select, populated from `database.db.CATEGORIES`, required), `date`
    (date input, defaults to today, required), `description` (text, optional)
  - Submit button labeled "Add expense"
  - A "Cancel" link back to `/profile`
  - Reuses existing form styling (`form-group`, `form-input`, `btn-submit`,
    `btn-ghost`, `auth-card`, `auth-error`) already established in
    `profile.html` / `register.html` — no new CSS classes needed
- **Modify:** `templates/profile.html`
  - Add an "Add expense" link/button (using existing `btn-submit` or
    `nav-cta` styling) near the Summary or Transaction history section that
    points to `{{ url_for('add_expense') }}`

## Files to change
- `app.py` — implement `add_expense()` for both `GET` and `POST`, guarded by
  `session.get("user_id")`
- `templates/profile.html` — add the "Add expense" link
- `database/queries.py` — add `insert_expense(user_id, amount, category,
  date, description)` helper

## Files to create
- `templates/add_expense.html`

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
  with an error message re-rendering the form (do not insert) if missing,
  non-numeric, or <= 0
- `category` must be one of `database.db.CATEGORIES`; reject with an error
  message if an unrecognised value is submitted
- `date` must be a well-formed `YYYY-MM-DD` string; reject with an error
  message if missing or malformed
- `description` is optional; store `NULL` when blank (matches existing
  `get_recent_transactions` handling of `NULL` descriptions as "—")
- On successful insert, redirect (not render) to `/profile` so a page
  refresh does not re-submit the form
- `insert_expense` in `database/queries.py` must call `get_db()` internally,
  commit, and close the connection before returning
- Unauthenticated requests to either `GET` or `POST /expenses/add` redirect
  to `/login`

## Definition of done
- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in shows a form with amount,
      category, date (pre-filled with today), and description fields
- [ ] Submitting the form with valid data redirects to `/profile`
- [ ] The newly added expense appears in the transaction history table on
      `/profile` immediately after redirect
- [ ] Total spent, transaction count, and category breakdown on `/profile`
      reflect the newly added expense
- [ ] Submitting with a missing or non-numeric amount re-renders the form
      with an error message and does not insert a row
- [ ] Submitting with amount <= 0 re-renders the form with an error message
      and does not insert a row
- [ ] Submitting with a missing or malformed date re-renders the form with
      an error message and does not insert a row
- [ ] Submitting with an empty description succeeds and the transaction
      history shows "—" for that row
- [ ] No hex colour values appear in the new markup — only CSS variables
