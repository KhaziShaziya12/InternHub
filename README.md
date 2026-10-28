# InternHub – Internship Management System

Flask + Bootstrap web app that stores everything in **Oracle Database 10g XE** (`INTERNHUB` user, `localhost:1521/XE`).

Students can search internships by category and eligibility, register, apply, and track their application status. Staff can manage students, post internships and update application statuses (Pending / Accepted / Rejected).

> **Honest status.** This project was written in a cloud workspace that cannot reach your PC or your Oracle database. The Python code and pages were checked offline (`tests/smoke_test.py`, which uses stand-in data, **not** Oracle). **The real Oracle connection has not been tested.** Follow "Verify the connection" below on your PC. `python inspect_db.py` and the `/health` page tell you exactly what works.

## What is in the folder

| Path | Purpose |
|---|---|
| `app.py` | Flask routes and validation |
| `db.py` | Oracle connection helpers (thick mode) |
| `inspect_db.py` | **Read-only** report of your existing tables and row counts |
| `setup_db.py` | Runs the SQL scripts (no SQL*Plus needed) |
| `sql/01_inspect_existing.sql` | Read-only inspection queries |
| `sql/02_schema.sql` | Creates missing tables/sequences only |
| `sql/03_sample_data.sql` | Optional sample rows, inserted only if absent |
| `templates/`, `static/` | HTML, CSS, JavaScript |
| `tests/smoke_test.py` | Offline page/validation test |

## Step-by-step setup on Windows 11

### 1. Check Oracle is running
Open **Services** (Win + R, type `services.msc`) and make sure `OracleServiceXE` and `OracleXETNSListener` are **Running**.

### 2. Install Python
Python 3.10 or newer, 64-bit, from python.org (tick "Add python.exe to PATH"). Check with `python --version`.

### 3. Oracle Client setup (important for 10g)
`python-oracledb` normally connects without any client ("thin mode"), but thin mode needs **Oracle Database 12.1 or newer**. Your 10g XE therefore needs **thick mode**, which uses Oracle Instant Client libraries:

1. Find out whether your Python is 32-bit or 64-bit: `python -c "import struct;print(struct.calcsize('P')*8)"`.
2. Download **Oracle Instant Client "Basic"** from oracle.com (search "Oracle Instant Client downloads Windows") matching that bit-ness. Version **11.2** is the safest match for a 10g server. Newer clients (12.x–19.x) may refuse to talk to 10g, and 19c+ definitely cannot be assumed to; try 11.2 first.
3. Unzip it, e.g. to `C:\oracle\instantclient_11_2` (the folder must contain `oci.dll`).
4. Instant Client 11.2 needs the **Microsoft Visual C++ 2005/2010 Redistributable** of the same bit-ness. Install it if you see error `DPI-1047`.
5. You will put this folder in `.env` as `ORACLE_CLIENT_DIR` in step 5.

You do **not** need to install a full Oracle client; your XE install is only the server.

### 4. Create the virtual environment and install packages
Open **Terminal** in the project folder (right-click the folder → *Open in Terminal*):

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
(If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.)

### 5. Configure `.env`
```powershell
copy .env.example .env
notepad .env
```
Set `DB_PASSWORD` to the INTERNHUB password, `ORACLE_CLIENT_DIR` to your Instant Client folder, and `SECRET_KEY` to any long random text. `DB_USER=INTERNHUB` and `DB_DSN=localhost:1521/XE` are already set.

### 6. Look at your existing database first (read-only)
```powershell
python inspect_db.py
```
This prints your tables, columns, constraints and row counts. It changes nothing. If it prints "Connected", the driver and client work.

InternHub uses these tables and columns:
`COMPANIES`, `STUDENTS`, `INTERNSHIPS`, `APPLICATIONS` (full list in `sql/02_schema.sql`).

* **Tables are missing →** go to step 7.
* **Tables already exist with different names or columns →** do *not* run step 7 blindly. Send the `inspect_db.py` output and the app's SQL in `app.py` should be adapted to your tables. The `/health` page also lists missing columns.

### 7. Create the missing tables (non-destructive)
```powershell
python setup_db.py            # creates only what is missing
python setup_db.py --sample   # same, plus optional sample data
```
Both scripts check `user_tables` / `user_sequences` first, never drop or alter anything, and never delete rows. You can also run `sql\02_schema.sql` and `sql\03_sample_data.sql` in SQL Developer or SQL*Plus.

### 8. Start the app
```powershell
python app.py
```
Open <http://127.0.0.1:5000>.

### Verify the connection
Open <http://127.0.0.1:5000/health>. It shows connected/not connected, the Oracle version banner, each table's state and row count, and any missing columns or sequences. Then try the checklist:

1. Register a student → appears in **Students**.
2. Open an internship → **Apply** → appears in **Applications** as Pending.
3. Change its status → **Track** page (search the student's email) shows the new status.
4. Edit and delete a student (deleting also removes that student's applications).

## Features
* **Home:** hero search bar, live statistics, category tiles, latest internships.
* **Internships:** search plus filters (category, work mode, open only), eligibility box on every card, detail page, post a new internship.
* **Students:** register, edit, delete (with confirmation), search.
* **Applications:** apply, duplicate protection, filter by status, change status, and a progress tracker on the Track page.
* **Companies:** list and add.
* **Errors:** friendly messages for connection problems (listener down, wrong password, locked account, missing client), missing tables/columns, duplicate email, invalid input.

## Troubleshooting

| Message | Meaning / fix |
|---|---|
| `DPI-1047` | Instant Client not found. Fix `ORACLE_CLIENT_DIR`, match 32/64-bit, install the VC++ redistributable. |
| `DPY-3010` | Thin mode used with 10g. Make sure `ORACLE_CLIENT_DIR` is set so thick mode loads. |
| `DPI-1050` / client too old | Use a newer Instant Client, or switch to `cx_Oracle==8.3.0` (Python 3.10 or older). |
| `ORA-12541` | Listener not running: start `OracleXETNSListener`. |
| `ORA-12514` / `ORA-12505` | Service/SID mismatch. Try `DB_DSN=localhost:1521/XE`. |
| `ORA-01017` | Wrong password in `.env`. |
| `ORA-28000` | Account locked: as SYSTEM run `ALTER USER internhub ACCOUNT UNLOCK;`. |
| `ORA-00942` | A table is missing. Run `python setup_db.py`. |
| Client/server mismatch persists | Try Instant Client 10.2 or 11.2 and a cx_Oracle fallback (see `requirements.txt`). |

## Design notes
White and very light blue background, royal blue primary, system fonts, visible focus outlines, skip link, labelled form fields, status shown with text and icon (not colour alone), responsive Bootstrap 5 layout. Bootstrap and icons load from a CDN, so the pages need internet access.

## Safety notes
* The app has no login. It is meant for local learning use, so do not expose it to the internet as is.
* Never share your real `.env` file.
* All SQL uses bind variables (no string-built user input).
