"""READ-ONLY: print the tables, columns, constraints and row counts of the
INTERNHUB schema so you can see what already exists before InternHub touches it.

Usage:  python inspect_db.py
"""
import sys

from dotenv import load_dotenv

load_dotenv()
import db  # noqa: E402

try:
    conn = db.connect()
except db.DBConnectionError as exc:
    print("Could not connect to Oracle:\n  " + str(exc))
    sys.exit(1)

cur = conn.cursor()
try:
    cur.execute("SELECT table_name FROM user_tables ORDER BY table_name")
    tables = [r[0] for r in cur.fetchall()]
    print(f"Connected. Driver: {db.DRIVER_NAME}.  Tables in this schema: {len(tables)}\n")
    for t in tables:
        print(f"TABLE {t}")
        cur.execute(
            "SELECT column_name, data_type, data_length, nullable FROM user_tab_columns "
            "WHERE table_name = :t ORDER BY column_id", {"t": t})
        for name, typ, length, nullable in cur.fetchall():
            print(f"    {name:<22} {typ}({length})  {'NULL' if nullable == 'Y' else 'NOT NULL'}")
        cur.execute(
            "SELECT constraint_name, constraint_type FROM user_constraints "
            "WHERE table_name = :t ORDER BY constraint_type", {"t": t})
        for cname, ctype in cur.fetchall():
            print(f"    constraint {cname} ({ctype})")
        cur.execute(f'SELECT COUNT(*) FROM "{t}"')
        print(f"    rows: {cur.fetchone()[0]}\n")
    cur.execute("SELECT sequence_name FROM user_sequences ORDER BY sequence_name")
    print("Sequences:", ", ".join(r[0] for r in cur.fetchall()) or "(none)")
    needed = {"COMPANIES", "STUDENTS", "INTERNSHIPS", "APPLICATIONS"}
    missing = sorted(needed - set(tables))
    print("\nInternHub needs: " + ", ".join(sorted(needed)))
    print("Missing tables:  " + (", ".join(missing) if missing else "none"))
except db.DatabaseError as exc:
    print("Oracle returned an error:\n  " + str(exc))
finally:
    conn.close()
