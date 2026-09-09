"""
Tests for Step 6: Date Filter For Profile.

Spec: .claude/specs/06-date-filter-for-profile.md

These tests treat `GET /profile` (with the optional `start_date` /
`end_date` query-string parameters) as a black box and assert on its
documented behavior only. Fixture data uses fixed, known dates (rather
than the seeded demo data, whose dates are relative to "today") so that
date-range assertions are deterministic.
"""

import pytest

from database.db import get_db
from database.queries import get_category_breakdown


# --- Fixed fixture data -----------------------------------------------------
# amount, category, date (YYYY-MM-DD), description
FIXED_EXPENSES = [
    (10.00, "Food", "2026-01-05", "January groceries"),
    (20.00, "Transport", "2026-01-15", "January bus fare"),
    (30.00, "Bills", "2026-02-10", "February electricity bill"),
    (15.00, "Health", "2026-02-20", "February pharmacy visit"),
    (25.00, "Shopping", "2026-03-05", "March new shoes"),
]
# All-time: total=100.00, count=5, top_category="Bills" (30 is the max single category)
# Feb-only (2026-02-01..2026-02-28): total=45.00, count=2, top_category="Bills" (30 > 15)


def _register_and_login(client, email="filteruser@example.com"):
    client.post(
        "/register",
        data={
            "name": "Filter User",
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


def _seed_fixed_expenses(user_id):
    db = get_db()
    db.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (user_id, amount, category, date_str, description)
            for amount, category, date_str, description in FIXED_EXPENSES
        ],
    )
    db.commit()
    db.close()


@pytest.fixture
def filter_client(client):
    """A logged-in client backed by a deterministic, fixed-date expense set."""
    user_id = _register_and_login(client)
    _seed_fixed_expenses(user_id)
    return client


# --- No filter params: identical to unfiltered / all-time behavior --------

def test_profile_no_filter_params_shows_alltime_data(filter_client):
    response = filter_client.get("/profile")
    assert response.status_code == 200
    body = response.get_data(as_text=True)

    assert "₹100.00" in body, "Expected all-time total spent across all fixed expenses"
    assert ">5<" in body, "Expected all-time transaction count of 5"
    assert "Bills" in body, "Expected top category 'Bills' to be shown"


# --- Valid date range narrows transactions, stats, and breakdown ----------

def test_profile_valid_date_range_filters_stats_and_transactions(filter_client):
    response = filter_client.get("/profile?start_date=2026-02-01&end_date=2026-02-28")
    assert response.status_code == 200
    body = response.get_data(as_text=True)

    assert "₹45.00" in body, "Expected total spent narrowed to the Feb-only subset"
    assert ">2<" in body, "Expected transaction count narrowed to 2 for the Feb-only subset"

    assert "February electricity bill" in body
    assert "February pharmacy visit" in body
    assert "January groceries" not in body, "Jan transaction must be excluded from a Feb-only filter"
    assert "January bus fare" not in body, "Jan transaction must be excluded from a Feb-only filter"
    assert "March new shoes" not in body, "March transaction must be excluded from a Feb-only filter"


def test_profile_valid_date_range_is_inclusive_of_boundary_dates(filter_client):
    # 2026-02-10 and 2026-02-20 are exact boundary dates of this range.
    response = filter_client.get("/profile?start_date=2026-02-10&end_date=2026-02-20")
    assert response.status_code == 200
    body = response.get_data(as_text=True)

    assert "February electricity bill" in body, "Start-date boundary expense should be included"
    assert "February pharmacy visit" in body, "End-date boundary expense should be included"
    assert "₹45.00" in body


# --- Zero matching transactions: empty state, not an error ----------------

def test_profile_date_range_with_no_matches_shows_empty_state(filter_client):
    response = filter_client.get("/profile?start_date=2026-04-01&end_date=2026-04-30")
    assert response.status_code == 200
    body = response.get_data(as_text=True)

    assert "₹0.00" in body, "Expected zero total spent for a range with no matching expenses"
    assert "no transactions found" in body.lower(), (
        "Expected an empty-state message when the filtered range has no matching transactions"
    )
    for description in (
        "January groceries",
        "January bus fare",
        "February electricity bill",
        "February pharmacy visit",
        "March new shoes",
    ):
        assert description not in body


# --- start_date after end_date: validation message + fallback -------------

def test_profile_start_after_end_falls_back_to_alltime_with_validation_message(filter_client):
    response = filter_client.get("/profile?start_date=2026-03-01&end_date=2026-01-01")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    body_lower = body.lower()

    assert "after" in body_lower and "end date" in body_lower, (
        "Expected a validation message explaining start_date is after end_date"
    )

    # Falls back to all-time data.
    assert "₹100.00" in body
    assert ">5<" in body
    assert "January groceries" in body
    assert "February electricity bill" in body
    assert "March new shoes" in body


# --- Malformed date strings: ignored gracefully, no crash -----------------

def test_profile_malformed_dates_ignored_shows_alltime_data(filter_client):
    response = filter_client.get("/profile?start_date=not-a-date&end_date=also-invalid")
    assert response.status_code == 200
    body = response.get_data(as_text=True)

    assert "₹100.00" in body, "Malformed dates should be ignored, falling back to all-time data"
    assert ">5<" in body
    assert "January groceries" in body
    assert "March new shoes" in body


@pytest.mark.parametrize(
    "bad_query",
    [
        "?start_date=2026/02/01&end_date=2026-02-28",
        "?start_date=02-01-2026&end_date=2026-02-28",
        "?start_date=&end_date=2026-02-28",
    ],
)
def test_profile_various_malformed_start_dates_do_not_crash(filter_client, bad_query):
    response = filter_client.get(f"/profile{bad_query}")
    assert response.status_code == 200, f"Malformed date query {bad_query!r} must not error"


# --- Auth guard: unauthenticated requests redirect to /login --------------

@pytest.mark.parametrize(
    "query_string",
    [
        "",
        "?start_date=2026-02-01&end_date=2026-02-28",
    ],
    ids=["no_filter_params", "with_filter_params"],
)
def test_profile_unauthenticated_redirects_to_login(client, query_string):
    response = client.get(f"/profile{query_string}")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# --- Category breakdown percentages sum to 100% for a filtered subset -----

def test_get_category_breakdown_filtered_subset_sums_to_100(filter_client):
    db = get_db()
    row = db.execute(
        "SELECT id FROM users WHERE email = ?", ("filteruser@example.com",)
    ).fetchone()
    db.close()
    user_id = row["id"]

    breakdown = get_category_breakdown(user_id, start_date="2026-02-01", end_date="2026-02-28")

    assert len(breakdown) == 2
    names = {item["name"] for item in breakdown}
    assert names == {"Bills", "Health"}
    assert sum(item["pct"] for item in breakdown) == 100, (
        "Category breakdown percentages must sum to 100 for a filtered subset"
    )


def test_profile_route_category_breakdown_percentages_sum_to_100(filter_client):
    response = filter_client.get("/profile?start_date=2026-02-01&end_date=2026-02-28")
    assert response.status_code == 200
    body = response.get_data(as_text=True)

    # Bills=30 of 45 -> 67%, Health=15 of 45 -> 33% (largest category absorbs the remainder).
    assert "67" in body
    assert "33" in body


# --- Filter form pre-fills the submitted date values -----------------------

def test_profile_form_prefills_submitted_filter_values(filter_client):
    response = filter_client.get("/profile?start_date=2026-02-01&end_date=2026-02-28")
    assert response.status_code == 200
    body = response.get_data(as_text=True)

    assert "2026-02-01" in body, "start_date should be pre-filled back into the form"
    assert "2026-02-28" in body, "end_date should be pre-filled back into the form"


def test_profile_form_has_no_prefilled_values_without_filter(filter_client):
    response = filter_client.get("/profile")
    assert response.status_code == 200
    body = response.get_data(as_text=True)

    # None of the fixed expense dates should leak into a raw YYYY-MM-DD form
    # value when no filter was submitted.
    for raw_date in ("2026-01-05", "2026-02-10", "2026-03-05"):
        assert raw_date not in body
