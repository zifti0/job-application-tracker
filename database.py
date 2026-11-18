"""
database.py - all MySQL access for the Job Application Tracker.

Every function opens a connection, runs its query, and closes the
connection. All values are passed as parameters (%s placeholders),
never pasted into the SQL string, which protects against SQL injection.
"""

import json
import os

import mysql.connector
from dotenv import load_dotenv

# Read DB settings from the .env file (see .env.example)
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "job_tracker"),
}

JOB_TYPES = ["Full-time", "Part-time", "Contract", "Internship"]
STATUSES = ["Applied", "Screening", "Interview", "Offer", "Rejected", "Withdrawn"]


# -------------------------------------------------------------
# Generic helpers
# -------------------------------------------------------------

def get_db():
    """Open a new connection to the job_tracker database."""
    return mysql.connector.connect(**DB_CONFIG)


def query(sql, params=(), one=False):
    """Run a SELECT and return a list of dicts (or a single dict if one=True)."""
    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()
    finally:
        conn.close()
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql, params=()):
    """Run an INSERT / UPDATE / DELETE, commit it, and return the new row id."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        new_id = cursor.lastrowid
        cursor.close()
    except mysql.connector.Error:
        conn.rollback()  # undo the partial change, then let the app show an error page
        raise
    finally:
        conn.close()
    return new_id


def parse_json(value, default=None):
    """MySQL returns JSON columns as text; turn them back into Python lists/dicts."""
    if value is None or value == "":
        return default
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


# -------------------------------------------------------------
# Companies
# -------------------------------------------------------------

def get_companies():
    """All companies with how many jobs and contacts each has."""
    return query("""
        SELECT c.*,
               (SELECT COUNT(*) FROM jobs j     WHERE j.company_id = c.company_id) AS job_count,
               (SELECT COUNT(*) FROM contacts k WHERE k.company_id = c.company_id) AS contact_count
        FROM companies c
        ORDER BY c.company_name
    """)


def get_company(company_id):
    return query("SELECT * FROM companies WHERE company_id = %s", (company_id,), one=True)


def add_company(data):
    return execute("""
        INSERT INTO companies (company_name, industry, website, city, state, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (data["company_name"], data["industry"], data["website"],
          data["city"], data["state"], data["notes"]))


def update_company(company_id, data):
    execute("""
        UPDATE companies
        SET company_name = %s, industry = %s, website = %s,
            city = %s, state = %s, notes = %s
        WHERE company_id = %s
    """, (data["company_name"], data["industry"], data["website"],
          data["city"], data["state"], data["notes"], company_id))


def delete_company(company_id):
    # ON DELETE CASCADE also removes this company's jobs, their applications, and contacts
    execute("DELETE FROM companies WHERE company_id = %s", (company_id,))


# -------------------------------------------------------------
# Jobs
# -------------------------------------------------------------

def _decode_job(job):
    if job:
        job["requirements"] = parse_json(job.get("requirements"), [])
    return job


def get_jobs(company_id=None):
    """All jobs joined with their company name (optionally for one company)."""
    sql = """
        SELECT j.*, c.company_name
        FROM jobs j
        JOIN companies c ON j.company_id = c.company_id
    """
    params = ()
    if company_id is not None:
        sql += " WHERE j.company_id = %s"
        params = (company_id,)
    sql += " ORDER BY j.date_posted DESC, j.job_title"
    return [_decode_job(j) for j in query(sql, params)]


def get_job(job_id):
    job = query("""
        SELECT j.*, c.company_name
        FROM jobs j
        JOIN companies c ON j.company_id = c.company_id
        WHERE j.job_id = %s
    """, (job_id,), one=True)
    return _decode_job(job)


def add_job(data):
    return execute("""
        INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max,
                          job_url, date_posted, requirements)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (data["company_id"], data["job_title"], data["job_type"], data["salary_min"],
          data["salary_max"], data["job_url"], data["date_posted"],
          json.dumps(data["requirements"])))


def update_job(job_id, data):
    execute("""
        UPDATE jobs
        SET company_id = %s, job_title = %s, job_type = %s, salary_min = %s,
            salary_max = %s, job_url = %s, date_posted = %s, requirements = %s
        WHERE job_id = %s
    """, (data["company_id"], data["job_title"], data["job_type"], data["salary_min"],
          data["salary_max"], data["job_url"], data["date_posted"],
          json.dumps(data["requirements"]), job_id))


def delete_job(job_id):
    execute("DELETE FROM jobs WHERE job_id = %s", (job_id,))


# -------------------------------------------------------------
# Applications
# -------------------------------------------------------------

APPLICATION_SELECT = """
    SELECT a.*, j.job_title, j.company_id, c.company_name
    FROM applications a
    JOIN jobs j      ON a.job_id = j.job_id
    JOIN companies c ON j.company_id = c.company_id
"""


def _decode_application(app_row):
    if app_row:
        app_row["interview_data"] = parse_json(app_row.get("interview_data"), {})
        app_row["cover_letter_sent"] = bool(app_row.get("cover_letter_sent"))
    return app_row


def get_applications(status=None, job_id=None):
    sql = APPLICATION_SELECT
    conditions, params = [], []
    if status:
        conditions.append("a.status = %s")
        params.append(status)
    if job_id is not None:
        conditions.append("a.job_id = %s")
        params.append(job_id)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY a.application_date DESC, a.application_id DESC"
    return [_decode_application(a) for a in query(sql, tuple(params))]


def get_application(application_id):
    row = query(APPLICATION_SELECT + " WHERE a.application_id = %s",
                (application_id,), one=True)
    return _decode_application(row)


def add_application(data):
    return execute("""
        INSERT INTO applications (job_id, application_date, status, resume_version,
                                  cover_letter_sent, interview_data)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (data["job_id"], data["application_date"], data["status"], data["resume_version"],
          data["cover_letter_sent"],
          json.dumps(data["interview_data"]) if data["interview_data"] else None))


def update_application(application_id, data):
    execute("""
        UPDATE applications
        SET job_id = %s, application_date = %s, status = %s, resume_version = %s,
            cover_letter_sent = %s, interview_data = %s
        WHERE application_id = %s
    """, (data["job_id"], data["application_date"], data["status"], data["resume_version"],
          data["cover_letter_sent"],
          json.dumps(data["interview_data"]) if data["interview_data"] else None,
          application_id))


def delete_application(application_id):
    execute("DELETE FROM applications WHERE application_id = %s", (application_id,))


# -------------------------------------------------------------
# Contacts
# -------------------------------------------------------------

def get_contacts(company_id=None):
    sql = """
        SELECT k.*, c.company_name
        FROM contacts k
        JOIN companies c ON k.company_id = c.company_id
    """
    params = ()
    if company_id is not None:
        sql += " WHERE k.company_id = %s"
        params = (company_id,)
    sql += " ORDER BY c.company_name, k.contact_name"
    return query(sql, params)


def get_contact(contact_id):
    return query("""
        SELECT k.*, c.company_name
        FROM contacts k
        JOIN companies c ON k.company_id = c.company_id
        WHERE k.contact_id = %s
    """, (contact_id,), one=True)


def add_contact(data):
    return execute("""
        INSERT INTO contacts (company_id, contact_name, title, email, phone, linkedin_url, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (data["company_id"], data["contact_name"], data["title"], data["email"],
          data["phone"], data["linkedin_url"], data["notes"]))


def update_contact(contact_id, data):
    execute("""
        UPDATE contacts
        SET company_id = %s, contact_name = %s, title = %s, email = %s,
            phone = %s, linkedin_url = %s, notes = %s
        WHERE contact_id = %s
    """, (data["company_id"], data["contact_name"], data["title"], data["email"],
          data["phone"], data["linkedin_url"], data["notes"], contact_id))


def delete_contact(contact_id):
    execute("DELETE FROM contacts WHERE contact_id = %s", (contact_id,))


# -------------------------------------------------------------
# Dashboard statistics
# -------------------------------------------------------------

def get_dashboard_stats():
    totals = query("""
        SELECT
            (SELECT COUNT(*) FROM companies)    AS companies,
            (SELECT COUNT(*) FROM jobs)         AS jobs,
            (SELECT COUNT(*) FROM applications) AS applications,
            (SELECT COUNT(*) FROM contacts)     AS contacts
    """, one=True)

    status_rows = query("""
        SELECT status, COUNT(*) AS count
        FROM applications
        GROUP BY status
    """)
    by_status = {s: 0 for s in STATUSES}
    for row in status_rows:
        by_status[row["status"]] = row["count"]

    type_rows = query("""
        SELECT job_type, COUNT(*) AS count
        FROM jobs
        GROUP BY job_type
    """)
    by_type = {t: 0 for t in JOB_TYPES}
    for row in type_rows:
        if row["job_type"] in by_type:
            by_type[row["job_type"]] = row["count"]

    salary = query("""
        SELECT AVG(salary_min) AS avg_min, AVG(salary_max) AS avg_max
        FROM jobs
    """, one=True)

    return {
        "totals": totals,
        "by_status": by_status,
        "by_type": by_type,
        "avg_salary_min": salary["avg_min"],
        "avg_salary_max": salary["avg_max"],
    }
