"""InternHub - Internship Management System (Flask + Oracle 10g XE)."""
import os
import re
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, url_for

load_dotenv()
import db  # noqa: E402  (must come after load_dotenv)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-me-in-env-file")
app.teardown_appcontext(db.close_conn)

STATUSES = ("PENDING", "ACCEPTED", "REJECTED")
MODES = ("Onsite", "Remote", "Hybrid")
CATEGORY_ICONS = {
    "Software": "bi-code-slash",
    "Data Science": "bi-bar-chart-line",
    "Design": "bi-palette",
    "Engineering": "bi-gear-wide-connected",
    "Finance": "bi-graph-up-arrow",
    "Marketing": "bi-megaphone",
    "Research": "bi-journal-text",
    "Other": "bi-briefcase",
}
DEPARTMENTS = [
    "Computer Science", "Information Technology", "Electronics", "Electrical",
    "Mechanical", "Civil", "Commerce", "Business Administration", "Mathematics",
    "Statistics", "Design", "Other",
]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[0-9][0-9\s\-]{7,16}[0-9]$")

BASE_INTERNSHIP_SELECT = """
    SELECT i.internship_id, i.role_title, i.category, i.description, i.location,
           i.work_mode, i.duration_weeks, i.stipend, i.eligibility, i.openings,
           i.deadline, c.company_id, c.company_name, c.industry,
           (SELECT COUNT(*) FROM applications a
             WHERE a.internship_id = i.internship_id) AS applicants,
           CASE WHEN i.deadline IS NULL OR i.deadline >= TRUNC(SYSDATE)
                THEN 1 ELSE 0 END AS is_open
      FROM internships i
      JOIN companies c ON c.company_id = i.company_id
"""


# ---------------------------------------------------------------- helpers
@app.template_filter("fmt_date")
def fmt_date(value):
    return value.strftime("%d %b %Y") if value else "—"


@app.template_filter("initials")
def initials(name):
    parts = (name or "?").split()
    return "".join(p[0] for p in parts[:2]).upper()


@app.context_processor
def inject_globals():
    return {"STATUSES": STATUSES, "CATEGORY_ICONS": CATEGORY_ICONS,
            "current_year": datetime.now().year}


def category_icon(name):
    return CATEGORY_ICONS.get(name, CATEGORY_ICONS["Other"])


app.jinja_env.globals["category_icon"] = category_icon


def clean_student(form):
    data = {
        "full_name": form.get("full_name", "").strip(),
        "email": form.get("email", "").strip().lower(),
        "phone": form.get("phone", "").strip(),
        "department": form.get("department", "").strip(),
        "skills": form.get("skills", "").strip(),
    }
    errors = []
    if len(data["full_name"]) < 2:
        errors.append("Please enter the student's full name.")
    if not EMAIL_RE.match(data["email"]):
        errors.append("Please enter a valid email address.")
    if not PHONE_RE.match(data["phone"]):
        errors.append("Phone number should have 9-18 digits (spaces, dashes and a leading + are allowed).")
    if not data["department"]:
        errors.append("Please choose a department.")
    if len(data["skills"]) > 500:
        errors.append("Skills must be 500 characters or fewer.")
    return data, errors


def get_companies():
    return db.query("SELECT company_id, company_name FROM companies ORDER BY company_name")


def get_categories():
    return db.query(
        "SELECT category, COUNT(*) AS cnt FROM internships GROUP BY category ORDER BY cnt DESC, category")


# ------------------------------------------------------------- error pages
@app.errorhandler(db.DBConnectionError)
def handle_connection_error(exc):
    return render_template("error.html", title="Cannot reach the database",
                           message=str(exc), show_health=True), 503


@app.errorhandler(db.DatabaseError)
def handle_db_error(exc):
    app.logger.exception("Oracle error")
    hint = ""
    code = db.ora_code(exc)
    if code == 942:
        hint = " A table is missing - run `python setup_db.py` (see README)."
    elif code == 904:
        hint = " A column name does not match - your existing table may differ; run `python inspect_db.py`."
    return render_template("error.html", title="Database error",
                           message=str(exc).strip() + hint, show_health=True), 500


@app.errorhandler(404)
def handle_404(_exc):
    return render_template("error.html", title="Page not found",
                           message="We couldn't find that page.", show_health=False), 404


# ------------------------------------------------------------------- home
@app.route("/")
def index():
    stats = db.query_one("""
        SELECT (SELECT COUNT(*) FROM students)    AS students,
               (SELECT COUNT(*) FROM companies)   AS companies,
               (SELECT COUNT(*) FROM internships
                 WHERE deadline IS NULL OR deadline >= TRUNC(SYSDATE)) AS open_internships,
               (SELECT COUNT(*) FROM applications) AS applications
          FROM dual""")
    featured = db.query(
        "SELECT * FROM (" + BASE_INTERNSHIP_SELECT +
        " ORDER BY i.created_at DESC, i.internship_id DESC) WHERE ROWNUM <= 6")
    return render_template("index.html", stats=stats, featured=featured,
                           categories=get_categories())


# ------------------------------------------------------------ internships
@app.route("/internships")
def internships():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    mode = request.args.get("mode", "").strip()
    only_open = request.args.get("open") == "1"

    where, params = [], {}
    if q:
        where.append("(UPPER(i.role_title) LIKE :q OR UPPER(c.company_name) LIKE :q "
                     "OR UPPER(i.location) LIKE :q OR UPPER(i.category) LIKE :q "
                     "OR UPPER(i.description) LIKE :q OR UPPER(i.eligibility) LIKE :q)")
        params["q"] = "%" + q.upper() + "%"
    if category:
        where.append("i.category = :category")
        params["category"] = category
    if mode in MODES:
        where.append("i.work_mode = :mode")
        params["mode"] = mode
    if only_open:
        where.append("(i.deadline IS NULL OR i.deadline >= TRUNC(SYSDATE))")

    sql = BASE_INTERNSHIP_SELECT
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY i.created_at DESC, i.internship_id DESC"
    rows = db.query(sql, params)
    return render_template("internships.html", internships=rows, categories=get_categories(),
                           q=q, category=category, mode=mode, only_open=only_open, modes=MODES)


@app.route("/internships/<int:internship_id>")
def internship_detail(internship_id):
    row = db.query_one(BASE_INTERNSHIP_SELECT + " WHERE i.internship_id = :id", {"id": internship_id})
    if not row:
        abort(404)
    return render_template("internship_detail.html", i=row)


@app.route("/internships/new", methods=["GET", "POST"])
def internship_new():
    companies = get_companies()
    form = request.form if request.method == "POST" else {}
    if request.method == "POST":
        errors = []
        role = form.get("role_title", "").strip()
        category = form.get("category", "").strip()
        deadline = form.get("deadline", "").strip()
        try:
            company_id = int(form.get("company_id", ""))
        except ValueError:
            company_id = None
            errors.append("Please choose a company (add one on the Companies page first if needed).")
        if len(role) < 3:
            errors.append("Please enter a role title.")
        if not category:
            errors.append("Please choose a category.")
        mode = form.get("work_mode", "Onsite")
        if mode not in MODES:
            errors.append("Invalid work mode.")
        if deadline:
            try:
                datetime.strptime(deadline, "%Y-%m-%d")
            except ValueError:
                errors.append("Deadline must be a valid date.")
        weeks = form.get("duration_weeks", "").strip()
        openings = form.get("openings", "1").strip() or "1"
        if weeks and not (weeks.isdigit() and 1 <= int(weeks) <= 104):
            errors.append("Duration must be a number of weeks between 1 and 104.")
        if not (openings.isdigit() and 1 <= int(openings) <= 999):
            errors.append("Openings must be a number between 1 and 999.")
        if errors:
            for e in errors:
                flash(e, "danger")
        else:
            new_id = db.next_id("internships_seq")
            db.execute("""
                INSERT INTO internships (internship_id, company_id, role_title, category, description,
                       location, work_mode, duration_weeks, stipend, eligibility, openings, deadline)
                VALUES (:id, :company_id, :role, :category, :description, :location, :mode,
                       :weeks, :stipend, :eligibility, :openings, TO_DATE(:deadline, 'YYYY-MM-DD'))""",
                       {"id": new_id, "company_id": company_id, "role": role, "category": category,
                        "description": form.get("description", "").strip()[:2000] or None,
                        "location": form.get("location", "").strip()[:100] or None,
                        "mode": mode, "weeks": int(weeks) if weeks else None,
                        "stipend": form.get("stipend", "").strip()[:40] or None,
                        "eligibility": form.get("eligibility", "").strip()[:500] or None,
                        "openings": int(openings), "deadline": deadline or None})
            flash("Internship posted.", "success")
            return redirect(url_for("internship_detail", internship_id=new_id))
    return render_template("internship_form.html", companies=companies, form=form,
                           categories=list(CATEGORY_ICONS), modes=MODES)


@app.route("/internships/<int:internship_id>/apply", methods=["GET", "POST"])
def apply(internship_id):
    row = db.query_one(BASE_INTERNSHIP_SELECT + " WHERE i.internship_id = :id", {"id": internship_id})
    if not row:
        abort(404)
    students = db.query("SELECT student_id, full_name, email FROM students ORDER BY full_name")
    if request.method == "POST":
        if not row["is_open"]:
            flash("Applications for this internship are closed.", "danger")
        else:
            sid = request.form.get("student_id", "")
            if not sid.isdigit() or not db.query_one(
                    "SELECT 1 AS ok FROM students WHERE student_id = :id", {"id": int(sid)}):
                flash("Please choose a registered student.", "danger")
            else:
                try:
                    app_id = db.next_id("applications_seq")
                    db.execute("""INSERT INTO applications (application_id, student_id, internship_id, status)
                                  VALUES (:id, :sid, :iid, 'PENDING')""",
                               {"id": app_id, "sid": int(sid), "iid": internship_id})
                    flash("Application submitted! Track its status on the Track page.", "success")
                    return redirect(url_for("applications"))
                except db.DatabaseError as exc:
                    if db.ora_code(exc) == 1:
                        flash("This student has already applied to this internship.", "warning")
                    else:
                        raise
    return render_template("apply.html", i=row, students=students)


# --------------------------------------------------------------- students
@app.route("/students")
def students():
    q = request.args.get("q", "").strip()
    sql = """SELECT s.student_id, s.full_name, s.email, s.phone, s.department, s.skills, s.created_at,
                    (SELECT COUNT(*) FROM applications a WHERE a.student_id = s.student_id) AS app_count
               FROM students s"""
    params = {}
    if q:
        sql += (" WHERE UPPER(s.full_name) LIKE :q OR UPPER(s.email) LIKE :q"
                " OR UPPER(s.department) LIKE :q OR UPPER(s.skills) LIKE :q")
        params["q"] = "%" + q.upper() + "%"
    sql += " ORDER BY s.full_name"
    return render_template("students.html", students=db.query(sql, params), q=q)


@app.route("/students/new", methods=["GET", "POST"])
def student_new():
    data = {}
    if request.method == "POST":
        data, errors = clean_student(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
        else:
            try:
                sid = db.next_id("students_seq")
                db.execute("""INSERT INTO students (student_id, full_name, email, phone, department, skills)
                              VALUES (:id, :full_name, :email, :phone, :department, :skills)""",
                           {"id": sid, **{k: (v or None) for k, v in data.items()}})
                flash(f"Welcome, {data['full_name']}! You are registered.", "success")
                return redirect(url_for("students"))
            except db.DatabaseError as exc:
                if db.ora_code(exc) == 1:
                    flash("That email address is already registered.", "warning")
                else:
                    raise
    return render_template("student_form.html", s=data, departments=DEPARTMENTS, editing=False)


@app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
def student_edit(student_id):
    current = db.query_one("SELECT * FROM students WHERE student_id = :id", {"id": student_id})
    if not current:
        abort(404)
    data = current
    if request.method == "POST":
        data, errors = clean_student(request.form)
        data["student_id"] = student_id
        if errors:
            for e in errors:
                flash(e, "danger")
        else:
            try:
                db.execute("""UPDATE students SET full_name = :full_name, email = :email, phone = :phone,
                                     department = :department, skills = :skills
                               WHERE student_id = :id""",
                           {"id": student_id, **{k: (data[k] or None) for k in
                                                 ("full_name", "email", "phone", "department", "skills")}})
                flash("Student updated.", "success")
                return redirect(url_for("students"))
            except db.DatabaseError as exc:
                if db.ora_code(exc) == 1:
                    flash("Another student already uses that email address.", "warning")
                else:
                    raise
    return render_template("student_form.html", s=data, departments=DEPARTMENTS, editing=True)


@app.route("/students/<int:student_id>/delete", methods=["POST"])
def student_delete(student_id):
    # applications.student_id is ON DELETE CASCADE, so this student's applications go too.
    if db.execute("DELETE FROM students WHERE student_id = :id", {"id": student_id}):
        flash("Student (and their applications) deleted.", "success")
    else:
        flash("Student not found.", "warning")
    return redirect(url_for("students"))


# ----------------------------------------------------------- applications
@app.route("/applications")
def applications():
    status = request.args.get("status", "").strip().upper()
    q = request.args.get("q", "").strip()
    where, params = [], {}
    if status in STATUSES:
        where.append("a.status = :status")
        params["status"] = status
    if q:
        where.append("(UPPER(s.full_name) LIKE :q OR UPPER(s.email) LIKE :q "
                     "OR UPPER(i.role_title) LIKE :q OR UPPER(c.company_name) LIKE :q)")
        params["q"] = "%" + q.upper() + "%"
    sql = """SELECT a.application_id, a.status, a.applied_on, a.updated_on,
                    s.student_id, s.full_name, s.email,
                    i.internship_id, i.role_title, c.company_name
               FROM applications a
               JOIN students s    ON s.student_id    = a.student_id
               JOIN internships i ON i.internship_id = a.internship_id
               JOIN companies c   ON c.company_id    = i.company_id"""
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY a.applied_on DESC, a.application_id DESC"
    counts = {r["status"]: r["cnt"] for r in db.query(
        "SELECT status, COUNT(*) AS cnt FROM applications GROUP BY status")}
    return render_template("applications.html", applications=db.query(sql, params),
                           status=status, q=q, counts=counts)


@app.route("/applications/<int:application_id>/status", methods=["POST"])
def application_status(application_id):
    status = request.form.get("status", "").upper()
    if status not in STATUSES:
        flash("Invalid status.", "danger")
    elif db.execute("UPDATE applications SET status = :s, updated_on = SYSDATE WHERE application_id = :id",
                    {"s": status, "id": application_id}):
        flash(f"Application marked {status.title()}.", "success")
    else:
        flash("Application not found.", "warning")
    return redirect(request.form.get("next") or url_for("applications"))


@app.route("/track")
def track():
    email = request.args.get("email", "").strip().lower()
    student, rows = None, []
    if email:
        student = db.query_one("SELECT student_id, full_name, email FROM students WHERE email = :e",
                               {"e": email})
        if student:
            rows = db.query("""SELECT a.application_id, a.status, a.applied_on, a.updated_on,
                                      i.internship_id, i.role_title, i.location, c.company_name
                                 FROM applications a
                                 JOIN internships i ON i.internship_id = a.internship_id
                                 JOIN companies c   ON c.company_id    = i.company_id
                                WHERE a.student_id = :sid
                                ORDER BY a.applied_on DESC""", {"sid": student["student_id"]})
        else:
            flash("No student is registered with that email.", "warning")
    return render_template("track.html", email=email, student=student, rows=rows)


# -------------------------------------------------------------- companies
@app.route("/companies", methods=["GET", "POST"])
def companies():
    if request.method == "POST":
        name = request.form.get("company_name", "").strip()
        if len(name) < 2:
            flash("Please enter a company name.", "danger")
        else:
            try:
                cid = db.next_id("companies_seq")
                db.execute("""INSERT INTO companies (company_id, company_name, industry, location, website)
                              VALUES (:id, :name, :industry, :location, :website)""",
                           {"id": cid, "name": name[:100],
                            "industry": request.form.get("industry", "").strip()[:60] or None,
                            "location": request.form.get("location", "").strip()[:100] or None,
                            "website": request.form.get("website", "").strip()[:200] or None})
                flash("Company added.", "success")
                return redirect(url_for("companies"))
            except db.DatabaseError as exc:
                if db.ora_code(exc) == 1:
                    flash("A company with that name already exists.", "warning")
                else:
                    raise
    rows = db.query("""SELECT c.company_id, c.company_name, c.industry, c.location, c.website,
                              (SELECT COUNT(*) FROM internships i WHERE i.company_id = c.company_id) AS posts
                         FROM companies c ORDER BY c.company_name""")
    return render_template("companies.html", companies=rows)


# ----------------------------------------------------------------- health
REQUIRED_COLUMNS = {
    "COMPANIES": ["COMPANY_ID", "COMPANY_NAME", "INDUSTRY", "LOCATION", "WEBSITE"],
    "STUDENTS": ["STUDENT_ID", "FULL_NAME", "EMAIL", "PHONE", "DEPARTMENT", "SKILLS", "CREATED_AT"],
    "INTERNSHIPS": ["INTERNSHIP_ID", "COMPANY_ID", "ROLE_TITLE", "CATEGORY", "DESCRIPTION", "LOCATION",
                    "WORK_MODE", "DURATION_WEEKS", "STIPEND", "ELIGIBILITY", "OPENINGS", "DEADLINE",
                    "CREATED_AT"],
    "APPLICATIONS": ["APPLICATION_ID", "STUDENT_ID", "INTERNSHIP_ID", "STATUS", "APPLIED_ON", "UPDATED_ON"],
}
REQUIRED_SEQUENCES = ["COMPANIES_SEQ", "STUDENTS_SEQ", "INTERNSHIPS_SEQ", "APPLICATIONS_SEQ"]


@app.route("/health")
def health():
    """Shows whether the real Oracle connection and tables are usable."""
    info = {"driver": db.DRIVER_NAME, "dsn": os.getenv("DB_DSN", "localhost:1521/XE"),
            "user": os.getenv("DB_USER", "INTERNHUB"), "connected": False,
            "version": None, "problems": [], "tables": []}
    try:
        db.query_one("SELECT 1 AS ok FROM dual")
        info["connected"] = True
    except db.DBConnectionError as exc:
        info["problems"].append(str(exc))
        return render_template("health.html", info=info)
    try:
        v = db.query_one("SELECT banner FROM v$version WHERE ROWNUM = 1")
        info["version"] = v["banner"] if v else None
    except db.DatabaseError:
        info["version"] = "(not visible to this user)"
    have = {}
    for r in db.query("SELECT table_name, column_name FROM user_tab_columns"):
        have.setdefault(r["table_name"], set()).add(r["column_name"])
    seqs = {r["sequence_name"] for r in db.query("SELECT sequence_name FROM user_sequences")}
    for table, cols in REQUIRED_COLUMNS.items():
        if table not in have:
            info["problems"].append(f"Table {table} is missing - run: python setup_db.py")
            info["tables"].append((table, "missing"))
        else:
            absent = [c for c in cols if c not in have[table]]
            if absent:
                info["problems"].append(f"Table {table} lacks column(s): {', '.join(absent)}")
                info["tables"].append((table, "columns missing"))
            else:
                n = db.query_one(f"SELECT COUNT(*) AS n FROM {table}")["n"]
                info["tables"].append((table, f"OK - {n} rows"))
    for s in REQUIRED_SEQUENCES:
        if s not in seqs:
            info["problems"].append(f"Sequence {s} is missing - run: python setup_db.py")
    return render_template("health.html", info=info)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")),
            debug=os.getenv("FLASK_DEBUG", "0") == "1")
