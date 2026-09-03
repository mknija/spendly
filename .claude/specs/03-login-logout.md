# Spec: Login and Logout

## Overview
This feature implements authentication for existing accounts. The `login.html` template and `GET /login` route already exist, but the form has no handler — submitting it does nothing. `GET /logout` currently returns the placeholder text `"Logout — coming in Step 3"`. This step adds the `POST /login` route that validates credentials against the `users` table (schema and `get_db()` from Step 1) and starts a session, plus a working `/logout` route that clears the session. It also makes the navbar session-aware so a logged-in user can actually reach the logout link. This is the third step on the roadmap and is required before any route can be gated behind "must be logged in" (profile, expenses).

Note: no `CLAUDE.md` was found in the project root, so roadmap/step-completion status could not be cross-checked against it. Scope was inferred from `app.py`'s placeholder comment (`Logout — coming in Step 3`), the existing `login.html` template, and `.claude/specs/02-registration.md`.

## Depends on
- Step 1 — Database setup (`database/db.py`: `get_db()`, `users` table with `id`, `email`, `password_hash`)
- Step 2 — Registration (existing users to log in with; `app.secret_key` already configured from `SECRET_KEY` env var in `app.py`)

## Routes
- `POST /login` — accepts `email`, `password` form fields; validates credentials, starts session, redirects to `/profile` — public
- `GET /login` — already implemented (renders the form) — public, no change needed unless re-rendering with `error`
- `GET /logout` — clears the session and redirects to the landing page — logged-in (safe to call when already logged out; it just redirects)

## Database changes
No database changes. The `users` table already has every column this feature needs: `email`, `password_hash`.

## Templates
- **Create:** none
- **Modify:**
  - `templates/login.html` — already posts to `/login` and already renders `{{ error }}`; no structural change needed
  - `templates/base.html` — make the navbar session-aware: when `session.user_id` is set, show a "Logout" link (`href="{{ url_for('logout') }}"`) instead of "Sign in" / "Get started"

## Files to change
- `app.py`:
  - Add `from werkzeug.security import check_password_hash` (extend existing `werkzeug.security` import)
  - Add `session` to the existing `flask` import
  - Implement `POST /login`:
    - Read `email`, `password` from `request.form`
    - Validate both are present and non-empty; on failure re-render `login.html` with `error`
    - Look up the user by email; if not found, re-render `login.html` with `error="Invalid email or password."`
    - Verify the password with `check_password_hash`; if it doesn't match, re-render `login.html` with the same generic error (never reveal whether the email or the password was wrong)
    - On success, store `session["user_id"] = user["id"]` and redirect to `/profile`
  - Implement `GET /logout`:
    - Call `session.clear()`
    - Redirect to `/` (landing page)
- `templates/base.html`:
  - Wrap the existing "Sign in" / "Get started" links in `{% if not session.user_id %}...{% else %}...{% endif %}`, showing a "Logout" link in the `else` branch

## Files to create
None.

## New dependencies
No new dependencies. `werkzeug.security.check_password_hash` is already installed; `flask.session` is part of Flask core.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Reuse the `get_db()` connection pattern from `database/db.py` exactly as-is (`sqlite3.Row` row factory)
- Do not modify the `users` or `expenses` schema
- Use one generic error message for both "email not found" and "wrong password" so login never leaks which part was incorrect
- Do not add a login-required guard to `/profile` or other routes in this step — that belongs to the profile feature (Step 4)

## Definition of done
- [ ] `POST /login` with a valid, existing email and matching password sets `session["user_id"]` and redirects to `/profile`
- [ ] Submitting the existing `login.html` form end-to-end (e.g. with the seeded `demo@spendly.com` / `demo123` account) logs the user in
- [ ] `POST /login` with an email that doesn't exist re-renders `login.html` with a visible generic error and does not set a session
- [ ] `POST /login` with a wrong password for an existing email re-renders `login.html` with the same generic error and does not set a session
- [ ] `POST /login` with a missing field re-renders `login.html` with a visible error and does not set a session
- [ ] After logging in, visiting `/logout` clears the session and redirects to `/`
- [ ] After `/logout`, the navbar shows "Sign in" / "Get started" again instead of "Logout"
- [ ] While logged in, the navbar shows a "Logout" link instead of "Sign in" / "Get started"
- [ ] `GET /login` still renders the form unchanged
- [ ] App starts without errors and existing routes (`/`, `/register`, `/terms`, `/privacy`) are unaffected
