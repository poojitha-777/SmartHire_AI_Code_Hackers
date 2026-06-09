import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    department TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT NOT NULL,
    employee_id INTEGER,
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

CREATE TABLE IF NOT EXISTS workflow_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL UNIQUE,
    account_created INTEGER DEFAULT 0,
    laptop_requested INTEGER DEFAULT 0,
    license_assigned INTEGER DEFAULT 0,
    welcome_email_sent INTEGER DEFAULT 0,
    overall_status TEXT DEFAULT 'Pending',
    progress_percentage INTEGER DEFAULT 0,
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

CREATE TABLE IF NOT EXISTS workflow_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER,
    file_name TEXT NOT NULL,
    document_type TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

CREATE TABLE IF NOT EXISTS pii_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT NOT NULL,
    rows_processed INTEGER NOT NULL,
    pii_types TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    masked_file TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS checklists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    task TEXT NOT NULL,
    completed INTEGER DEFAULT 0,
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

CREATE TABLE IF NOT EXISTS faq (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS training_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,
    course TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS employee_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER,
    feedback_type TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);
"""

FAQ_SEED = [
    ("What is leave policy?", "Employees receive paid annual leave, sick leave, and public holidays as per HR policy."),
    ("How do I apply leave?", "Apply leave in the HR portal and notify your reporting manager before the planned dates."),
    ("What are office timings?", "Standard office timings are 9:30 AM to 6:30 PM, Monday to Friday."),
    ("What is the dress code?", "Smart casuals are accepted unless your team has a specific client-facing requirement."),
    ("Who should I contact for IT support?", "Contact the IT helpdesk or raise a support ticket from the employee portal."),
    ("What training should I complete?", "Complete security awareness, role onboarding, and department-specific training."),
]

TRAINING_SEED = {
    "Data Analyst": ["Python", "SQL", "Power BI"],
    "AI Engineer": ["Python", "Machine Learning", "Deep Learning", "MLOps"],
    "Software Engineer": ["Git", "Secure Coding", "API Design"],
    "HR Executive": ["HRMS", "Compliance Basics", "Employee Engagement"],
}

USER_SEED = [
    ("hr@smarthire.local", "hr123", "HR", None),
]

EMPLOYEE_SEED = [
    ("Employee 1", "employee1@smarthire.local", "Engineering", "Software Engineer", "2026-01-08T09:00:00+00:00"),
    ("Employee 2", "employee2@smarthire.local", "Data Analytics", "Data Analyst", "2026-02-15T09:00:00+00:00"),
    ("Employee 3", "employee3@smarthire.local", "Operations Support", "Support Specialist", "2026-03-04T09:00:00+00:00"),
    ("Employee 4", "employee4@smarthire.local", "Human Resources", "HR Executive", "2026-04-01T09:00:00+00:00"),
    ("Employee 5", "employee5@smarthire.local", "AI Research", "AI Engineer", "2026-05-20T09:00:00+00:00"),
]

CHECKLIST_SEED = [
    "Complete profile verification",
    "Upload mandatory documents",
    "Finish security awareness training",
    "Meet reporting manager",
    "Review team introduction",
]


def get_db(database_path):
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(database_path):
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    db = get_db(database_path)
    db.executescript(SCHEMA)
    columns = [row["name"] for row in db.execute("PRAGMA table_info(employees)").fetchall()]
    if "email" not in columns:
        db.execute("ALTER TABLE employees ADD COLUMN email TEXT")
    if db.execute("SELECT COUNT(*) FROM faq").fetchone()[0] == 0:
        db.executemany("INSERT INTO faq (question, answer) VALUES (?, ?)", FAQ_SEED)
    if db.execute("SELECT COUNT(*) FROM training_recommendations").fetchone()[0] == 0:
        rows = [(role, course) for role, courses in TRAINING_SEED.items() for course in courses]
        db.executemany("INSERT INTO training_recommendations (role, course) VALUES (?, ?)", rows)
    employee_ids = []
    for name, email, department, role, created_at in EMPLOYEE_SEED:
        employee = db.execute("SELECT id FROM employees WHERE lower(email) = lower(?)", (email,)).fetchone()
        if employee is None:
            cur = db.execute(
                "INSERT INTO employees (name, email, department, role, created_at) VALUES (?, ?, ?, ?, ?)",
                (name, email, department, role, created_at),
            )
            employee_id = cur.lastrowid
        else:
            employee_id = employee["id"]
            db.execute(
                "UPDATE employees SET name = ?, department = ?, role = ? WHERE id = ?",
                (name, department, role, employee_id),
            )
        employee_ids.append(employee_id)
        db.execute(
            """
            INSERT INTO workflow_status
            (employee_id, account_created, laptop_requested, license_assigned, welcome_email_sent, overall_status, progress_percentage)
            VALUES (?, 1, 1, 1, 1, 'Completed', 100)
            ON CONFLICT(employee_id) DO NOTHING
            """,
            (employee_id,),
        )
        if db.execute("SELECT COUNT(*) FROM checklists WHERE employee_id = ?", (employee_id,)).fetchone()[0] == 0:
            db.executemany(
                "INSERT INTO checklists (employee_id, task, completed) VALUES (?, ?, ?)",
                [(employee_id, task, 1 if index < 4 else 0) for index, task in enumerate(CHECKLIST_SEED)],
            )
        db.execute(
            """
            INSERT INTO users (email, password, role, employee_id)
            VALUES (?, 'emp123', 'employee', ?)
            ON CONFLICT(email) DO UPDATE SET role = 'employee', employee_id = excluded.employee_id
            """,
            (email, employee_id),
        )

    user_rows = list(USER_SEED)
    if employee_ids:
        user_rows.append(("employee@smarthire.local", "emp123", "employee", employee_ids[0]))
    for email, password, role, employee_id in user_rows:
        db.execute(
            """
            INSERT INTO users (email, password, role, employee_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET password = excluded.password, role = excluded.role, employee_id = excluded.employee_id
            """,
            (email, password, role, employee_id),
        )
    db.commit()
    db.close()
