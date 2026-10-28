"""Run the InternHub SQL scripts without needing SQL*Plus.

Usage (from the project folder, with the virtual environment active):
    python setup_db.py            -> creates missing tables/sequences only
    python setup_db.py --sample   -> also adds the optional sample data

Both scripts are non-destructive: they never drop, alter or delete anything.
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv()
import db  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def split_blocks(text):
    """Split a script into PL/SQL blocks that end with a line containing only '/'."""
    blocks, current = [], []
    for line in text.splitlines():
        if line.strip() == "/":
            block = "\n".join(current).strip()
            if block:
                blocks.append(block)
            current = []
        elif line.strip().upper().startswith("SET "):
            continue  # SQL*Plus-only command
        else:
            current.append(line)
    tail = "\n".join(current).strip()
    if tail:
        blocks.append(tail)
    return blocks


def run_script(conn, filename):
    path = os.path.join(HERE, "sql", filename)
    with open(path, encoding="utf-8") as fh:
        blocks = split_blocks(fh.read())
    cur = conn.cursor()
    print(f"\n=== {filename} ===")
    for block in blocks:
        cur.callproc("dbms_output.enable")
        cur.execute(block)
        line_var = cur.var(str)
        status_var = cur.var(int)
        while True:
            cur.callproc("dbms_output.get_line", (line_var, status_var))
            if status_var.getvalue() != 0:
                break
            print("  " + line_var.getvalue())
    conn.commit()
    cur.close()


def main():
    try:
        conn = db.connect()
    except db.DBConnectionError as exc:
        print("\nCould not connect to Oracle:\n  " + str(exc))
        sys.exit(1)
    try:
        run_script(conn, "02_schema.sql")
        if "--sample" in sys.argv:
            run_script(conn, "03_sample_data.sql")
        print("\nDone.")
    except db.DatabaseError as exc:
        print("\nOracle returned an error:\n  " + str(exc))
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
