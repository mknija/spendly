"""
Tests for Step 7: Add Expense.

Spec: .claude/specs/07-add-expense.md

These tests treat `GET /expenses/add` and `POST /expenses/add` as a black
box and assert only on the documented behavior: the form is auth-guarded,
valid submissions insert a row for the current user and redirect to
`/profile` (where the new expense is reflected in transaction history,
summary stats, and category breakdown), invalid submissions re-render the
form with an error and do not touch the database, and blank descriptions
are stored as NULL / displayed as "—".
"""

from datetime import datetime

import pytest

from database.db import CATEGORIES, get_db


EMAIL = "addexpense@example.com"


def _register_and_login(client, email=EMAIL, name="Add Expense User"):
    client.post(
        "/register",
        data={
            "name": name,
            "email": email,
            "password": "password123",
            "confirm_password": "password123",
        },
    )
    client.post("/login", data={"email": email, "password": "password123"})
    db = get_db()
    row = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    db.close()
    return row["id"]


@pytest.fixture
def logged_in_client(client):
    """A logged-in client for a fresh user with zero existing expenses."""
    _register_and_login(client)
    return client


def _user_id(email=EMAIL):
    db = get_db()
    row = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    db.close()
    return row["id"]


def _expense_count(user_id):
    db = get_db()
    count = db.execute(
        "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    db.close()
    return count


def _total_expense_count():
    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    db.close()
    return count


def _fetch_expenses(user_id):
    db = get_db()
    rows = db.execute(
        "SELECT amount, category, date, description FROM expenses WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    db.close()
    return rows


# --- Auth guard: unauthenticated requests redirect to /login --------------

def test_get_add_expense_redirects_when_logged_out(client):
    response = client.get("/expenses/add")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_post_add_expense_redirects_when_logged_out(client):
    response = client.post(
        "/expenses/add",
        data={
            "amount": "25.00",
            "category": "Food",
            "date": "2026-01-01",
            "description": "Should not be inserted",
        },
    )
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_post_add_expense_while_logged_out_does_not_insert_row(client):
    before = _total_expense_count()
    client.post(
        "/expenses/add",
        data={
            "amount": "25.00",
            "category": "Food",
            "date": "2026-01-01",
            "description": "Should not be inserted",
        },
    )
    after = _total_expense_count()
    assert after == before, "Unauthenticated POST must not insert an expense row"


# --- GET form rendering (logged in) ----------------------------------------

def test_get_add_expense_form_when_logged_in_shows_all_fields(logged_in_client):
    response = logged_in_client.get("/expenses/add")
    assert response.status_code == 200
    body = response.get_data(as_text=True)

    assert 'name="amount"' in body, "Expected an amount input field"
    assert 'name="category"' in body, "Expected a category select field"
    assert 'name="date"' in body, "Expected a date input field"
    assert 'name="description"' in body, "Expected a description input field"
    assert "Add expense" in body, "Expected the submit button labeled 'Add expense'"


def test_get_add_expense_form_prefills_date_with_today(logged_in_client):
    response = logged_in_client.get("/expenses/add")
    body = response.get_data(as_text=True)
    today_str = datetime.today().strftime("%Y-%m-%d")
    assert today_str in body, "Expected the date field to be pre-filled with today's date"


def test_get_add_expense_form_lists_all_categories(logged_in_client):
    response = logged_in_client.get("/expenses/add")
    body = response.get_data(as_text=True)
    for category in CATEGORIES:
        assert category in body, f"Expected category option '{category}' in the form"


def test_get_add_expense_form_has_cancel_link_to_profile(logged_in_client):
    response = logged_in_client.get("/expenses/add")
    body = response.get_data(as_text=True)
    assert "Cancel" in body, "Expected a Cancel link"
    assert "/profile" in body, "Expected the Cancel link to point back to /profile"


# --- POST happy path: valid submission inserts and redirects --------------

def test_post_valid_expense_redirects_to_profile(logged_in_client):
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "42.50",
            "category": "Food",
            "date": "2026-05-01",
            "description": "Lunch with client",
        },
    )
    assert response.status_code == 302
    assert "/profile" in response.headers["Location"]


def test_post_valid_expense_inserts_row_in_db(logged_in_client):
    user_id = _user_id()
    assert _expense_count(user_id) == 0

    logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "42.50",
            "category": "Food",
            "date": "2026-05-01",
            "description": "Lunch with client",
        },
    )

    assert _expense_count(user_id) == 1
    rows = _fetch_expenses(user_id)
    assert rows[0]["amount"] == pytest.approx(42.50)
    assert rows[0]["category"] == "Food"
    assert rows[0]["date"] == "2026-05-01"
    assert rows[0]["description"] == "Lunch with client"


def test_post_valid_expense_appears_in_transaction_history_on_profile(logged_in_client):
    logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "42.50",
            "category": "Food",
            "date": "2026-05-01",
            "description": "Lunch with client",
        },
    )
    response = logged_in_client.get("/profile")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Lunch with client" in body
    assert "May 01, 2026" in body


def test_post_valid_expense_updates_summary_stats_on_profile(logged_in_client):
    logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "42.50",
            "category": "Food",
            "date": "2026-05-01",
            "description": "Lunch with client",
        },
    )
    response = logged_in_client.get("/profile")
    body = response.get_data(as_text=True)
    assert "₹42.50" in body, "Expected total spent to reflect the new expense"
    assert ">1<" in body, "Expected transaction count to reflect the new expense"


def test_post_valid_expense_updates_category_breakdown_on_profile(logged_in_client):
    logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "42.50",
            "category": "Food",
            "date": "2026-05-01",
            "description": "Lunch with client",
        },
    )
    response = logged_in_client.get("/profile")
    body = response.get_data(as_text=True)
    assert "Food" in body
    assert "100" in body, "Single-category breakdown should show 100%"


# --- Validation: amount ------------------------------------------------

@pytest.mark.parametrize(
    "bad_amount",
    ["", "abc", "0", "-10"],
    ids=["missing", "non_numeric", "zero", "negative"],
)
def test_post_invalid_amount_rerenders_form_without_inserting(logged_in_client, bad_amount):
    user_id = _user_id()
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": bad_amount,
            "category": "Food",
            "date": "2026-05-01",
            "description": "Bad amount",
        },
    )
    assert response.status_code == 200, "Invalid amount must re-render the form, not redirect"
    body = response.get_data(as_text=True)
    assert "auth-error" in body, "Expected an error message re-rendered on the form"
    assert _expense_count(user_id) == 0, "Invalid amount must not insert a row"


def test_post_missing_amount_field_entirely_rerenders_form_without_inserting(logged_in_client):
    user_id = _user_id()
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "category": "Food",
            "date": "2026-05-01",
            "description": "No amount field at all",
        },
    )
    assert response.status_code == 200
    assert "auth-error" in response.get_data(as_text=True)
    assert _expense_count(user_id) == 0


# --- Validation: category -----------------------------------------------

def test_post_invalid_category_rerenders_form_without_inserting(logged_in_client):
    user_id = _user_id()
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "20.00",
            "category": "NotARealCategory",
            "date": "2026-05-01",
            "description": "Bad category",
        },
    )
    assert response.status_code == 200
    assert "auth-error" in response.get_data(as_text=True)
    assert _expense_count(user_id) == 0


def test_post_missing_category_field_entirely_rerenders_form_without_inserting(logged_in_client):
    user_id = _user_id()
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "20.00",
            "date": "2026-05-01",
            "description": "No category field at all",
        },
    )
    assert response.status_code == 200
    assert "auth-error" in response.get_data(as_text=True)
    assert _expense_count(user_id) == 0


# --- Validation: date -----------------------------------------------------

@pytest.mark.parametrize(
    "bad_date",
    ["", "not-a-date", "2026/05/01", "05-01-2026", "2026-13-40"],
    ids=[
        "missing",
        "non_date_text",
        "slash_format",
        "us_format",
        "invalid_calendar_date",
    ],
)
def test_post_invalid_date_rerenders_form_without_inserting(logged_in_client, bad_date):
    user_id = _user_id()
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "20.00",
            "category": "Food",
            "date": bad_date,
            "description": "Bad date",
        },
    )
    assert response.status_code == 200, "Malformed date must re-render the form, not redirect"
    body = response.get_data(as_text=True)
    assert "auth-error" in body, "Expected an error message re-rendered on the form"
    assert _expense_count(user_id) == 0, "Malformed date must not insert a row"


def test_post_missing_date_field_entirely_rerenders_form_without_inserting(logged_in_client):
    user_id = _user_id()
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "20.00",
            "category": "Food",
            "description": "No date field at all",
        },
    )
    assert response.status_code == 200
    assert "auth-error" in response.get_data(as_text=True)
    assert _expense_count(user_id) == 0


# --- Optional description handling -----------------------------------------

def test_post_blank_description_succeeds_and_stores_null(logged_in_client):
    user_id = _user_id()
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "15.00",
            "category": "Other",
            "date": "2026-05-02",
            "description": "",
        },
    )
    assert response.status_code == 302, "Blank description is optional; submission should succeed"

    rows = _fetch_expenses(user_id)
    assert len(rows) == 1
    assert rows[0]["description"] is None, "Blank description must be stored as NULL"


def test_post_missing_description_field_stored_as_null(logged_in_client):
    user_id = _user_id()
    logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "15.00",
            "category": "Other",
            "date": "2026-05-02",
        },
    )
    rows = _fetch_expenses(user_id)
    assert len(rows) == 1
    assert rows[0]["description"] is None


def test_post_blank_description_displays_em_dash_in_transaction_history(logged_in_client):
    logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "15.00",
            "category": "Other",
            "date": "2026-05-02",
            "description": "",
        },
    )
    response = logged_in_client.get("/profile")
    body = response.get_data(as_text=True)
    assert "—" in body, "Expected NULL description to display as em dash '—'"


# --- DB side effects: row count changes only on successful insert ---------

def test_expense_count_unchanged_after_failed_validation_then_increases_after_success(
    logged_in_client,
):
    user_id = _user_id()
    assert _expense_count(user_id) == 0

    # Invalid submission (amount <= 0) must not insert a row.
    logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "-5",
            "category": "Food",
            "date": "2026-05-01",
            "description": "Invalid",
        },
    )
    assert _expense_count(user_id) == 0

    # Valid submission must insert exactly one row.
    logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "5.00",
            "category": "Food",
            "date": "2026-05-01",
            "description": "Valid",
        },
    )
    assert _expense_count(user_id) == 1
