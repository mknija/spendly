import math
import os
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

from database.db import get_db, init_db, seed_db, CATEGORIES
from database.queries import (
    get_user_by_id,
    get_recent_transactions,
    get_summary_stats,
    get_category_breakdown,
    insert_expense,
    get_expense_by_id,
    update_expense,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

def _valid_date(s):
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password or not confirm_password:
            return render_template("register.html", error="All fields are required.")

        if len(password) < 8:
            return render_template("register.html", error="Password must be at least 8 characters.")

        if password != confirm_password:
            return render_template("register.html", error="Passwords do not match.")

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            db.close()
            return render_template("register.html", error="An account with this email already exists.")

        password_hash = generate_password_hash(password)
        cursor = db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        db.commit()
        user_id = cursor.lastrowid
        db.close()

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template("login.html", error="Invalid email or password.")

        db = get_db()
        user = db.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,)).fetchone()
        db.close()

        if not user or not check_password_hash(user["password_hash"], password):
            return render_template("login.html", error="Invalid email or password.")

        session["user_id"] = user["id"]
        return redirect(url_for("profile"))

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    user_data = get_user_by_id(user_id)
    if user_data is None:
        session.clear()
        return redirect(url_for("login"))

    name_parts = user_data["name"].split()
    if len(name_parts) > 1:
        initials = (name_parts[0][0] + name_parts[-1][0]).upper()
    else:
        initials = user_data["name"][:2].upper()
    user = {**user_data, "initials": initials}

    start_raw = request.args.get("start_date", "")
    end_raw = request.args.get("end_date", "")

    start_date = start_raw if _valid_date(start_raw) else None
    end_date = end_raw if _valid_date(end_raw) else None

    filter_error = None
    if start_date and end_date and start_date > end_date:
        filter_error = "Start date is after end date — showing all-time data instead."
        start_date, end_date = None, None

    # --- SUBAGENT 1: TRANSACTION HISTORY --------------------------------
    transactions = get_recent_transactions(user_id, start_date=start_date, end_date=end_date)
    # ----------------------------------------------------------------------

    # --- SUBAGENT 2: SUMMARY STATS ----------------------------------------
    stats = get_summary_stats(user_id, start_date=start_date, end_date=end_date)
    # ----------------------------------------------------------------------

    # --- SUBAGENT 3: CATEGORY BREAKDOWN ------------------------------------
    raw_breakdown = get_category_breakdown(user_id, start_date=start_date, end_date=end_date)
    breakdown = [{"category": item["name"], "amount": item["amount"], "percent": item["pct"]} for item in raw_breakdown]
    # ------------------------------------------------------------------------

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        breakdown=breakdown,
        filter_error=filter_error,
        start_raw=start_raw,
        end_raw=end_raw,
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]

    if request.method == "POST":
        amount_raw = request.form.get("amount", "")
        category = request.form.get("category", "")
        date_raw = request.form.get("date", "")
        description_raw = request.form.get("description", "").strip()

        def _rerender(error):
            return render_template(
                "add_expense.html",
                error=error,
                categories=CATEGORIES,
                amount=amount_raw,
                category=category,
                date=date_raw,
                description=description_raw,
            )

        try:
            amount = float(amount_raw)
            valid_amount = math.isfinite(amount) and amount > 0
        except (ValueError, TypeError):
            valid_amount = False

        if not valid_amount:
            return _rerender("Amount must be a number greater than 0.")

        if category not in CATEGORIES:
            return _rerender("Please select a valid category.")

        if not _valid_date(date_raw):
            return _rerender("Please enter a valid date.")

        description = description_raw if description_raw else None

        insert_expense(user_id, amount, category, date_raw, description)
        return redirect(url_for("profile"))

    today_str = datetime.today().strftime("%Y-%m-%d")
    return render_template("add_expense.html", categories=CATEGORIES, date=today_str)


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    expense = get_expense_by_id(user_id, id)
    if expense is None:
        return redirect(url_for("profile"))

    if request.method == "POST":
        amount_raw = request.form.get("amount", "")
        category = request.form.get("category", "")
        date_raw = request.form.get("date", "")
        description_raw = request.form.get("description", "").strip()

        def _rerender(error):
            return render_template(
                "edit_expense.html",
                error=error,
                categories=CATEGORIES,
                expense_id=id,
                amount=amount_raw,
                category=category,
                date=date_raw,
                description=description_raw,
            )

        try:
            amount = float(amount_raw)
            valid_amount = math.isfinite(amount) and amount > 0
        except (ValueError, TypeError):
            valid_amount = False

        if not valid_amount:
            return _rerender("Amount must be a number greater than 0.")

        if category not in CATEGORIES:
            return _rerender("Please select a valid category.")

        if not _valid_date(date_raw):
            return _rerender("Please enter a valid date.")

        description = description_raw if description_raw else None

        update_expense(user_id, id, amount, category, date_raw, description)
        return redirect(url_for("profile"))

    return render_template(
        "edit_expense.html",
        categories=CATEGORIES,
        expense_id=id,
        amount=expense["amount"],
        category=expense["category"],
        date=expense["date"],
        description=expense["description"] or "",
    )


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
