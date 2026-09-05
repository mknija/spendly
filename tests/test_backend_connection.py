from datetime import datetime

import pytest

from database.db import get_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)


def _demo_user_id():
    db = get_db()
    row = db.execute("SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)).fetchone()
    db.close()
    return row["id"]


def _create_user(name, email):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, "not-a-real-hash"),
    )
    db.commit()
    user_id = cursor.lastrowid
    db.close()
    return user_id


# --- Unit tests: database/queries.py -------------------------------------

def test_get_user_by_id_valid(app):
    result = get_user_by_id(_demo_user_id())
    assert result["name"] == "Demo User"
    assert result["email"] == "demo@spendly.com"
    assert result["member_since"]


def test_get_user_by_id_nonexistent(app):
    assert get_user_by_id(999999) is None


def test_get_summary_stats_with_expenses(app):
    stats = get_summary_stats(_demo_user_id())
    assert stats["total_spent"] == pytest.approx(280.74)
    assert stats["transaction_count"] == 8
    assert stats["top_category"] == "Bills"


def test_get_summary_stats_no_expenses(app):
    user_id = _create_user("No Expenses", "noexpenses@example.com")
    assert get_summary_stats(user_id) == {
        "total_spent": 0,
        "transaction_count": 0,
        "top_category": "—",
    }


def test_get_recent_transactions_with_expenses(app):
    transactions = get_recent_transactions(_demo_user_id())
    assert len(transactions) == 8
    for txn in transactions:
        assert set(txn.keys()) == {"date", "description", "category", "amount"}
    parsed_dates = [datetime.strptime(t["date"], "%b %d, %Y") for t in transactions]
    assert parsed_dates == sorted(parsed_dates, reverse=True)


def test_get_recent_transactions_no_expenses(app):
    user_id = _create_user("No Transactions", "notxns@example.com")
    assert get_recent_transactions(user_id) == []


def test_get_category_breakdown_with_expenses(app):
    breakdown = get_category_breakdown(_demo_user_id())
    assert len(breakdown) == 7
    amounts = [row["amount"] for row in breakdown]
    assert amounts == sorted(amounts, reverse=True)
    assert sum(row["pct"] for row in breakdown) == 100


def test_get_category_breakdown_no_expenses(app):
    user_id = _create_user("No Breakdown", "nobreakdown@example.com")
    assert get_category_breakdown(user_id) == []


# --- Route tests -----------------------------------------------------------

def test_profile_redirects_when_logged_out(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_profile_authenticated_seed_user(client):
    login_response = client.post(
        "/login", data={"email": "demo@spendly.com", "password": "demo123"}
    )
    assert login_response.status_code == 302

    response = client.get("/profile")
    assert response.status_code == 200
    body = response.get_data(as_text=True)

    assert "Demo User" in body
    assert "demo@spendly.com" in body
    assert "₹280.74" in body
    assert ">8<" in body
    assert "Bills" in body

    first_date_index = body.find("Sep 20, 2026")
    last_date_index = body.find("Sep 02, 2026")
    assert first_date_index != -1 and last_date_index != -1
    assert first_date_index < last_date_index

    for category in ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]:
        assert category in body


def test_profile_new_user_zero_expenses(client):
    client.post(
        "/register",
        data={
            "name": "Fresh User",
            "email": "fresh@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
    )
    client.post("/login", data={"email": "fresh@example.com", "password": "password123"})
    response = client.get("/profile")
    assert response.status_code == 200
    assert "₹0.00" in response.get_data(as_text=True)
