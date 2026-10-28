"""Offline smoke test: checks that every page renders and forms validate.

IMPORTANT: this does NOT talk to Oracle. It replaces the database functions with
canned data, so it only proves the Flask routes, templates and validation work.
Real database behaviour must be checked on your PC (see README, "Verify").

Run:  python tests/smoke_test.py
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as app_module  # noqa: E402
import db  # noqa: E402

NOW = datetime.now()
INTERNSHIP = dict(internship_id=1, role_title="Python Intern", category="Software", description="Build APIs",
                  location="Pune", work_mode="Hybrid", duration_weeks=8, stipend="Rs 10,000", eligibility="CSE",
                  openings=2, deadline=NOW + timedelta(days=10), company_id=1, company_name="Acme",
                  industry="IT", applicants=1, is_open=1, created_at=NOW)
STUDENT = dict(student_id=1, full_name="Asha Rao", email="asha@example.com", phone="9876543210",
               department="Computer Science", skills="Python", created_at=NOW, app_count=1)
APPLICATION = dict(application_id=1, status="PENDING", applied_on=NOW, updated_on=None, student_id=1,
                   full_name="Asha Rao", email="asha@example.com", internship_id=1, role_title="Python Intern",
                   company_name="Acme", location="Pune")
calls = []


def fake_query(sql, params=None):
    s = " ".join(sql.split()).upper()
    if "FROM INTERNSHIPS I" in s and "FROM APPLICATIONS A JOIN" not in s:
        return [INTERNSHIP]
    if "FROM STUDENTS S" in s:
        return [STUDENT]
    if "SELECT STUDENT_ID, FULL_NAME, EMAIL FROM STUDENTS" in s:
        return [STUDENT]
    if "FROM APPLICATIONS A" in s:
        return [APPLICATION]
    if "GROUP BY STATUS" in s:
        return [{"status": "PENDING", "cnt": 1}]
    if "GROUP BY CATEGORY" in s:
        return [{"category": "Software", "cnt": 1}]
    if "FROM COMPANIES C" in s:
        return [dict(company_id=1, company_name="Acme", industry="IT", location="Pune", website=None, posts=1)]
    if "FROM COMPANIES ORDER" in s:
        return [dict(company_id=1, company_name="Acme")]
    if "FROM INTERNSHIPS I" in s:
        return [INTERNSHIP]
    if "FROM STUDENTS WHERE STUDENT_ID" in s:
        return [STUDENT]
    if "FROM STUDENTS WHERE EMAIL" in s:
        return [STUDENT] if (params or {}).get("e") == "asha@example.com" else []
    if "FROM DUAL" in s and "STUDENTS" in s:
        return [dict(students=1, companies=1, open_internships=1, applications=1)]
    if "FROM USER_TAB_COLUMNS" in s:
        rows = []
        for t, cols in app_module.REQUIRED_COLUMNS.items():
            rows += [dict(table_name=t, column_name=c) for c in cols]
        return rows
    if "USER_SEQUENCES" in s:
        return [dict(sequence_name=n) for n in app_module.REQUIRED_SEQUENCES]
    if "V$VERSION" in s:
        return [dict(banner="Oracle Database 10g Express Edition (FAKE)")]
    if "COUNT(*) AS N" in s:
        return [dict(n=1)]
    if "SELECT 1 AS OK" in s:
        return [dict(ok=1)]
    if "ROWNUM <= 6" in s:
        return [INTERNSHIP]
    raise AssertionError("Unhandled SQL in fake: " + s[:120])


def fake_execute(sql, params=None):
    calls.append((" ".join(sql.split())[:40], params))
    return 1


db.query = fake_query
db.query_one = lambda sql, params=None: (fake_query(sql, params) or [None])[0]
db.execute = fake_execute
db.next_id = lambda seq: 99

client = app_module.app.test_client()
app_module.app.config["TESTING"] = True
failures = []


def check(name, cond):
    print(("PASS  " if cond else "FAIL  ") + name)
    if not cond:
        failures.append(name)


for path in ["/", "/internships", "/internships?q=py&category=Software&mode=Hybrid&open=1",
             "/internships/1", "/internships/new", "/internships/1/apply", "/students", "/students/new",
             "/students/1/edit", "/applications", "/applications?status=PENDING", "/track",
             "/track?email=asha@example.com", "/track?email=nobody@example.com", "/companies", "/health"]:
    r = client.get(path)
    check(f"GET {path} -> {r.status_code}", r.status_code == 200)

check("unknown page is 404", client.get("/nope").status_code == 404)

r = client.post("/students/new", data=dict(full_name="A", email="bad", phone="1", department=""))
check("bad registration rejected (no insert)", r.status_code == 200 and not calls)

r = client.post("/students/new", data=dict(full_name="Ravi Kumar", email="ravi@example.com",
                                           phone="9123456780", department="Electronics", skills="C"))
check("valid registration inserts and redirects", r.status_code == 302 and any("INSERT INTO STUDENTS" in c[0].upper() for c in calls))

r = client.post("/applications/1/status", data=dict(status="ACCEPTED"))
check("status update accepted", r.status_code == 302 and any("UPDATE APPLICATIONS" in c[0].upper() for c in calls))
n = len(calls)
client.post("/applications/1/status", data=dict(status="HIRED"))
check("invalid status ignored", len(calls) == n)

r = client.post("/students/1/delete")
check("student delete runs", r.status_code == 302 and any("DELETE FROM STUDENTS" in c[0].upper() for c in calls))

r = client.post("/internships/1/apply", data=dict(student_id="1"))
check("apply inserts application", r.status_code == 302 and any("INSERT INTO APPLICATIONS" in c[0].upper() for c in calls))

print("\n%d failure(s)" % len(failures))
sys.exit(1 if failures else 0)
