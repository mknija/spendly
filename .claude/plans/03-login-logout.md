# Plan: Login and Logout (Step 3)

## Context
Spec `.claude/specs/03-login-logout.md` calls for a `POST /login` handler that validates credentials against the `users` table and starts a session, plus a working `GET /logout` that clears the session, and a session-aware navbar so a logged-in user can reach "Logout". This is required before any route (profile, expenses) can be gated behind a login-required check in a later step.

**Key finding from exploration:** the working tree already contains this exact implementation, uncommitted. `git status` shows `app.py` and `templates/base.html` as modified (not staged), matching every requirement in the spec byte-for-byte:

- `app.py`: `session` added to the Flask import, `check_password_hash` added to the werkzeug import, `/login` now accepts `GET, POST` with the full validate → lookup → verify → `session["user_id"]` → redirect-to-`/profile` flow (generic `"Invalid email or password."` error on any failure), and `/logout` now does `session.clear()` + `redirect(url_for("landing"))`.
- `templates/base.html`: navbar wrapped in `{% if session.user_id %}...{% else %}...{% endif %}`, showing "Logout" vs. "Sign in"/"Get started".
- `templates/login.html` already posts to `/login` and renders `{{ error }}` — untouched, as the spec expects.
- `database/db.py` already has `get_db()`, the `users` table (`id`, `name`, `email`, `password_hash`), and seeds a `demo@spendly.com` / `demo123` account — nothing here needs to change, and nothing does.

So there is no remaining **code** to write for this step. The plan below is a verification pass against the spec's Definition of Done, followed by committing the already-written changes — no new implementation.

## Verification steps (run the app, exercise each DoD item)
1. Start the app: `python app.py` (runs on port 5001), confirm no startup errors and `/`, `/register`, `/terms`, `/privacy` still load.
2. `GET /login` — confirm the form renders unchanged.
3. Submit the login form with `demo@spendly.com` / `demo123` — confirm redirect to `/profile` (currently the Step-4 placeholder text) and that a session cookie is set.
4. Submit with a non-existent email — confirm `login.html` re-renders with the generic error and no session is set.
5. Submit with `demo@spendly.com` and a wrong password — confirm the same generic error, no session set.
6. Submit with a missing field (e.g. blank password) — confirm a visible error, no session set.
7. While logged in, check the navbar shows "Logout" instead of "Sign in"/"Get started".
8. Visit `/logout` — confirm session is cleared and it redirects to `/`, and the navbar reverts to "Sign in"/"Get started".
9. Confirm `/logout` is safe to hit while already logged out (just redirects, no error).

## After verification
- If all checks pass, stage and commit `app.py` and `templates/base.html` (the spec file `.claude/specs/03-login-logout.md` is already tracked as untracked/new and can be added too, following this repo's pattern from prior steps of committing the spec alongside the implementation).
- If any check fails, fix the specific discrepancy in `app.py` / `templates/base.html` (the code already closely follows the spec, so a failure would likely be a small deviation, not a missing feature) and re-verify.

## Out of scope (per spec)
- No login-required guard on `/profile` or other routes — that's Step 4.
- No changes to the `users`/`expenses` schema.
- No new dependencies.

## Outcome
All verification steps were run against the live app via curl and passed. Changes were committed as `bde3576` on `feature/login-logout`.
