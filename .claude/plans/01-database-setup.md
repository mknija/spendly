# Database Setup — Implementation Plan

## Context

Spendly needs a data layer foundation — a SQLite database with `users` and `expenses` tables — that every future feature (auth, profile, expense CRUD) depends on. The spec (`.claude/specs/01-database-setup.md`) fully defines the schema and required functions.

`.gitignore` already excludes `expense_tracker.db`, confirming that filename is the intended database name (not `spendly.db`).

**Status: already implemented.** `database/db.py` and `app.py` in the working tree currently contain the full implementation described below — this plan documents the design as built, verified against the spec's Definition of Done.

## Files Changed

### `database/db.py` (replaced stub with full implementation)

1. **Imports**: `sqlite3`, `os`, `datetime.date`, `generate_password_hash` from `werkzeug.security`.
2. **`DB_PATH`**: absolute path to `expense_tracker.db` in the project root, computed via `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`, so it works regardless of the process's working directory.
3. **`get_db()`**:
   - `sqlite3.connect(DB_PATH)`
   - `conn.row_factory = sqlite3.Row`
   - `conn.execute("PRAGMA foreign_keys = ON")`
   - return `conn`
4. **`init_db()`**:
   - Opens a connection via `get_db()`
   - `CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')))`
   - `CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, amount REAL NOT NULL, category TEXT NOT NULL, date TEXT NOT NULL, description TEXT, created_at TEXT DEFAULT (datetime('now')), FOREIGN KEY (user_id) REFERENCES users(id))`
   - commit, close
5. **`seed_db()`**:
   - Opens a connection via `get_db()`
   - `SELECT COUNT(*) FROM users` — if count > 0, closes connection and returns early (idempotent)
   - Inserts demo user: name `Demo User`, email `demo@spendly.com`, `password_hash = generate_password_hash("demo123")` via parameterized `INSERT`
   - Uses `cursor.lastrowid` to get the new user's id
   - Inserts 8 sample expenses tied to that `user_id`, covering all 7 categories (Food, Transport, Bills, Health, Entertainment, Shopping, Other, with Food repeated for the 8th) with `date` values in `YYYY-MM-DD` format spread across the current month (computed via `datetime.date.today()`, not hardcoded), via `executemany` with `?` placeholders
   - commit, close

All SQL uses `?` placeholders exclusively — no f-strings/`.format()` in query text (dates/amounts are passed as bound parameters, not interpolated into SQL).

### `app.py`

1. Added import: `from database.db import get_db, init_db, seed_db`
2. After `app = Flask(__name__)`, added:
   ```python
   with app.app_context():
       init_db()
       seed_db()
   ```
3. No route logic changes — existing placeholder routes unchanged.

## Verification (already performed)

1. Fresh run of `python app.py` creates `expense_tracker.db` in the project root with no errors.
2. Second run does not duplicate seed data (`users` count stays 1, `expenses` count stays 8).
3. Inspected via `get_db()`: 1 user with a hashed (non-plaintext) password, 8 expenses across all 7 categories with `YYYY-MM-DD` dates.
4. Constraint enforcement confirmed: inserting a duplicate email raises `sqlite3.IntegrityError` (UNIQUE constraint failed: users.email); inserting an expense with a non-existent `user_id` raises `sqlite3.IntegrityError` (FOREIGN KEY constraint failed).
5. Existing routes (`/`, `/register`, `/login`, `/terms`, `/privacy`) confirmed to still return 200 via Flask test client.

## Outstanding

None — all items in the spec's Definition of Done are satisfied. No further action needed for this step.
