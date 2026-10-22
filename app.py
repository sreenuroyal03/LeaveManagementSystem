from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session
)

import os
import sqlite3
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

from database import create_tables, get_connection

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "dev-only-change-this-before-deployment"
)

create_tables()


def login_required(role=None):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):

            if "employee_id" not in session:
                return redirect(url_for("login"))

            if role and session.get("role") != role:
                return "Access denied", 403

            return function(*args, **kwargs)

        return wrapper
    return decorator


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not name or not email or len(password) < 8:
            return render_template(
                "register.html",
                error="Enter valid details and a password of at least 8 characters."
            )

        connection = get_connection()

        try:
            connection.execute(
                """
                INSERT INTO employees (name, email, password, role)
                VALUES (?, ?, ?, ?)
                """,
                (
                    name,
                    email,
                    generate_password_hash(password),
                    "employee"
                )
            )

            connection.commit()

        except sqlite3.IntegrityError:
            return render_template(
                "register.html",
                error="This email is already registered."
            )

        finally:
            connection.close()

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        email = request.form["email"].strip().lower()
        password = request.form["password"]

        connection = get_connection()

        employee = connection.execute(
            "SELECT * FROM employees WHERE email = ?",
            (email,)
        ).fetchone()

        connection.close()

        if employee and check_password_hash(
            employee["password"],
            password
        ):

            session.clear()
            session["employee_id"] = employee["id"]
            session["name"] = employee["name"]
            session["role"] = employee["role"]

            if employee["role"] == "admin":
                return redirect(url_for("admin_dashboard"))

            return redirect(url_for("employee_dashboard"))

        error = "Invalid email or password."

    return render_template("login.html", error=error)


@app.route("/employee")
@login_required(role="employee")
def employee_dashboard():

    connection = get_connection()

    leaves = connection.execute(
        """
        SELECT *
        FROM leave_requests
        WHERE employee_id = ?
        ORDER BY id DESC
        """,
        (session["employee_id"],)
    ).fetchall()

    connection.close()

    return render_template(
        "employee_dashboard.html",
        leaves=leaves,
        name=session["name"]
    )


@app.route("/apply-leave", methods=["POST"])
@login_required(role="employee")
def apply_leave():

    leave_type = request.form["leave_type"]
    start_date = request.form["start_date"]
    end_date = request.form["end_date"]
    reason = request.form["reason"].strip()

    allowed_types = ["Casual", "Sick", "Earned"]

    if (
        leave_type not in allowed_types
        or not start_date
        or not end_date
        or end_date < start_date
        or not reason
    ):
        return "Invalid leave details", 400

    connection = get_connection()

    connection.execute(
        """
        INSERT INTO leave_requests
        (employee_id, leave_type, start_date, end_date, reason)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            session["employee_id"],
            leave_type,
            start_date,
            end_date,
            reason
        )
    )

    connection.commit()
    connection.close()

    return redirect(url_for("employee_dashboard"))


@app.route("/admin")
@login_required(role="admin")
def admin_dashboard():

    connection = get_connection()

    leaves = connection.execute(
        """
        SELECT
            leave_requests.*,
            employees.name,
            employees.email
        FROM leave_requests
        JOIN employees
            ON leave_requests.employee_id = employees.id
        ORDER BY leave_requests.id DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "admin_dashboard.html",
        leaves=leaves
    )


@app.route("/update-leave/<int:leave_id>", methods=["POST"])
@login_required(role="admin")
def update_leave(leave_id):

    status = request.form["status"]

    if status not in ["Approved", "Rejected"]:
        return "Invalid status", 400

    connection = get_connection()

    connection.execute(
        """
        UPDATE leave_requests
        SET status = ?
        WHERE id = ?
        """,
        (status, leave_id)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)