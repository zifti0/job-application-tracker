"""
app.py - Flask routes for the Job Application Tracker.

Pages:
    /               Dashboard (statistics overview)
    /companies      Companies  - list / add / view / edit / delete
    /jobs           Jobs       - list / add / view / edit / delete
    /applications   Applications - list / add / view / edit / delete
    /contacts       Contacts   - list / add / edit / delete
    /job-match      Job Match  - rank jobs by how many of your skills they need
"""

import os
import re
from datetime import date

from flask import Flask, abort, flash, redirect, render_template, request, url_for

import database as db

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")  # needed for flash messages

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# -------------------------------------------------------------
# Form / validation helpers
# -------------------------------------------------------------

def field(name):
    """Get a trimmed form value, or None if it was left blank."""
    value = request.form.get(name, "").strip()
    return value or None


def check_max_length(errors, value, label, max_len):
    if value and len(value) > max_len:
        errors.append(f"{label} must be at most {max_len} characters.")


def check_url(errors, value, label):
    if value and not value.lower().startswith(("http://", "https://")):
        errors.append(f"{label} must start with http:// or https://")


def parse_int(errors, value, label):
    if value is None:
        return None
    try:
        number = int(value.replace(",", ""))
    except ValueError:
        errors.append(f"{label} must be a whole number.")
        return None
    if number < 0:
        errors.append(f"{label} cannot be negative.")
    return number


def parse_date(errors, value, label, required=False):
    if value is None:
        if required:
            errors.append(f"{label} is required.")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{label} must be a valid date (YYYY-MM-DD).")
        return None


def parse_skills(text):
    """'Python, SQL , flask' -> ['Python', 'SQL', 'flask'] (no blanks, no duplicates)."""
    skills, seen = [], set()
    for part in (text or "").split(","):
        skill = part.strip()
        if skill and skill.lower() not in seen:
            seen.add(skill.lower())
            skills.append(skill)
    return skills


def validate_company():
    errors = []
    data = {
        "company_name": field("company_name"),
        "industry": field("industry"),
        "website": field("website"),
        "city": field("city"),
        "state": field("state"),
        "notes": field("notes"),
    }
    if not data["company_name"]:
        errors.append("Company name is required.")
    check_max_length(errors, data["company_name"], "Company name", 100)
    check_max_length(errors, data["industry"], "Industry", 50)
    check_max_length(errors, data["website"], "Website", 200)
    check_max_length(errors, data["city"], "City", 50)
    check_max_length(errors, data["state"], "State", 50)
    check_url(errors, data["website"], "Website")
    return data, errors


def validate_job():
    errors = []
    data = {
        "company_id": field("company_id"),
        "job_title": field("job_title"),
        "job_type": field("job_type"),
        "job_url": field("job_url"),
        "requirements": parse_skills(request.form.get("requirements")),
    }
    if not data["company_id"] or not db.get_company(data["company_id"]):
        errors.append("Please choose a company.")
    if not data["job_title"]:
        errors.append("Job title is required.")
    check_max_length(errors, data["job_title"], "Job title", 100)
    if data["job_type"] and data["job_type"] not in db.JOB_TYPES:
        errors.append("Please choose a valid job type.")
    check_max_length(errors, data["job_url"], "Job URL", 300)
    check_url(errors, data["job_url"], "Job URL")
    data["salary_min"] = parse_int(errors, field("salary_min"), "Minimum salary")
    data["salary_max"] = parse_int(errors, field("salary_max"), "Maximum salary")
    if (data["salary_min"] is not None and data["salary_max"] is not None
            and data["salary_min"] > data["salary_max"]):
        errors.append("Minimum salary cannot be greater than maximum salary.")
    data["date_posted"] = parse_date(errors, field("date_posted"), "Date posted")
    return data, errors


def validate_application():
    errors = []
    data = {
        "job_id": field("job_id"),
        "status": field("status") or "Applied",
        "resume_version": field("resume_version"),
        "cover_letter_sent": request.form.get("cover_letter_sent") == "on",
    }
    if not data["job_id"] or not db.get_job(data["job_id"]):
        errors.append("Please choose a job.")
    if data["status"] not in db.STATUSES:
        errors.append("Please choose a valid status.")
    check_max_length(errors, data["resume_version"], "Resume version", 50)
    data["application_date"] = parse_date(errors, field("application_date"),
                                          "Application date", required=True)

    # Interview details are stored together in the interview_data JSON column
    interview = {
        "interview_date": field("interview_date"),
        "interview_type": field("interview_type"),
        "interviewer": field("interviewer"),
        "notes": field("interview_notes"),
    }
    if interview["interview_date"]:
        parse_date(errors, interview["interview_date"], "Interview date")
    # Only keep the keys that were filled in; store NULL if nothing was entered
    data["interview_data"] = {k: v for k, v in interview.items() if v}
    return data, errors


def validate_contact():
    errors = []
    data = {
        "company_id": field("company_id"),
        "contact_name": field("contact_name"),
        "title": field("title"),
        "email": field("email"),
        "phone": field("phone"),
        "linkedin_url": field("linkedin_url"),
        "notes": field("notes"),
    }
    if not data["company_id"] or not db.get_company(data["company_id"]):
        errors.append("Please choose a company.")
    if not data["contact_name"]:
        errors.append("Contact name is required.")
    check_max_length(errors, data["contact_name"], "Contact name", 100)
    check_max_length(errors, data["title"], "Title", 100)
    check_max_length(errors, data["email"], "Email", 100)
    check_max_length(errors, data["phone"], "Phone", 20)
    check_max_length(errors, data["linkedin_url"], "LinkedIn URL", 200)
    if data["email"] and not EMAIL_RE.match(data["email"]):
        errors.append("Email address doesn't look valid.")
    check_url(errors, data["linkedin_url"], "LinkedIn URL")
    return data, errors


@app.context_processor
def inject_active_section():
    """Tell base.html which nav link to highlight (e.g. 'company_edit' -> 'companies')."""
    endpoint = request.endpoint or ""
    sections = [("job_match", "job_match"), ("compan", "companies"), ("job", "jobs"),
                ("application", "applications"), ("contact", "contacts")]
    for prefix, section in sections:
        if endpoint.startswith(prefix):
            return {"active_section": section}
    return {"active_section": "dashboard"}


@app.template_filter("money")
def money(value):
    """45000 -> $45,000 (blank if missing)."""
    return f"${value:,.0f}" if value is not None else ""


def show_errors(errors):
    for error in errors:
        flash(error, "danger")


# -------------------------------------------------------------
# Job Match algorithm
# -------------------------------------------------------------

def calculate_matches(user_skills, jobs):
    """
    For each job, compare its required skills with the user's skills
    (case-insensitive) and compute a match percentage:

        match % = matched required skills / total required skills * 100

    Returns jobs sorted from best to worst match. Jobs with no listed
    requirements are skipped because a percentage can't be computed.
    """
    have = {s.lower() for s in user_skills}
    results = []
    for job in jobs:
        required = job["requirements"] or []
        if not required:
            continue
        matched = [s for s in required if s.lower() in have]
        missing = [s for s in required if s.lower() not in have]
        percent = round(len(matched) / len(required) * 100)
        results.append({
            "job": job,
            "matched": matched,
            "missing": missing,
            "percent": percent,
            "total": len(required),
        })
    # Highest percentage first; ties broken by more matched skills, then title
    results.sort(key=lambda r: (-r["percent"], -len(r["matched"]), r["job"]["job_title"]))
    return results


# -------------------------------------------------------------
# Dashboard
# -------------------------------------------------------------

@app.route("/")
def dashboard():
    stats = db.get_dashboard_stats()
    applications = db.get_applications()

    # Upcoming interviews come from the interview_data JSON column
    today = date.today().isoformat()
    upcoming = [a for a in applications
                if a["interview_data"].get("interview_date", "") >= today]
    upcoming.sort(key=lambda a: a["interview_data"]["interview_date"])

    total_apps = stats["totals"]["applications"]
    responded = total_apps - stats["by_status"]["Applied"] - stats["by_status"]["Withdrawn"]
    active = sum(stats["by_status"][s] for s in ("Applied", "Screening", "Interview"))

    return render_template(
        "dashboard.html",
        stats=stats,
        recent=applications[:5],
        upcoming=upcoming,
        response_rate=round(responded / total_apps * 100) if total_apps else 0,
        active=active,
    )


# -------------------------------------------------------------
# Companies
# -------------------------------------------------------------

@app.route("/companies")
def companies():
    return render_template("companies.html", companies=db.get_companies())


@app.route("/companies/new", methods=["GET", "POST"])
def company_new():
    if request.method == "POST":
        data, errors = validate_company()
        if not errors:
            new_id = db.add_company(data)
            flash(f"Added {data['company_name']}.", "success")
            return redirect(url_for("company_detail", company_id=new_id))
        show_errors(errors)
        return render_template("company_form.html", company=data, mode="Add")
    return render_template("company_form.html", company={}, mode="Add")


@app.route("/companies/<int:company_id>")
def company_detail(company_id):
    company = db.get_company(company_id) or abort(404)
    return render_template("company_detail.html", company=company,
                           jobs=db.get_jobs(company_id=company_id),
                           contacts=db.get_contacts(company_id=company_id))


@app.route("/companies/<int:company_id>/edit", methods=["GET", "POST"])
def company_edit(company_id):
    company = db.get_company(company_id) or abort(404)
    if request.method == "POST":
        data, errors = validate_company()
        if not errors:
            db.update_company(company_id, data)
            flash(f"Updated {data['company_name']}.", "success")
            return redirect(url_for("company_detail", company_id=company_id))
        show_errors(errors)
        data["company_id"] = company_id
        return render_template("company_form.html", company=data, mode="Edit")
    return render_template("company_form.html", company=company, mode="Edit")


@app.route("/companies/<int:company_id>/delete", methods=["POST"])
def company_delete(company_id):
    company = db.get_company(company_id) or abort(404)
    db.delete_company(company_id)
    flash(f"Deleted {company['company_name']} and its jobs, applications, and contacts.", "success")
    return redirect(url_for("companies"))


# -------------------------------------------------------------
# Jobs
# -------------------------------------------------------------

@app.route("/jobs")
def jobs():
    return render_template("jobs.html", jobs=db.get_jobs())


def job_form(job, mode):
    return render_template("job_form.html", job=job, mode=mode,
                           companies=db.get_companies(), job_types=db.JOB_TYPES)


@app.route("/jobs/new", methods=["GET", "POST"])
def job_new():
    if request.method == "POST":
        data, errors = validate_job()
        if not errors:
            new_id = db.add_job(data)
            flash(f"Added job: {data['job_title']}.", "success")
            return redirect(url_for("job_detail", job_id=new_id))
        show_errors(errors)
        return job_form(data, "Add")
    # Allow "Add job" links from a company page to preselect the company
    return job_form({"company_id": request.args.get("company_id"), "requirements": []}, "Add")


@app.route("/jobs/<int:job_id>")
def job_detail(job_id):
    job = db.get_job(job_id) or abort(404)
    return render_template("job_detail.html", job=job,
                           applications=db.get_applications(job_id=job_id))


@app.route("/jobs/<int:job_id>/edit", methods=["GET", "POST"])
def job_edit(job_id):
    job = db.get_job(job_id) or abort(404)
    if request.method == "POST":
        data, errors = validate_job()
        if not errors:
            db.update_job(job_id, data)
            flash(f"Updated job: {data['job_title']}.", "success")
            return redirect(url_for("job_detail", job_id=job_id))
        show_errors(errors)
        data["job_id"] = job_id
        return job_form(data, "Edit")
    return job_form(job, "Edit")


@app.route("/jobs/<int:job_id>/delete", methods=["POST"])
def job_delete(job_id):
    job = db.get_job(job_id) or abort(404)
    db.delete_job(job_id)
    flash(f"Deleted job: {job['job_title']} (and its applications).", "success")
    return redirect(url_for("jobs"))


# -------------------------------------------------------------
# Applications
# -------------------------------------------------------------

@app.route("/applications")
def applications():
    status = request.args.get("status")
    if status not in db.STATUSES:
        status = None
    return render_template("applications.html",
                           applications=db.get_applications(status=status),
                           statuses=db.STATUSES, current_status=status)


def application_form(application, mode):
    return render_template("application_form.html", application=application, mode=mode,
                           jobs=db.get_jobs(), statuses=db.STATUSES,
                           interview_types=["Phone", "Video", "Technical", "Behavioral", "Onsite"])


@app.route("/applications/new", methods=["GET", "POST"])
def application_new():
    if request.method == "POST":
        data, errors = validate_application()
        if not errors:
            new_id = db.add_application(data)
            flash("Application added.", "success")
            return redirect(url_for("application_detail", application_id=new_id))
        show_errors(errors)
        return application_form(data, "Add")
    return application_form({
        "job_id": request.args.get("job_id"),
        "application_date": date.today().isoformat(),
        "status": "Applied",
        "interview_data": {},
    }, "Add")


@app.route("/applications/<int:application_id>")
def application_detail(application_id):
    application = db.get_application(application_id) or abort(404)
    return render_template("application_detail.html", application=application)


@app.route("/applications/<int:application_id>/edit", methods=["GET", "POST"])
def application_edit(application_id):
    application = db.get_application(application_id) or abort(404)
    if request.method == "POST":
        data, errors = validate_application()
        if not errors:
            db.update_application(application_id, data)
            flash("Application updated.", "success")
            return redirect(url_for("application_detail", application_id=application_id))
        show_errors(errors)
        data["application_id"] = application_id
        return application_form(data, "Edit")
    return application_form(application, "Edit")


@app.route("/applications/<int:application_id>/delete", methods=["POST"])
def application_delete(application_id):
    db.get_application(application_id) or abort(404)
    db.delete_application(application_id)
    flash("Application deleted.", "success")
    return redirect(url_for("applications"))


# -------------------------------------------------------------
# Contacts
# -------------------------------------------------------------

@app.route("/contacts")
def contacts():
    return render_template("contacts.html", contacts=db.get_contacts())


def contact_form(contact, mode):
    return render_template("contact_form.html", contact=contact, mode=mode,
                           companies=db.get_companies())


@app.route("/contacts/new", methods=["GET", "POST"])
def contact_new():
    if request.method == "POST":
        data, errors = validate_contact()
        if not errors:
            db.add_contact(data)
            flash(f"Added contact: {data['contact_name']}.", "success")
            return redirect(url_for("contacts"))
        show_errors(errors)
        return contact_form(data, "Add")
    return contact_form({"company_id": request.args.get("company_id")}, "Add")


@app.route("/contacts/<int:contact_id>/edit", methods=["GET", "POST"])
def contact_edit(contact_id):
    contact = db.get_contact(contact_id) or abort(404)
    if request.method == "POST":
        data, errors = validate_contact()
        if not errors:
            db.update_contact(contact_id, data)
            flash(f"Updated contact: {data['contact_name']}.", "success")
            return redirect(url_for("contacts"))
        show_errors(errors)
        data["contact_id"] = contact_id
        return contact_form(data, "Edit")
    return contact_form(contact, "Edit")


@app.route("/contacts/<int:contact_id>/delete", methods=["POST"])
def contact_delete(contact_id):
    contact = db.get_contact(contact_id) or abort(404)
    db.delete_contact(contact_id)
    flash(f"Deleted contact: {contact['contact_name']}.", "success")
    return redirect(url_for("contacts"))


# -------------------------------------------------------------
# Job Match
# -------------------------------------------------------------

@app.route("/job-match")
def job_match():
    skills_text = request.args.get("skills", "")
    skills = parse_skills(skills_text)
    results = calculate_matches(skills, db.get_jobs()) if skills else None
    return render_template("job_match.html", skills_text=skills_text,
                           skills=skills, results=results)


# -------------------------------------------------------------
# Error pages
# -------------------------------------------------------------

@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
