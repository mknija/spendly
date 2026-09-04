# Plan: Profile Page (Step 4) — hardcoded-data UI

## Context
`.claude/specs/04-profile-page.md` calls for replacing the `/profile` placeholder (`"Profile page — coming in Step 4"`) with a fully designed page, but with **all data hardcoded** — no DB queries yet. The stated goal is to lock down the UI (user info card, summary stats, transaction history table, category breakdown) before Step 5 wires it to real queries. This keeps the profile route auth-gated (redirect to `/login` when logged out) but everything it renders is a static Python dict/list passed straight to the template.

There is no `CLAUDE.md` in this repo (confirmed: not at root, not anywhere via glob) — consistent with what Steps 2 and 3's specs already noted, so nothing there to cross-check.

Per the user's answer to the navbar-scope question: add a "Profile" link to the navbar, but do **not** add a literal username anywhere (that would require also touching `/login`/`/register` to stash `name` in session, which is outside this spec's `Files to change` list).

## Reused patterns (from static/css/style.css and templates/)
- Layout wrapper: `.auth-section` / `.auth-container` (style.css, used in register.html/login.html) — narrow (`--auth-width: 440px`) auth-card wrapper. Profile needs a **wider** wrapper since it holds a table, so introduce a new `.profile-section` / `.profile-container` pair following the exact same convention (`max-width: var(--max-width)` i.e. 1200px, `margin: 0 auto`, matching `.legal-inner`/`.features-inner`), not the narrow auth one.
- Card: `.auth-card` (white `--paper-card` bg, `--border`, `--radius-md`, padding) — reused as-is for each of the four profile sections (info card, stats card, table card, breakdown card).
- Stats row: `.hero-v2-stats` / `.stat` / `.stat-label` / `.stat-value` (style.css ~234-286, used in landing.html) — reused for the "total spent / transaction count / top category" row.
- Category breakdown bars: `.hero-v2-bars` / `.v2-bar-row` / `.mock-cat` / `.mock-bar-track` / `.mock-bar` (+ `.mock-bar-2/3/4` color variants, style.css ~288-323) — reused for the per-category rows. Landing.html's only inline `style="width:X%"` usage is for these bars; the spec here says **no inline styles**, so bar-fill width instead uses fixed-percentage utility classes, not `style=`.
- No existing `.avatar`, table, or badge classes — these are new, built from existing CSS variables only (`--accent`, `--accent-light`, `--accent-2`, `--accent-2-light`, `--danger`, `--danger-light`, `--border`, `--paper-warm`, `--radius-*`), following the same "class per variant, no hex" convention as `.mock-bar-2/3/4`.

## Hardcoded data (mirrors seed_db() in database/db.py so it looks real)
User: name `Demo User`, email `demo@spendly.com`, member since `September 2026`, avatar initials `DU`.

Transactions (newest first):
| Date | Description | Category | Amount |
|---|---|---|---|
| Sep 20, 2026 | Dinner out | Food | ₹22.30 |
| Sep 17, 2026 | Miscellaneous | Other | ₹10.00 |
| Sep 14, 2026 | New shoes | Shopping | ₹60.20 |
| Sep 11, 2026 | Movie tickets | Entertainment | ₹15.75 |
| Sep 08, 2026 | Pharmacy | Health | ₹25.00 |
| Sep 05, 2026 | Electricity bill | Bills | ₹89.99 |
| Sep 03, 2026 | Bus fare | Transport | ₹12.00 |
| Sep 02, 2026 | Groceries | Food | ₹45.50 |

Stats: total spent `₹280.74`, transaction count `8`, top category `Bills`.

Category breakdown (total → rounded %): Bills 89.99 → 30%, Food 67.80 → 25%, Shopping 60.20 → 20%, Health 25.00 → 10%, Entertainment 15.75 → 5%, Transport 12.00 → 5%, Other 10.00 → 5% (sums to 100%).

Badge/bar color grouping (cycles through the 3 existing accent pairs + 1 neutral, since only 3 tinted var pairs exist):
- Group A (`--accent` / `--accent-light`): Food, Health
- Group B (`--accent-2` / `--accent-2-light`): Transport, Shopping
- Group C (`--danger` / `--danger-light`): Bills, Entertainment
- Group D (`--ink-muted` / `--paper-warm`): Other

## Files changed

### 1. `app.py`
Replaced the placeholder `/profile` view with a guarded, hardcoded-data view:
```python
@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = {"name": "Demo User", "email": "demo@spendly.com", "member_since": "September 2026", "initials": "DU"}
    stats = {"total_spent": 280.74, "transaction_count": 8, "top_category": "Bills"}
    transactions = [ ... 8 rows, see table above ... ]
    breakdown = [ ... 7 rows, see breakdown above ... ]
    return render_template(
        "profile.html", user=user, stats=stats, transactions=transactions, breakdown=breakdown
    )
```
No new imports needed — `session`, `redirect`, `url_for`, `render_template` were already imported.

### 2. `templates/base.html`
Added a "Profile" link inside the existing `{% if session.user_id %}` branch, before Logout:
```html
{% if session.user_id %}
<a href="{{ url_for('profile') }}">Profile</a>
<a href="{{ url_for('logout') }}" class="nav-cta">Logout</a>
{% else %}
```

### 3. `static/css/style.css`
Appended a new "Profile page" section with: `.profile-section` / `.profile-container` (wide wrapper), `.profile-header` / `.avatar` / `.profile-name` / `.profile-email` / `.profile-joined`, `.section-title`, `.table-scroll` + `.txn-table` (+`th`/`td`/`.txn-amount`), `.badge` + `.badge-a/b/c/d`, and `.bar-fill-5/10/20/25/30` fixed-width classes (applied to `.mock-bar` instead of an inline `width` style). Also added a small-screen rule stacking `.profile-header`.

### 4. `templates/profile.html` (new)
`{% extends "base.html" %}`, four `.auth-card` sections inside `.profile-section > .profile-container`:
1. **User info card**: `.avatar` with `{{ user.initials }}`, name, email, "Member since {{ user.member_since }}".
2. **Summary stats row**: `.hero-v2-stats`/`.stat` — total spent, transaction count, top category.
3. **Transaction history table**: `.txn-table`, one row per transaction, category cell as a `.badge` (color group looked up via a Jinja `badge_class` dict keyed by category).
4. **Category breakdown**: `.hero-v2-bars`/`.v2-bar-row`, bar div gets `class="{{ bar_class[category] }} bar-fill-{{ percent }}"`.

Empty-state handling wasn't needed since the hardcoded list is never empty in this step (a Step 5 concern once real queries land).

## Rules honored
No SQLAlchemy/ORM, no DB queries in the route (all literals), no inline styles anywhere in `profile.html` (percentages via `bar-fill-*` classes, colors via `badge-*`/`mock-bar-*` classes), only CSS variables (no hex) in new style.css rules, `profile.html` extends `base.html`.

## Outcome
Implemented on `feature/profile-page` and verified live via `python app.py` + curl:
- `GET /profile` while logged out → `302` to `/login`.
- `POST /login` (`demo@spendly.com` / `demo123`) → `302` to `/profile`.
- `GET /profile` while logged in → `200`, placeholder text gone.
- Rendered output: `₹280.74` total, `8` transactions, `Bills` top category, 8 transaction rows with badges, 7-row category breakdown with correct bar-fill classes.
- Zero `style="` attributes and zero hex colors (`#...`) anywhere in the rendered `profile.html` output.
- Navbar shows "Profile" + "Logout" while logged in, "Sign in"/"Get started" while logged out.
- Regression check: `/`, `/register`, `/login`, `/logout`, `/terms`, `/privacy` all still respond correctly.

Not yet committed — changes are sitting on `feature/profile-page` pending user review.
