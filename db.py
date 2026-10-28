"""Oracle database helpers for InternHub.

Oracle 10g XE is too old for python-oracledb's default "thin" mode (it needs
Oracle Database 12.1+), so this module always uses "thick" mode, which loads
Oracle Instant Client libraries installed on your PC (see README.md).

It also works with the older cx_Oracle driver if oracledb is not installed.
"""
import os

from flask import g

try:
    import oracledb as driver
    DRIVER_NAME = "oracledb"
except ImportError:  # fall back to the older driver
    import cx_Oracle as driver
    DRIVER_NAME = "cx_Oracle"

DatabaseError = driver.DatabaseError
_client_ready = False


class DBConnectionError(Exception):
    """Raised with a beginner-friendly message when we cannot connect."""


def ora_code(exc):
    """Return the ORA-xxxxx number inside a driver exception (or None)."""
    try:
        return exc.args[0].code
    except Exception:
        return None


def _init_client():
    """Load Oracle Instant Client once (thick mode)."""
    global _client_ready
    if _client_ready:
        return
    lib_dir = os.getenv("ORACLE_CLIENT_DIR", "").strip() or None
    init = getattr(driver, "init_oracle_client", None)
    if init is not None:  # cx_Oracle 7.x has no init function (uses PATH)
        try:
            init(lib_dir=lib_dir) if lib_dir else init()
        except Exception as exc:
            # Calling it twice (e.g. Flask reloader) is harmless.
            if "already" not in str(exc).lower():
                raise DBConnectionError(
                    "Could not load Oracle Instant Client. Set ORACLE_CLIENT_DIR in .env "
                    "to the folder that contains oci.dll (and make sure Python and the "
                    f"client are both 64-bit or both 32-bit). Driver said: {exc}"
                )
    _client_ready = True


def _friendly(exc):
    text = str(exc)
    hints = {
        "DPI-1047": "Oracle Client libraries were not found. Install Oracle Instant Client and set ORACLE_CLIENT_DIR in .env.",
        "DPI-1050": "Your Oracle Client is too old for this driver. Use a newer Instant Client or cx_Oracle 7.3 (see README).",
        "DPY-3010": "Thin mode cannot talk to Oracle 10g. Thick mode (Instant Client) is required; check ORACLE_CLIENT_DIR.",
        "ORA-12541": "The Oracle listener is not running. Start the 'OracleServiceXE' and 'OracleXETNSListener' Windows services.",
        "ORA-12514": "The listener does not know the service name. Check DB_DSN (expected localhost:1521/XE).",
        "ORA-12505": "The listener does not know the SID. Check DB_DSN (expected localhost:1521/XE).",
        "ORA-01017": "Wrong DB_USER or DB_PASSWORD in your .env file.",
        "ORA-28000": "The INTERNHUB account is locked. Unlock it as SYSTEM: ALTER USER internhub ACCOUNT UNLOCK;",
        "ORA-12170": "Connection timed out. Is the database running?",
    }
    for key, hint in hints.items():
        if key in text:
            return f"{hint}  [{text.strip()}]"
    return text.strip()


def connect():
    """Open a new connection using the settings in .env."""
    _init_client()
    user = os.getenv("DB_USER", "INTERNHUB")
    password = os.getenv("DB_PASSWORD", "")
    dsn = os.getenv("DB_DSN", "localhost:1521/XE")
    try:
        return driver.connect(user=user, password=password, dsn=dsn)
    except DBConnectionError:
        raise
    except Exception as exc:
        raise DBConnectionError(_friendly(exc))


def get_conn():
    """One connection per web request (stored on Flask's `g`)."""
    if "db" not in g:
        g.db = connect()
    return g.db


def close_conn(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass


def query(sql, params=None):
    """Run a SELECT and return a list of dicts with lower-case keys."""
    cur = get_conn().cursor()
    try:
        cur.execute(sql, params or {})
        cols = [d[0].lower() for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        cur.close()


def query_one(sql, params=None):
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql, params=None):
    """Run INSERT / UPDATE / DELETE, commit, and return rows affected."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(sql, params or {})
        count = cur.rowcount
        conn.commit()
        return count
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def next_id(sequence):
    """Oracle 10g has no IDENTITY columns, so we ask a sequence for the id."""
    row = query_one(f"SELECT {sequence}.NEXTVAL AS id FROM dual")
    return int(row["id"])
