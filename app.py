import os
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

from database.db import get_db, init_db, seed_db
from database.queries import get_user_by_id, get_recent_transactions, get_summary_stats, get_category_breakdown

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

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

    def _valid_date(s):
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return True
        except (ValueError, TypeError):
            return False

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


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
