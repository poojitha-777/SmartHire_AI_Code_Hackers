from agents.ai_loop import run_hr_ai_loop
from agents.hr_agent import generate_hr_schedule, prioritize_hr_tasks, send_hr_alerts, track_hr_activity
from chatbot.common import gemini_answer
from database.db import get_db


def _faq_answer(question, database_path):
    db = get_db(database_path)
    rows = db.execute("SELECT question, answer FROM faq").fetchall()
    db.close()
    normalized = question.lower().strip()
    for row in rows:
        faq_question = row["question"].lower()
        if normalized == faq_question or any(word in faq_question for word in normalized.split() if len(word) > 3):
            return row["answer"]
    return None


def _employee_status(database_path):
    db = get_db(database_path)
    rows = db.execute(
        """
        SELECT e.name, e.role, COALESCE(w.overall_status, 'Pending') AS status,
               COALESCE(w.progress_percentage, 0) AS progress
        FROM employees e
        LEFT JOIN workflow_status w ON w.employee_id = e.id
        ORDER BY e.created_at DESC
        LIMIT 5
        """
    ).fetchall()
    db.close()
    if not rows:
        return "No employee onboarding records are available yet."
    return "\n".join(f"{row['name']} ({row['role']}): {row['status']} at {row['progress']}%" for row in rows)


def _document_status(database_path):
    db = get_db(database_path)
    rows = db.execute("SELECT file_name, risk_level, pii_types FROM pii_reports ORDER BY created_at DESC LIMIT 5").fetchall()
    db.close()
    if not rows:
        return "No document verification reports are available yet."
    return "\n".join(f"{row['file_name']}: {row['risk_level']} risk, detected {row['pii_types']}" for row in rows)


def _format_schedule(database_path):
    return "\n".join(f"{item['time']} -> {item['task']}" for item in generate_hr_schedule(database_path))


def _format_alerts(database_path):
    return "\n".join(f"- {alert}" for alert in send_hr_alerts(database_path))


def _format_priorities(database_path):
    return "\n".join(f"{item['priority']}: {item['action']}" for item in prioritize_hr_tasks(database_path))


def _format_ai_loop(database_path):
    loop = run_hr_ai_loop(database_path)
    steps = "\n".join(f"- {step}" for step in loop["steps"])
    return (
        f"{loop['loop_name']}\n"
        f"{steps}\n"
        f"Decision: {loop['decision']['intent']}\n"
        f"Reason: {loop['decision']['reason']}\n"
        f"Next best action: {loop['reflection']['next_best_action']}\n"
        f"Confidence: {loop['reflection']['confidence']}"
    )


def answer_question(question, database_path):
    question = question.strip()
    if not question:
        return "Please ask about onboarding status, policy, documents, schedule, alerts, or HR priorities."

    normalized = question.lower()
    if any(word in normalized for word in ["schedule", "timetable", "calendar", "day plan"]):
        return _format_schedule(database_path)
    if any(word in normalized for word in ["alert", "reminder", "urgent"]):
        return _format_alerts(database_path)
    if any(word in normalized for word in ["priority", "prioritize", "next best", "critical"]):
        return _format_priorities(database_path)
    if "ai loop" in normalized or "decision loop" in normalized or "agent loop" in normalized:
        return _format_ai_loop(database_path)
    if "document" in normalized or "verification" in normalized or "risk" in normalized:
        return _document_status(database_path)
    if "status" in normalized or "onboarding" in normalized or "employee" in normalized:
        return _employee_status(database_path)
    if "activity" in normalized:
        activity = track_hr_activity(database_path)
        return (
            f"Tracked at {activity['timestamp']}: {activity['employees_tracked']} employees, "
            f"{activity['completed_onboarding']} completed onboardings, "
            f"{activity['documents_reviewed']} document reports."
        )

    return _faq_answer(question, database_path) or gemini_answer(
        question,
        "You are the HR AI Assistant for SmartHire AI. Focus on HR management, scheduling, alerts, document verification, onboarding status, and decision support.",
    )
