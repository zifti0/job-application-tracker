# AI Usage Documentation

## Tools Used

**Claude (Anthropic)** was my main AI tool for this project. I used it to:

- break the project specification down into a checklist and a schedule that fit my deadline
- generate starter code (schema, Flask routes, database functions, templates), which I then set up, ran, tested and reviewed
- debug setup problems on my Windows machine by sending it screenshots of errors
- draft documentation (the README and this file), which I edited

## Key Prompts

1. **"why did you use ON DELETE CASCADE? wouldn't that delete stuff i might want to keep? what about SET NULL"**
   I learned that `SET NULL` won't work here because `company_id` is `NOT NULL`, and changing that would leave orphaned jobs that the `JOIN` queries would hide. `RESTRICT` would block deleting a company until its jobs and contacts were removed by hand. I kept `CASCADE` because the delete confirmation warns about it, but a soft delete (an `is_archived` flag) would be safer in a real app.
2. **"what if an application has more than one interview round, does interview_data handle that"**
   It doesn't. `interview_data` is a single JSON object, so editing it overwrites the previous interview. Supporting multiple rounds would mean storing a JSON array of interview objects or making a separate `interviews` table.
3. **"walk me through what happens when i click save on the add job form, like step by step to the database"**
   This took me through the whole request: the form POST, server-side validation in `validate_job()`, `json.dumps()` on the skills list, a parameterized `INSERT` and commit, then a redirect to the job's page (the Post/Redirect/Get pattern, so refreshing the page doesn't submit the form twice).
4. **"why does it open a new database connection for every query, isn't that slow"**
   Each connection adds some overhead (a network handshake and a login), and saving a job actually opens two connections. It's fine for a single-user local app, but production code would use a connection pool (`mysql.connector.pooling`) or reuse one connection per request.

## What AI Generated

- **`schema.sql`:** 4 tables with primary and foreign keys (`ON DELETE CASCADE`), ENUM columns, the two required JSON columns (`jobs.requirements` and `applications.interview_data`), and sample data
- **`database.py`:** `query()` and `execute()` helpers with parameterized (`%s`) queries, CRUD functions for each table, JOIN queries, and dashboard aggregates (`COUNT`, `GROUP BY`, `AVG`)
- **`app.py`:** Flask routes for every page, server-side validation, flash messages, and the Job Match function `calculate_matches()`
- **Templates and CSS:** Bootstrap layout, list/detail/form pages, and delete confirmation popups
- **A first draft of the README**

## My Role: Setup, Testing, Review

- **Environment.** I ran `schema.sql` in Workbench and checked the output, created the virtual environment, installed the dependencies, and set up my own `.env` file.
- **Safety check before running the schema.** A `job_tracker` database already existed on my machine. Since the script drops tables, I checked what was in it before running anything. It was empty, so nothing was lost.
- **Testing.** I confirmed the dashboard loaded live data from MySQL. I checked that Job Match ranks "Software Developer" at 100% (3/3) and "Data Analyst" at 67% (2/3, missing Tableau) for `Python, SQL, Flask`, which matches the example in the spec. I also added, edited and deleted a company and confirmed the delete confirmation appeared.
- **Version control.** I committed the project in 9 commits organized by feature instead of one large upload, and I verified with `git status` that `.env` (which has my password) was never committed.
- **Design decisions I reviewed and kept:**
  - **`ON DELETE CASCADE`**, so deleting a company removes its related rows instead of failing on a foreign key error. The confirmation dialog warns about this.
  - **Interview details stored as a JSON object**, as the spec requires.
  - **Database credentials in `.env`**, not hardcoded.

## What Worked Well

- Giving the AI the actual spec meant the schema matched the required column names and types exactly.
- Screenshots of errors worked much better than describing them.
- The generated code handled edge cases I would have missed at first: duplicate or blank skills, case-insensitive matching, minimum salary greater than maximum, and invalid IDs.

## Lessons Learned

- **Specific input gets specific output.** The spec and rubric got far better results than a general prompt would have.
- **The environment was harder than the code.** Every problem I hit was setup: a stopped server, a forgotten password, and a Workbench bug. The AI can't see my machine, so I had to give it exact error messages and screenshots.
- **One step at a time is faster.** Checking each command's output caught problems immediately.
- **Use parameterized queries.** `%s` placeholders, not f-strings, prevent SQL injection.
