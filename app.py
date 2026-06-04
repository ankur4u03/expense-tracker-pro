from flask import Flask, render_template, request, redirect, send_file,session
import sqlite3
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "ankur_secret_key"
# ==========================
# DATABASE
# ==========================

def init_db():

    conn = sqlite3.connect("expense.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        amount REAL,
        type TEXT,
        category TEXT,
        date TEXT,
        month TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()


# ==========================
# HOME
# ==========================

@app.route("/")
def home():

    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("expense.db")
    cur = conn.cursor()

    search = request.args.get("search", "")

    # Transactions Search

    if search:

        cur.execute("""
        SELECT * FROM transactions
        WHERE user_id = ?
        AND (title LIKE ?
        OR category LIKE ?
        )
        ORDER BY id DESC
        """,
       (
            session["user_id"],
            f"%{search}%",
            f"%{search}%"
        ))

    else:

        cur.execute("""
        SELECT * FROM transactions
        WHERE user_id=?
        ORDER BY id DESC
    """,
    (session["user_id"],)
    )

    transactions = cur.fetchall()
    

    # Income

    cur.execute(
    "SELECT SUM(amount) FROM transactions WHERE type='Income' AND user_id=?",
    (session["user_id"],)
)

    income = cur.fetchone()[0] or 0

    # Expense

    cur.execute(
    "SELECT SUM(amount) FROM transactions WHERE type='Expense' AND user_id=?",
    (session["user_id"],)
)

    expense = cur.fetchone()[0] or 0

    # Analytics

    if search:

      cur.execute("""
      SELECT category, SUM(amount)
      FROM transactions
      WHERE type='Expense'
      AND user_id=?
      AND (
        title LIKE ?
        OR category LIKE ?
        )
        GROUP BY category
        """,
        (
        session["user_id"],
        f"%{search}%",
        f"%{search}%"
        ))

    else:

      cur.execute("""
      SELECT category, SUM(amount)
      FROM transactions
      WHERE type='Expense'
      AND user_id=?
      GROUP BY category
      """,
      (session["user_id"],)
      )

    category_data = cur.fetchall()

    # Monthly Report

    if search:

       cur.execute("""
       SELECT month, SUM(amount)
       FROM transactions
       WHERE type='Expense'
       AND user_id=?
       AND (
        title LIKE ?
        OR category LIKE ?
        )
        GROUP BY month
        """,
        (
        session["user_id"],
        f"%{search}%",
        f"%{search}%"
        ))

    else:

        cur.execute("""
        SELECT month, SUM(amount)
        FROM transactions
        WHERE type='Expense'
        AND user_id=?
        GROUP BY month
        """,
        (session["user_id"],)
        )

    monthly_report = cur.fetchall()

    conn.close()

    balance = income - expense

    return render_template(
        "index.html",
        transactions=transactions,
        income=income,
        expense=expense,
        balance=balance,
        category_data=category_data,
        monthly_report=monthly_report,
        search=search,
        username=session.get("username")
    )
    
# ==========================
# ADD TRANSACTION
# ==========================

@app.route("/add", methods=["POST"])
def add():

    title = request.form["title"]
    amount = float(request.form["amount"])
    ttype = request.form["type"]
    category = request.form["category"]

    date = datetime.now().strftime("%d-%m-%Y")
    month = datetime.now().strftime("%B %Y")

    conn = sqlite3.connect("expense.db")
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO transactions
    (user_id, title, amount, type, category, date, month)
    VALUES (?, ?, ?, ?, ?, ?,?)
    """,
    (
        session["user_id"],
        title,
        amount,
        ttype,
        category,
        date,
        month
    ))

    conn.commit()
    conn.close()

    return redirect("/")


# ==========================
# DELETE
# ==========================

@app.route("/delete/<int:id>")
def delete(id):

    conn = sqlite3.connect("expense.db")
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM transactions WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):

    conn = sqlite3.connect("expense.db")
    cur = conn.cursor()

    if request.method == "POST":

        title = request.form["title"]
        amount = request.form["amount"]
        ttype = request.form["type"]
        category = request.form["category"]

        cur.execute("""
        UPDATE transactions
        SET title=?, amount=?, type=?, category=?
        WHERE id=?
        """, (title, amount, ttype, category, id))

        conn.commit()
        conn.close()

        return redirect("/")

    cur.execute(
        "SELECT * FROM transactions WHERE id=?",
        (id,)
    )

    transaction = cur.fetchone()

    conn.close()

    return render_template(
        "edit.html",
        transaction=transaction
    )

# ==========================
# EXPORT EXCEL
# ==========================

@app.route("/export")
def export():

    conn = sqlite3.connect("expense.db")

    df = pd.read_sql_query(
        """
        SELECT * FROM transactions
        WHERE user_id=?
        """,
        conn,
        params=(session["user_id"],)
    )

    conn.close()

    file_name = "Expense_Report.xlsx"

    df.to_excel(
        file_name,
        index=False
    )

    return send_file(
        file_name,
        as_attachment=True
    )
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        password = generate_password_hash(
            request.form["password"]
        )

        conn = sqlite3.connect("expense.db")
        cur = conn.cursor()

        try:

            cur.execute(
                """
                INSERT INTO users(name,email,password)
                VALUES(?,?,?)
                """,
                (username, email, password)
            )

            conn.commit()

        except:
            conn.close()
            return "Email already exists"

        conn.close()

        return redirect("/login")

    return render_template("register.html")

# ==========================
# LOGIN
# ==========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("expense.db")
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        )

        user = cur.fetchone()

        conn.close()

        if user and check_password_hash(
            user[3],
            password
        ):

            session["user_id"] = user[0]
            session["username"] = user[1]

            return redirect("/")

        return "Invalid Email or Password"

    return render_template("login.html")

@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("expense.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name,email FROM users WHERE id=?",
        (session["user_id"],)
    )

    user = cursor.fetchone()
    conn.close()

    if not user:
        return redirect("/login")

    return render_template(
        "profile.html",
        username=user[0],
        email=user[1]
    )
@app.route("/edit-profile")
def edit_profile():
    return "Edit Profile Page Coming Soon"


@app.route("/change-password")
def change_password():
    return "Change Password Page Coming Soon"
# ==========================
# LOGOUT
# ==========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# ==========================
# RUN
# ==========================

if __name__ == "__main__":
    app.run(debug=True)