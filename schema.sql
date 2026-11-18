-- =============================================================
-- Job Application Tracker - database creation script
-- Run this whole file in MySQL Workbench (or the mysql CLI).
-- WARNING: it drops and recreates the job_tracker tables.
-- =============================================================

CREATE DATABASE IF NOT EXISTS job_tracker
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE job_tracker;

-- Drop child tables first so foreign keys don't block the drop
DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS contacts;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS companies;

-- -------------------------------------------------------------
-- companies
-- -------------------------------------------------------------
CREATE TABLE companies (
    company_id   INT PRIMARY KEY AUTO_INCREMENT,
    company_name VARCHAR(100) NOT NULL,
    industry     VARCHAR(50),
    website      VARCHAR(200),
    city         VARCHAR(50),
    state        VARCHAR(50),
    notes        TEXT,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- -------------------------------------------------------------
-- jobs  (each job belongs to one company)
-- requirements is a JSON array of skills, e.g. ["Python", "SQL"]
-- -------------------------------------------------------------
CREATE TABLE jobs (
    job_id       INT PRIMARY KEY AUTO_INCREMENT,
    company_id   INT NOT NULL,
    job_title    VARCHAR(100) NOT NULL,
    job_type     ENUM('Full-time', 'Part-time', 'Contract', 'Internship'),
    salary_min   INT,
    salary_max   INT,
    job_url      VARCHAR(300),
    date_posted  DATE,
    requirements JSON,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_jobs_company
        FOREIGN KEY (company_id) REFERENCES companies(company_id)
        ON DELETE CASCADE
);

-- -------------------------------------------------------------
-- applications  (each application is for one job)
-- interview_data is a JSON object, e.g.
--   {"interview_date": "2026-11-20", "interview_type": "Technical",
--    "interviewer": "Jane Doe", "notes": "LeetCode medium"}
-- -------------------------------------------------------------
CREATE TABLE applications (
    application_id    INT PRIMARY KEY AUTO_INCREMENT,
    job_id            INT NOT NULL,
    application_date  DATE NOT NULL,
    status            ENUM('Applied', 'Screening', 'Interview', 'Offer', 'Rejected', 'Withdrawn')
                      DEFAULT 'Applied',
    resume_version    VARCHAR(50),
    cover_letter_sent BOOLEAN DEFAULT FALSE,
    interview_data    JSON,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_applications_job
        FOREIGN KEY (job_id) REFERENCES jobs(job_id)
        ON DELETE CASCADE
);

-- -------------------------------------------------------------
-- contacts  (people you know at a company)
-- -------------------------------------------------------------
CREATE TABLE contacts (
    contact_id   INT PRIMARY KEY AUTO_INCREMENT,
    company_id   INT NOT NULL,
    contact_name VARCHAR(100) NOT NULL,
    title        VARCHAR(100),
    email        VARCHAR(100),
    phone        VARCHAR(20),
    linkedin_url VARCHAR(200),
    notes        TEXT,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_contacts_company
        FOREIGN KEY (company_id) REFERENCES companies(company_id)
        ON DELETE CASCADE
);

-- -------------------------------------------------------------
-- Indexes (from Assignment 3) to speed up common lookups
-- Foreign key columns are indexed automatically by MySQL.
-- -------------------------------------------------------------
CREATE INDEX idx_job_title        ON jobs(job_title);
CREATE INDEX idx_salary           ON jobs(salary_min);
CREATE INDEX idx_company_type     ON jobs(company_id, job_type);
CREATE INDEX idx_app_status       ON applications(status);
CREATE INDEX idx_company_industry ON companies(industry);

-- =============================================================
-- Sample data (fictional companies and people)
-- =============================================================

INSERT INTO companies (company_name, industry, website, city, state, notes) VALUES
('TechCorp',        'Software',      'https://techcorp.example.com',  'Miami',         'FL', 'Strong new-grad program.'),
('DataCo',          'Analytics',     'https://dataco.example.com',    'Orlando',       'FL', 'Mostly hybrid roles.'),
('CloudNine Systems','Cloud',        'https://cloudnine.example.com', 'Austin',        'TX', NULL),
('GreenLeaf Health','Healthcare',    'https://greenleaf.example.com', 'Tampa',         'FL', 'Met a recruiter at the career fair.'),
('Byte Bank',       'Finance',       'https://bytebank.example.com',  'New York',      'NY', 'Fintech, fast interview process.'),
('PixelForge',      'Gaming',        'https://pixelforge.example.com','San Francisco', 'CA', NULL);

INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max, job_url, date_posted, requirements) VALUES
(1, 'Software Developer',        'Full-time',  85000, 105000, 'https://techcorp.example.com/careers/1',  '2026-10-01', '["Python", "SQL", "Flask"]'),
(1, 'Software Engineer Intern',  'Internship', 30000,  40000, 'https://techcorp.example.com/careers/2',  '2026-10-10', '["Python", "Git", "Data Structures"]'),
(2, 'Data Analyst',              'Full-time',  70000,  85000, 'https://dataco.example.com/jobs/7',       '2026-09-25', '["Python", "SQL", "Tableau"]'),
(3, 'Cloud Engineer',            'Full-time',  95000, 125000, 'https://cloudnine.example.com/jobs/3',    '2026-10-15', '["AWS", "Docker", "Linux", "Python"]'),
(3, 'DevOps Intern',             'Internship', 28000,  35000, 'https://cloudnine.example.com/jobs/9',    '2026-11-01', '["Linux", "Git", "Docker"]'),
(4, 'Backend Developer',         'Contract',   60000,  80000, 'https://greenleaf.example.com/jobs/12',   '2026-10-20', '["Java", "Spring", "SQL"]'),
(5, 'Full Stack Engineer',       'Full-time',  100000, 130000,'https://bytebank.example.com/careers/44', '2026-11-05', '["JavaScript", "React", "Python", "SQL"]'),
(6, 'Game Tools Programmer',     'Part-time',  40000,  55000, 'https://pixelforge.example.com/jobs/2',   '2026-10-28', '["C++", "Python", "Git"]');

INSERT INTO applications (job_id, application_date, status, resume_version, cover_letter_sent, interview_data) VALUES
(1, '2026-10-05', 'Interview', 'v3-backend',  TRUE,  '{"interview_date": "2026-11-20", "interview_type": "Technical", "interviewer": "Alex Rivera", "notes": "Two LeetCode mediums + Flask questions"}'),
(2, '2026-10-12', 'Screening', 'v3-general',  FALSE, NULL),
(3, '2026-09-28', 'Rejected',  'v2-data',     TRUE,  NULL),
(4, '2026-10-18', 'Applied',   'v3-backend',  FALSE, NULL),
(5, '2026-11-03', 'Applied',   'v3-general',  TRUE,  NULL),
(7, '2026-11-06', 'Offer',     'v3-backend',  TRUE,  '{"interview_date": "2026-11-12", "interview_type": "Onsite", "interviewer": "Priya Shah", "notes": "Final round went well"}'),
(8, '2026-10-30', 'Withdrawn', 'v1',          FALSE, NULL);

INSERT INTO contacts (company_id, contact_name, title, email, phone, linkedin_url, notes) VALUES
(1, 'Alex Rivera',  'Engineering Manager', 'alex.rivera@techcorp.example.com', '305-555-0101', 'https://www.linkedin.com/in/alex-rivera-example', 'Interviewer for the developer role.'),
(1, 'Maria Lopez',  'Campus Recruiter',    'maria.lopez@techcorp.example.com', '305-555-0102', NULL, 'Met at the FIU career fair.'),
(2, 'Kevin Chen',   'Data Team Lead',      'kchen@dataco.example.com',         NULL,           NULL, NULL),
(4, 'Sam Patel',    'Technical Recruiter', 'spatel@greenleaf.example.com',     '813-555-0144', NULL, 'Follow up after Thanksgiving.'),
(5, 'Priya Shah',   'Senior Engineer',     'priya@bytebank.example.com',       NULL,           'https://www.linkedin.com/in/priya-shah-example', 'Did the onsite interview.'),
(6, 'Jordan Blake', 'HR Coordinator',      'jblake@pixelforge.example.com',    '415-555-0190', NULL, NULL);
