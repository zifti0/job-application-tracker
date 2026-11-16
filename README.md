# Job Application Tracker

A full-stack web app for tracking job applications. You can keep companies, job postings, applications and contacts in one place, and use the **Job Match** feature to rank saved jobs by how well they fit your skills.

**Stack:** MySQL · Python 3 + Flask · HTML/CSS (Bootstrap 5 from a CDN)

## Features

- **Dashboard:** totals, applications by status, response rate, average salary range, upcoming interviews and recent applications
- **Full CRUD on all 4 tables:** companies, jobs, applications and contacts, with list views, detail views, add/edit forms and delete-with-confirmation
- **Validation** on both sides. The browser checks required fields, URLs and emails, and the server checks lengths, URL and email format, salary min ≤ max, valid dates and valid ENUM values.
- **JSON columns:**
  - `jobs.requirements` stores the required skills as a JSON array
  - `applications.interview_data` stores the interview details as a JSON object
- **Job Match:** type in your skills and see every job ranked by match percentage, along with which skills you have and which you're missing

## Database design

```
companies 1 ──< jobs 1 ──< applications
companies 1 ──< contacts
```

| Table | Key columns | Foreign key |
|---|---|---|
| `companies` | company_id (PK), company_name | none |
| `jobs` | job_id (PK), job_title, job_type ENUM, salary_min/max, requirements JSON | company_id → companies |
| `applications` | application_id (PK), application_date, status ENUM, interview_data JSON | job_id → jobs |
| `contacts` | contact_id (PK), contact_name, email, phone | company_id → companies |

All foreign keys use `ON DELETE CASCADE`. Deleting a company also removes its jobs, contacts and those jobs' applications, and the delete confirmation warns you about this.

## Setup (Windows)

### 1. Prerequisites
- **Python 3.10+.** Check with `python --version`.
- **MySQL Server 8.x**, running. MySQL Workbench is useful but is only a client, so the server has to be installed too. In Workbench, the "Local instance MySQL80" connection should open without errors.

### 2. Clone and install
```bash
git clone <this-repo-url>
cd job_tracker
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
(macOS/Linux: `source venv/bin/activate`)

### 3. Create the database
**Option A: MySQL Workbench.** Open your local connection, then go to *File → Open SQL Script…* and pick `schema.sql`. Click the lightning-bolt ⚡ button to run the whole script.

**Option B: command line**
```bash
mysql -u root -p < schema.sql
```

This creates the `job_tracker` database, the 4 tables and some sample data.
⚠️ Re-running `schema.sql` drops and recreates the tables, which resets the data.

### 4. Configure your MySQL password
```bash
copy .env.example .env
```
(macOS/Linux: `cp .env.example .env`)

Open `.env` and set `DB_PASSWORD` to your MySQL root password. You can also change `DB_USER`, `DB_HOST` or `DB_PORT` if yours are different.

### 5. Run
```bash
python app.py
```
Open **http://127.0.0.1:5000** in your browser.

## Troubleshooting

| Error | Fix |
|---|---|
| `Access denied for user 'root'@'localhost'` | The password in `.env` is wrong, or `.env` doesn't exist yet (step 4). |
| `Unknown database 'job_tracker'` | Run `schema.sql` (step 3). |
| `Can't connect to MySQL server on 'localhost'` | The MySQL server isn't running. Open *Services* on Windows and start **MySQL80**. |
| `ModuleNotFoundError: No module named 'flask'` | Activate the venv (`venv\Scripts\activate`) and run `pip install -r requirements.txt`. |

## Project structure

```
job_tracker/
├── app.py               # Flask routes, form validation, Job Match algorithm
├── database.py          # MySQL connection + all SQL queries
├── schema.sql           # Creates the database, tables, and sample data
├── requirements.txt     # Python dependencies
├── .env.example         # Template for your local DB settings (copy to .env)
├── templates/           # Jinja2 HTML templates
│   ├── base.html        # Shared layout + navbar
│   ├── _macros.html     # Reusable pieces (status badges, delete buttons…)
│   ├── dashboard.html
│   ├── companies.html, company_form.html, company_detail.html
│   ├── jobs.html, job_form.html, job_detail.html
│   ├── applications.html, application_form.html, application_detail.html
│   ├── contacts.html, contact_form.html
│   ├── job_match.html
│   └── 404.html
├── static/
│   └── style.css
├── AI_USAGE.md          # How GenAI tools were used
└── README.md
```

## How Job Match works

1. The user's skills are split on commas, trimmed and de-duplicated.
2. For each job, the skills listed in its `requirements` JSON are compared with the user's skills. The comparison ignores upper/lower case.
3. The match percentage is `matched skills / required skills × 100`.
4. Jobs are sorted by match % (highest first). Ties go to the job with more matched skills.
5. Each result shows the skills you have in green and the ones you're missing in red.

Example: with the skills `Python, SQL, Flask`, *Software Developer at TechCorp* is a 100% match (3/3), and *Data Analyst at DataCo* is 67% (2/3, missing Tableau).
