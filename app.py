import os

from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

from database.db import get_db, init_db, seed_db

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

    user = {"name": "Demo User", "email": "demo@spendly.com", "member_since": "September 2026", "initials": "DU"}
    stats = {"total_spent": 280.74, "transaction_count": 8, "top_category": "Bills"}
    transactions = [
        {"date": "Sep 20, 2026", "description": "Dinner out", "category": "Food", "amount": 22.30},
        {"date": "Sep 17, 2026", "description": "Miscellaneous", "category": "Other", "amount": 10.00},
        {"date": "Sep 14, 2026", "description": "New shoes", "category": "Shopping", "amount": 60.20},
        {"date": "Sep 11, 2026", "description": "Movie tickets", "category": "Entertainment", "amount": 15.75},
        {"date": "Sep 08, 2026", "description": "Pharmacy", "category": "Health", "amount": 25.00},
        {"date": "Sep 05, 2026", "description": "Electricity bill", "category": "Bills", "amount": 89.99},
        {"date": "Sep 03, 2026", "description": "Bus fare", "category": "Transport", "amount": 12.00},
        {"date": "Sep 02, 2026", "description": "Groceries", "category": "Food", "amount": 45.50},
    ]
    breakdown = [
        {"category": "Bills", "amount": 89.99, "percent": 30},
        {"category": "Food", "amount": 67.80, "percent": 25},
        {"category": "Shopping", "amount": 60.20, "percent": 20},
        {"category": "Health", "amount": 25.00, "percent": 10},
        {"category": "Entertainment", "amount": 15.75, "percent": 5},
        {"category": "Transport", "amount": 12.00, "percent": 5},
        {"category": "Other", "amount": 10.00, "percent": 5},
    ]
    return render_template(
        "profile.html", user=user, stats=stats, transactions=transactions, breakdown=breakdown
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
