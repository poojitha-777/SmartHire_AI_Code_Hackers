from datetime import UTC, datetime

from database.db import get_db
from tools.onboarding_tools import assign_license, create_account, request_laptop, send_welcome_email

CHECKLIST_TASKS = [
    "Upload Resume",
    "Upload Aadhaar",
    "Upload PAN",
    "Complete Security Training",
    "Meet Reporting Manager",
    "Setup Company Email",
]


def _log(db, employee_id, message):
    db.execute(
        "INSERT INTO workflow_logs (employee_id, message, created_at) VALUES (?, ?, ?)",
        (employee_id, message, datetime.now(UTC).isoformat(timespec="seconds")),
    )


def run_onboarding_agent(employee_id, database_path):
    db = get_db(database_path)
    employee = db.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
    if not employee:
        db.close()
        raise ValueError(f"Employee {employee_id} not found")

    db.execute("DELETE FROM workflow_logs WHERE employee_id = ?", (employee_id,))
    db.execute(
        """
        INSERT INTO workflow_status (employee_id) VALUES (?)
        ON CONFLICT(employee_id) DO UPDATE SET
            account_created = 0,
            laptop_requested = 0,
            license_assigned = 0,
            welcome_email_sent = 0,
            overall_status = 'Running',
            progress_percentage = 0
        """,
        (employee_id,),
    )
    db.commit()

    tools = [
        ("account_created", create_account),
        ("laptop_requested", request_laptop),
        ("license_assigned", assign_license),
        ("welcome_email_sent", send_welcome_email),
    ]

    completed = 0
    for column, tool in tools:
        result = tool(employee)
        completed += 1
        progress = int((completed / len(tools)) * 100)
        db.execute(
            f"UPDATE workflow_status SET {column} = 1, progress_percentage = ?, overall_status = ? WHERE employee_id = ?",
            (progress, "Completed" if progress == 100 else "Running", employee_id),
        )
        _log(db, employee_id, result)
        db.commit()

    existing = db.execute("SELECT COUNT(*) FROM checklists WHERE employee_id = ?", (employee_id,)).fetchone()[0]
    if existing == 0:
        db.executemany(
            "INSERT INTO checklists (employee_id, task, completed) VALUES (?, ?, 0)",
            [(employee_id, task) for task in CHECKLIST_TASKS],
        )
    _log(db, employee_id, "Workflow Completed")
    db.commit()
    db.close()
