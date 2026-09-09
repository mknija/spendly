from datetime import datetime

from database.db import get_db


def _date_clause(start_date, end_date):
    if start_date and end_date:
        return " AND date >= ? AND date <= ?", [start_date, end_date]
    return "", []


def get_user_by_id(user_id):
    db = get_db()
    row = db.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    db.close()

    if row is None:
        return None

    member_since = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S").strftime("%B %Y")
    return {"name": row["name"], "email": row["email"], "member_since": member_since}


# --- SUBAGENT 2: SUMMARY STATS ------------------------------------------
def get_summary_stats(user_id, start_date=None, end_date=None):
    """Return dict with total_spent, transaction_count, top_category.
    No expenses -> {"total_spent": 0, "transaction_count": 0, "top_category": "—"}.
    """
    db = get_db()
    clause, extra_params = _date_clause(start_date, end_date)
    where = "WHERE user_id = ?" + clause
    params = [user_id] + extra_params

    total_spent = db.execute(
        f"SELECT COALESCE(SUM(amount), 0) FROM expenses {where}", params
    ).fetchone()[0]

    transaction_count = db.execute(
        f"SELECT COUNT(*) FROM expenses {where}", params
    ).fetchone()[0]

    row = db.execute(
        f"SELECT category FROM expenses {where} "
        "GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
        params,
    ).fetchone()
    top_category = row["category"] if row is not None else "—"

    db.close()

    return {
        "total_spent": total_spent,
        "transaction_count": transaction_count,
        "top_category": top_category,
    }
# -------------------------------------------------------------------------


# --- SUBAGENT 1: TRANSACTION HISTORY -------------------------------------
def get_recent_transactions(user_id, limit=10, start_date=None, end_date=None):
    """Return list of dicts {date, description, category, amount}, newest
    first, date formatted "%b %d, %Y", description "—" if NULL.
    Empty list if no expenses.
    """
    db = get_db()
    clause, extra_params = _date_clause(start_date, end_date)
    rows = db.execute(
        "SELECT date, description, category, amount FROM expenses "
        f"WHERE user_id = ?{clause} ORDER BY date DESC, created_at DESC LIMIT ?",
        [user_id] + extra_params + [limit],
    ).fetchall()
    db.close()

    transactions = []
    for row in rows:
        display_date = datetime.strptime(row["date"], "%Y-%m-%d").strftime("%b %d, %Y")
        transactions.append(
            {
                "date": display_date,
                "description": row["description"] or "—",
                "category": row["category"],
                "amount": row["amount"],
            }
        )
    return transactions
# -------------------------------------------------------------------------


# --- SUBAGENT 3: CATEGORY BREAKDOWN --------------------------------------
def get_category_breakdown(user_id, start_date=None, end_date=None):
    """Return list of dicts {name, amount, pct}, ordered by amount desc;
    pct values are ints summing to 100 (largest category absorbs the
    rounding remainder). Empty list if no expenses.
    """
    db = get_db()
    clause, extra_params = _date_clause(start_date, end_date)
    rows = db.execute(
        "SELECT category, SUM(amount) AS total FROM expenses "
        f"WHERE user_id = ?{clause} GROUP BY category ORDER BY total DESC",
        [user_id] + extra_params,
    ).fetchall()
    db.close()

    if not rows:
        return []

    grand_total = sum(row["total"] for row in rows)
    rounded_pcts = [round(row["total"] / grand_total * 100) for row in rows]
    remainder = 100 - sum(rounded_pcts)
    rounded_pcts[0] += remainder

    return [
        {"name": row["category"], "amount": row["total"], "pct": pct}
        for row, pct in zip(rows, rounded_pcts)
    ]
# -------------------------------------------------------------------------


def insert_expense(user_id, amount, category, expense_date, description):
    """Insert a new expense row for user_id. description may be None."""
    db = get_db()
    db.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, expense_date, description),
    )
    db.commit()
    db.close()
