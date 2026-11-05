from datetime import timedelta
from functools import wraps
import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "learning.db"))
# Ensure the parent directory exists (useful when a host mounts persistent storage).
os.makedirs(os.path.dirname(os.path.abspath(DATABASE)), exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-before-deployment")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
)

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DATABASE)
    # Return rows that support both numeric and column-name access (row[0], row["id"]).
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('teacher','student')),
        display_name TEXT NOT NULL,
        class_name TEXT DEFAULT '一年甲班'
    );
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        student_id INTEGER NOT NULL,
        score REAL NOT NULL,
        completed INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY(student_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS quizzes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        question_count INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS quiz_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        correct_count INTEGER NOT NULL,
        FOREIGN KEY(quiz_id) REFERENCES quizzes(id),
        FOREIGN KEY(student_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS quiz_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id INTEGER NOT NULL,
        question_no INTEGER NOT NULL,
        correct_count INTEGER NOT NULL,
        total_count INTEGER NOT NULL,
        FOREIGN KEY(quiz_id) REFERENCES quizzes(id)
    );
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rating INTEGER NOT NULL,
        difficult TEXT,
        suggestion TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count == 0:
        users = [
            ("teacher", generate_password_hash("teacher123"), "teacher", "王老師", "一年甲班"),
            ("student01", generate_password_hash("student123"), "student", "陳小明", "一年甲班"),
            ("student02", generate_password_hash("student123"), "student", "林小華", "一年甲班"),
            ("student03", generate_password_hash("student123"), "student", "張小美", "一年甲班"),
        ]
        db.executemany(
            "INSERT INTO users(username,password_hash,role,display_name,class_name) VALUES(?,?,?,?,?)",
            users
        )
        students = db.execute("SELECT id FROM users WHERE role='student'").fetchall()
        assignment_rows = []
        for idx, student in enumerate(students):
            assignment_rows.append(("第一單元學習單", student["id"], [90, 82, 95][idx], 1))
            assignment_rows.append(("第二單元學習單", student["id"], [85, 88, 91][idx], 1))
        db.executemany("INSERT INTO assignments(title,student_id,score,completed) VALUES(?,?,?,?)", assignment_rows)
        cur = db.execute("INSERT INTO quizzes(title,question_count) VALUES(?,?)", ("第一單元測驗", 5))
        quiz_id = cur.lastrowid
        for idx, student in enumerate(students):
            db.execute("INSERT INTO quiz_results(quiz_id,student_id,correct_count) VALUES(?,?,?)",
                       (quiz_id, student["id"], [4, 3, 5][idx]))
        for qno, correct in enumerate([3, 2, 3, 2, 2], start=1):
            db.execute("INSERT INTO quiz_questions(quiz_id,question_no,correct_count,total_count) VALUES(?,?,?,?)",
                       (quiz_id, qno, correct, 3))
        # Clearly fictional sample feedback so the teacher dashboard is demonstrable immediately.
        db.executemany(
            "INSERT INTO feedback(rating,difficult,suggestion) VALUES(?,?,?)",
            [
                (5, "第二單元的概念比較多，需要多一點例子。", "希望增加課堂練習。"),
                (4, "測驗題目需要仔細閱讀。", "可以提供考前重點整理。"),
                (5, "整體課程容易理解。", "希望維持目前的教學方式。"),
            ]
        )
        db.commit()
    db.close()

def login_required(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("您沒有權限進入此頁面。", "error")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)
        return wrapped
    return decorator

@app.route("/", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        chosen_role = request.form.get("role", "")
        user = get_db().execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password) and user["role"] == chosen_role:
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["display_name"] = user["display_name"]
            session.permanent = request.form.get("remember") == "on"
            flash("登入成功，歡迎使用學習成果分析網！", "success")
            return redirect(url_for("dashboard"))
        flash("帳號、密碼或登入身分不正確。", "error")
    return render_template("login.html")

@app.route("/dashboard")
@login_required()
def dashboard():
    if session["role"] == "teacher":
        return redirect(url_for("teacher_dashboard"))
    return redirect(url_for("student_dashboard"))

@app.route("/teacher")
@login_required("teacher")
def teacher_dashboard():
    db = get_db()
    students = db.execute("SELECT id,display_name,class_name FROM users WHERE role='student' ORDER BY id").fetchall()
    assignments = db.execute("""
        SELECT a.title, u.display_name, a.score, a.completed
        FROM assignments a JOIN users u ON a.student_id=u.id ORDER BY a.id DESC
    """).fetchall()
    quizzes = db.execute("""
        SELECT q.id,q.title,q.question_count,ROUND(100.0*AVG(r.correct_count)/q.question_count,1) AS avg_rate
        FROM quizzes q LEFT JOIN quiz_results r ON q.id=r.quiz_id GROUP BY q.id ORDER BY q.id DESC
    """).fetchall()
    question_stats = db.execute("""
        SELECT q.title,qq.question_no,qq.correct_count,qq.total_count,
        ROUND(100.0*qq.correct_count/qq.total_count,1) AS rate
        FROM quiz_questions qq JOIN quizzes q ON qq.quiz_id=q.id ORDER BY q.id DESC,qq.question_no
    """).fetchall()
    feedback = db.execute("SELECT rating,difficult,suggestion FROM feedback ORDER BY id DESC").fetchall()
    avg_rating = db.execute("SELECT ROUND(AVG(rating),1) FROM feedback").fetchone()[0]
    return render_template("teacher.html", students=students, assignments=assignments,
                           quizzes=quizzes, question_stats=question_stats,
                           feedback=feedback, avg_rating=avg_rating)

@app.route("/student")
@login_required("student")
def student_dashboard():
    db = get_db()
    uid = session["user_id"]
    assignments = db.execute("SELECT title,score,completed FROM assignments WHERE student_id=? ORDER BY id DESC",(uid,)).fetchall()
    results = db.execute("""
        SELECT q.title,q.question_count,r.correct_count,
        ROUND(100.0*r.correct_count/q.question_count,1) AS rate
        FROM quiz_results r JOIN quizzes q ON r.quiz_id=q.id WHERE r.student_id=? ORDER BY q.id DESC
    """,(uid,)).fetchall()
    class_stats = db.execute("""
        SELECT q.title,ROUND(100.0*AVG(r.correct_count)/q.question_count,1) AS avg_rate
        FROM quizzes q JOIN quiz_results r ON q.id=r.quiz_id GROUP BY q.id
    """).fetchall()
    question_stats = db.execute("""
        SELECT q.title,qq.question_no,ROUND(100.0*qq.correct_count/qq.total_count,1) AS rate
        FROM quiz_questions qq JOIN quizzes q ON qq.quiz_id=q.id ORDER BY q.id DESC,qq.question_no
    """).fetchall()
    return render_template("student.html", assignments=assignments, results=results,
                           class_stats=class_stats, question_stats=question_stats)

@app.route("/feedback", methods=["GET", "POST"])
@login_required("student")
def submit_feedback():
    if request.method == "POST":
        try:
            rating = int(request.form.get("rating", ""))
        except ValueError:
            rating = 0
        if rating < 1 or rating > 5:
            flash("請選擇 1 至 5 分的課程滿意度。", "error")
        else:
            # Deliberately store no user_id, username, or other student identifier.
            get_db().execute(
                "INSERT INTO feedback(rating,difficult,suggestion) VALUES(?,?,?)",
                (rating, request.form.get("difficult","").strip(), request.form.get("suggestion","").strip())
            )
            get_db().commit()
            flash("匿名問卷已送出，謝謝您的回饋！", "success")
            return redirect(url_for("student_dashboard"))
    return render_template("feedback.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("您已成功登出。", "success")
    return redirect(url_for("login"))

# Initialize demo schema/data when the WSGI server imports this module.
init_db()

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
