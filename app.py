import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from database import get_db, init_db
from matching import score_job, extract_skills_with_gemini

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key-before-deployment")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

@app.context_processor
def inject_user():
    return {"current_user": session.get("user")}

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def role_required(role):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("user"):
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            if session["user"]["role"] != role:
                flash("You don't have permission to access that page.", "danger")
                return redirect(url_for("index"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator

@app.route("/")
def index():
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT COUNT(*) AS n FROM jobs WHERE status='open'")
    open_jobs = cur.fetchone()["n"]
    cur.execute("SELECT COUNT(*) AS n FROM users WHERE role='employer' AND verified=1")
    verified_employers = cur.fetchone()["n"]
    cur.execute("SELECT COUNT(*) AS n FROM users WHERE role='worker'")
    workers = cur.fetchone()["n"]
    cur.execute("""SELECT j.*, u.name AS employer_name FROM jobs j
                   JOIN users u ON u.id=j.employer_id
                   WHERE j.status='open' ORDER BY j.created_at DESC LIMIT 6""")
    jobs = cur.fetchall()
    cur.close(); db.close()
    return render_template("index.html", open_jobs=open_jobs,
                           verified_employers=verified_employers, workers=workers, jobs=jobs)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip().lower() or None
        password = request.form.get("password", "")
        role = request.form.get("role", "worker")
        language = request.form.get("language", "English")
        city = request.form.get("city", "").strip()
        skills = request.form.get("skills", "").strip()
        experience = request.form.get("experience", "").strip()
        if not name or not phone or len(password) < 8 or role not in ("worker", "employer"):
            flash("Enter your name and phone number, choose an account type, and use a password of at least 8 characters.", "danger")
            return render_template("register.html")
        db = get_db(); cur = db.cursor()
        try:
            cur.execute("""INSERT INTO users
                (name, phone, email, password_hash, role, language, city, skills, experience)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (name, phone, email, generate_password_hash(password), role, language, city, skills, experience))
            db.commit()
            flash("Account created. You can now log in.", "success")
            return redirect(url_for("login"))
        except Exception:
            db.rollback()
            flash("That phone number or email may already be registered.", "danger")
        finally:
            cur.close(); db.close()
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")
        db = get_db(); cur = db.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE phone=%s OR email=%s LIMIT 1", (identifier, identifier.lower()))
        user = cur.fetchone()
        cur.close(); db.close()
        if user and check_password_hash(user["password_hash"], password):
            session["user"] = {"id": user["id"], "name": user["name"], "role": user["role"]}
            flash(f"Welcome, {user['name']}!", "success")
            return redirect(url_for("index"))
        flash("Incorrect login details.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

@app.route("/jobs")
def jobs():
    keyword = request.args.get("q", "").strip()
    city = request.args.get("city", "").strip()
    db = get_db(); cur = db.cursor(dictionary=True)
    sql = """SELECT j.*, u.name AS employer_name, u.verified AS employer_verified
             FROM jobs j JOIN users u ON u.id=j.employer_id WHERE j.status='open'"""
    params = []
    if keyword:
        sql += " AND (j.title LIKE %s OR j.description LIKE %s OR j.skills LIKE %s)"
        like = f"%{keyword}%"; params += [like, like, like]
    if city:
        sql += " AND j.city LIKE %s"; params.append(f"%{city}%")
    sql += " ORDER BY j.created_at DESC"
    cur.execute(sql, tuple(params)); job_list = cur.fetchall()
    cur.close(); db.close()
    return render_template("jobs.html", jobs=job_list, q=keyword, city=city)

@app.route("/jobs/<int:job_id>")
def job_detail(job_id):
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("""SELECT j.*, u.name AS employer_name, u.phone AS employer_phone,
                   u.verified AS employer_verified FROM jobs j
                   JOIN users u ON u.id=j.employer_id WHERE j.id=%s""", (job_id,))
    job = cur.fetchone()
    applied = False
    if job and session.get("user"):
        cur.execute("SELECT id FROM applications WHERE job_id=%s AND worker_id=%s",
                    (job_id, session["user"]["id"]))
        applied = cur.fetchone() is not None
    cur.close(); db.close()
    if not job:
        flash("Job not found.", "danger")
        return redirect(url_for("jobs"))
    return render_template("job_detail.html", job=job, applied=applied)

@app.route("/jobs/<int:job_id>/apply", methods=["POST"])
@login_required
@role_required("worker")
def apply_job(job_id):
    db = get_db(); cur = db.cursor()
    try:
        cur.execute("INSERT INTO applications (job_id, worker_id, message) VALUES (%s,%s,%s)",
                    (job_id, session["user"]["id"], request.form.get("message", "").strip()))
        db.commit()
        flash("Application submitted successfully.", "success")
    except Exception:
        db.rollback()
        flash("You may have already applied, or this job is no longer available.", "warning")
    finally:
        cur.close(); db.close()
    return redirect(url_for("job_detail", job_id=job_id))

@app.route("/post-job", methods=["GET", "POST"])
@login_required
@role_required("employer")
def post_job():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        city = request.form.get("city", "").strip()
        wage = request.form.get("wage", "").strip()
        wage_period = request.form.get("wage_period", "day")
        hours = request.form.get("hours", "").strip()
        skills = request.form.get("skills", "").strip()
        contact = request.form.get("contact", "").strip()
        if not all([title, description, city, wage, hours]):
            flash("Please complete all required fields.", "danger")
            return render_template("post_job.html")
        try:
            wage_value = float(wage)
            if wage_value <= 0: raise ValueError()
        except ValueError:
            flash("Enter a valid wage amount.", "danger")
            return render_template("post_job.html")
        db = get_db(); cur = db.cursor()
        cur.execute("""INSERT INTO jobs
            (employer_id,title,description,city,wage,wage_period,hours,skills,contact)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (session["user"]["id"],title,description,city,wage_value,wage_period,hours,skills,contact))
        db.commit(); cur.close(); db.close()
        flash("Your job listing is now live.", "success")
        return redirect(url_for("jobs"))
    return render_template("post_job.html")

@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db(); cur = db.cursor(dictionary=True)
    user_id = session["user"]["id"]
    if session["user"]["role"] == "employer":
        cur.execute("""SELECT j.*, (SELECT COUNT(*) FROM applications a WHERE a.job_id=j.id) AS applicants
                       FROM jobs j WHERE j.employer_id=%s ORDER BY j.created_at DESC""", (user_id,))
        listings = cur.fetchall()
        cur.execute("""SELECT a.*, j.title, u.name AS worker_name, u.phone AS worker_phone
                       FROM applications a JOIN jobs j ON j.id=a.job_id
                       JOIN users u ON u.id=a.worker_id WHERE j.employer_id=%s
                       ORDER BY a.created_at DESC""", (user_id,))
        applications = cur.fetchall()
    else:
        cur.execute("""SELECT a.*, j.title, j.city, j.wage, j.wage_period, j.status
                       FROM applications a JOIN jobs j ON j.id=a.job_id
                       WHERE a.worker_id=%s ORDER BY a.created_at DESC""", (user_id,))
        applications = cur.fetchall(); listings = []
    cur.close(); db.close()
    return render_template("dashboard.html", listings=listings, applications=applications)

@app.route("/api/match", methods=["POST"])
def api_match():
    data = request.get_json(silent=True) or {}
    skills = data.get("skills", "").strip()
    city = data.get("city", "").strip()
    if not skills:
        return jsonify({"error": "Please enter your skills."}), 400
    db = get_db(); cur = db.cursor(dictionary=True)
    sql = """SELECT j.*, u.name AS employer_name, u.verified AS employer_verified
             FROM jobs j JOIN users u ON u.id=j.employer_id WHERE j.status='open'"""
    params = []
    if city:
        sql += " AND j.city LIKE %s"; params.append(f"%{city}%")
    cur.execute(sql, tuple(params)); rows = cur.fetchall()
    cur.close(); db.close()
    for row in rows:
        row["match_score"] = score_job(skills, row.get("skills","") + " " + row["title"] + " " + row["description"])
    rows.sort(key=lambda x: x["match_score"], reverse=True)
    return jsonify({"matches": rows[:10]})

@app.route("/api/extract-skills", methods=["POST"])
def api_extract_skills():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "Please provide a voice transcript or text."}), 400
    result = extract_skills_with_gemini(text)
    return jsonify({"skills": result, "mode": "gemini" if os.getenv("GEMINI_API_KEY") else "basic"})

@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=os.getenv("FLASK_DEBUG") == "1")
