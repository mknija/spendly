# Spec: Delete Expense

## Overview
Step 9 replaces the placeholder `/expenses/<int:id>/delete` route with a real
handler that lets a logged-in user permanently remove one of their own
existing expenses. Today the route just returns the string "Delete expense
— coming in Step 9". This step adds a POST-only handler that deletes the
matching row from the `expenses` table (scoped to the logged-in user), a way
to trigger it from the transaction history on `/profile`, and a
confirmation step so a user cannot delete a row by accident (e.g. a
misclick or a page prefetch). On success the user is redirected back to
`/profile` so the transaction history, totals, and category breakdown all
reflect the removal immediately.

## Depends on
- Step 1: Database setup (`expenses` table exists)
- Step 3: Login / Logout (`session["user_id"]` is set on login)
- Step 5: Backend routes for profile page (`database/queries.py` pattern,
  live `/profile` route to redirect back to)
- Step 8: Edit expense (`get_expense_by_id` ownership-lookup pattern this
  step reuses; per-row action link pattern added to `profile.html`)

## Routes
- `POST /expenses/<int:id>/delete` — deletes the expense row (only if it
  belongs to `session["user_id"]`), then redirects to `/profile` — access
  level: logged-in only (redirect to `/login` if not authenticated);
  redirect to `/profile` with no error if the expense does not exist or
  does not belong to the logged-in user (do not leak whether the id exists
  for another user)

No `GET /expenses/<int:id>/delete` route — deleting is a mutation and must
only happen via `POST`, submitted from a small form so it cannot be
triggered by a plain link click, page prefetch, or crawler.

## Database changes
No database changes. The existing `expenses` table already supports
row deletion by `id`/`user_id`; no new tables or columns are needed.

## Templates
- **Modify:** `templates/profile.html`
  - In the transaction history table, add a "Delete" action per row, next
    to the existing "Edit" link — implemented as a small
    `<form method="POST" action="{{ url_for('delete_expense', id=t.id) }}">`
    containing a single submit button (styled `btn-ghost`, matching the
    existing "Edit" link), so no full-page navigation form is needed
  - Add a JavaScript `confirm()` prompt on that form's `submit` event
    (e.g. `onsubmit="return confirm('Delete this expense?')"`) so the
    delete only proceeds if the user confirms — no new CSS classes, no new
    JS file needed beyond this inline handler

## Files to change
- `app.py` — implement `delete_expense(id)` as `POST`-only, guarded by
  `session.get("user_id")` and ownership of the expense
- `templates/profile.html` — add the per-row "Delete" form/button with a
  confirmation prompt in the transaction table
- `database/queries.py` — add `delete_expense_by_id(user_id, expense_id)`
  that deletes the row only `WHERE id = ? AND user_id = ?`

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Passwords hashed with werkzeug (unchanged in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- `delete_expense(id)` must only accept `POST` (`methods=["POST"]`) — no
  `GET` handling, so a delete can never be triggered by simply visiting a
  URL
- Every delete must be scoped to `session["user_id"]`
  (`WHERE id = ? AND user_id = ?`) so one user can never delete another
  user's expense by guessing an id
- Deleting a non-existent or not-owned expense id redirects to `/profile`
  with no error message (matches the existing not-found/not-owned handling
  in `edit_expense`) — do not raise a 404 or expose whether the id exists
- On successful delete, redirect (not render) to `/profile` so a page
  refresh does not re-submit the deletion
- `delete_expense_by_id` in `database/queries.py` must call `get_db()`
  internally, commit, and close the connection before returning
- Unauthenticated `POST` requests to `/expenses/<int:id>/delete` redirect
  to `/login`
- The delete action in `profile.html` must require a JS confirmation
  before submitting, so an accidental click cannot delete data silently

## Definition of done
- [ ] Submitting `POST /expenses/<id>/delete` while logged out redirects to
      `/login`
- [ ] Submitting `POST /expenses/<id>/delete` for an expense that does not
      belong to the logged-in user redirects to `/profile` and leaves that
      expense untouched
- [ ] Submitting `POST /expenses/<id>/delete` for a non-existent id
      redirects to `/profile` without error
- [ ] Each row in the transaction history table on `/profile` has a working
      "Delete" action that prompts for confirmation before submitting
- [ ] Confirming the prompt deletes the expense and redirects to `/profile`
- [ ] Cancelling the confirmation prompt does not submit the form or delete
      the expense
- [ ] The deleted expense no longer appears in the transaction history on
      `/profile` after redirect
- [ ] Total spent, transaction count, and category breakdown on `/profile`
      reflect the deletion (not the pre-delete values)
- [ ] Visiting `/expenses/<id>/delete` directly with a `GET` request does
      not delete the expense (method not allowed)
- [ ] No hex colour values appear in the modified markup — only CSS
      variables
