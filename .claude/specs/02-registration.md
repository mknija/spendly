# Spec: Registration

## Overview
This feature implements account creation for Spendly. The `register.html` template and `GET /register` route already exist, but the form has no handler — submitting it does nothing. This step adds the `POST /register` route that validates input, hashes the password, inserts a new row into the `users` table (schema and `get_db()` already implemented in Step 1), and starts a logged-in session for the new user. This is the second step on the roadmap and the foundation every later authenticated feature (login, logout, profile, expenses) builds on.

Note: no `CLAUDE.md` was found in the project root, so roadmap/step-completion status could not be cross-checked against it. Scope below was inferred from `app.py`'s placeholder comments (`Logout — coming in Step 3`, `Profile page — coming in Step 4`, etc.) and the existing templates.

## Depends on
- Step 1 — Database setup (`database/db.py`: `get_db()`, `init_db()`, `users` table with `id`, `name`, `email`, `password_hash`, `created_at`)

## Routes
- `POST /register` — accepts `name`, `email`, `password` form fields; validates, hashes password, inserts user, starts session, redirects to a logged-in landing point — public
- `GET /register` — already implemented (renders the form) — public, no change needed unless re-rendering with `error`

## Database changes
No database changes. The `users` table (from `database/db.py`) already has every column this feature needs: `name`, `email`, `password_hash`, `created_at`.

## Templates
- **Create:** none
- **Modify:** `templates/register.html` — already posts to `/register` and already renders `{{ error }}`; no structural change expected, only reuse of the existing `error` block for validation/duplicate-email messages

## Files to change
- `app.py`:
  - Set `app.secret_key` from an environment variable (no session support exists yet — `SECRET_KEY` is not currently read anywhere)
  - Add `from flask import request, redirect, url_for, session` (extend existing `flask` import)
  - Add `from werkzeug.security import generate_password_hash`
  - Add `from database.db import get_db` to the existing `database.db` import
  - Implement `POST /register`:
    - Read `name`, `email`, `password` from `request.form`
    - Validate all three are present and non-empty; validate password length ≥ 8 characters (matches the placeholder text `Min. 8 characters` in `register.html`)
    - On validation failure, re-render `register.html` with `error` set, same as the template already expects
    - Check for an existing user with that email; if found, re-render with `error="An account with this email already exists."`
    - Hash the password with `generate_password_hash`
    - Insert the new user via a parameterized `INSERT`
    - Store `session["user_id"] = <new id>` to log the user in immediately after registration
    - Redirect to `/profile` (the next placeholder route) since no dashboard exists yet

## Files to create
None.

## New dependencies
No new dependencies. `werkzeug.security` is already installed; `flask.session` is part of Flask core.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Reuse the `get_db()` connection pattern from `database/db.py` exactly as-is (`sqlite3.Row` row factory, `PRAGMA foreign_keys = ON`)
- Do not modify the `users` or `expenses` schema
- `app.secret_key` must come from an environment variable, never hardcoded in source

## Definition of done
- [ ] `POST /register` with valid, unique `name`/`email`/`password` (≥ 8 chars) creates a row in `users` with a hashed `password_hash`
- [ ] Submitting the existing `register.html` form end-to-end creates an account and redirects to `/profile`
- [ ] After successful registration, `session["user_id"]` is set to the new user's id
- [ ] Registering with an email that already exists in `users` re-renders `register.html` with a visible error and does not insert a duplicate row
- [ ] Registering with a missing field or a password under 8 characters re-renders `register.html` with a visible error and does not insert a row
- [ ] `GET /register` still renders the form unchanged
- [ ] Passwords are never stored or logged in plaintext
- [ ] App starts without errors and existing routes (`/`, `/login`, `/terms`, `/privacy`) are unaffected
