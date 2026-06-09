from datetime import UTC, datetime

from database.db import get_db


def generate_hr_schedule(database_path):
    db = get_db(database_path)
    pending = db.execute(
        """
        SELECT COUNT(*)
        FROM workflow_status
        WHERE overall_status IS NULL OR overall_status != 'Completed'
        """
    ).fetchone()[0]
    high_risk = db.execute("SELECT COUNT(*) FROM pii_reports WHERE risk_level = 'HIGH'").fetchone()[0]
    db.close()

    schedule = [
        ("08:30 AM", "HR Standup Meeting"),
        ("09:30 AM", "New Joiner Review"),
        ("10:30 AM", "Resume Screening"),
        ("12:00 PM", "Interview Round"),
        ("02:00 PM", "Employee Onboarding Check"),
        ("03:30 PM", "Policy Review Meeting"),
        ("05:00 PM", "Report Generation"),
    ]
    if pending:
        schedule.insert(4, ("01:30 PM", f"Pending Onboarding Follow-up ({pending})"))
    if high_risk:
        schedule.insert(5, ("02:30 PM", f"High-risk Document Review ({high_risk})"))
    return [{"time": time, "task": task} for time, task in schedule]


def send_hr_alerts(database_path):
    db = get_db(database_path)
    pending_tasks = db.execute("SELECT COUNT(*) FROM checklists WHERE completed = 0").fetchone()[0]
    pending_onboarding = db.execute(
        "SELECT COUNT(*) FROM workflow_status WHERE overall_status IS NULL OR overall_status != 'Completed'"
    ).fetchone()[0]
    high_risk = db.execute("SELECT COUNT(*) FROM pii_reports WHERE risk_level = 'HIGH'").fetchone()[0]
    db.close()

    alerts = [
        "Meeting starting in 10 minutes: HR Standup Meeting",
        "Interview scheduled now: Resume Screening queue needs review",
    ]
    if pending_tasks:
        alerts.append(f"Pending onboarding tasks: {pending_tasks} checklist items open")
    if pending_onboarding:
        alerts.append(f"Approval required for employee onboarding: {pending_onboarding} pending workflows")
    if high_risk:
        alerts.append(f"High-risk document detected: {high_risk} report needs verification")
    return alerts


def prioritize_hr_tasks(database_path):
    db = get_db(database_path)
    pending = db.execute(
        """
        SELECT e.name, e.role, COALESCE(w.progress_percentage, 0) AS progress
        FROM employees e
        LEFT JOIN workflow_status w ON w.employee_id = e.id
        WHERE COALESCE(w.progress_percentage, 0) < 100
        ORDER BY progress ASC
        LIMIT 5
        """
    ).fetchall()
    risks = db.execute(
        "SELECT file_name, risk_level FROM pii_reports WHERE risk_level IN ('HIGH', 'MEDIUM') ORDER BY created_at DESC LIMIT 5"
    ).fetchall()
    db.close()

    tasks = []
    for report in risks:
        tasks.append({
            "priority": "Critical" if report["risk_level"] == "HIGH" else "High",
            "action": f"Verify {report['risk_level'].lower()} risk document: {report['file_name']}",
        })
    for employee in pending:
        tasks.append({
            "priority": "High" if employee["progress"] < 50 else "Medium",
            "action": f"Complete onboarding approval for {employee['name']} ({employee['progress']}%)",
        })
    if not tasks:
        tasks.append({"priority": "Normal", "action": "Review today's HR schedule and prepare status report"})
    return tasks


def track_hr_activity(database_path):
    db = get_db(database_path)
    employees = db.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
    completed = db.execute("SELECT COUNT(*) FROM workflow_status WHERE overall_status = 'Completed'").fetchone()[0]
    reports = db.execute("SELECT COUNT(*) FROM pii_reports").fetchone()[0]
    db.close()
    return {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "employees_tracked": employees,
        "completed_onboarding": completed,
        "documents_reviewed": reports,
    }
