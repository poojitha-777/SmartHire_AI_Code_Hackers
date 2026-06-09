from agents.hr_agent import generate_hr_schedule, prioritize_hr_tasks, send_hr_alerts, track_hr_activity
from database.db import get_db


def perceive_hr_context(database_path):
    db = get_db(database_path)
    context = {
        "employees": db.execute("SELECT COUNT(*) FROM employees").fetchone()[0],
        "pending_onboarding": db.execute(
            "SELECT COUNT(*) FROM workflow_status WHERE overall_status IS NULL OR overall_status != 'Completed'"
        ).fetchone()[0],
        "open_checklist_items": db.execute("SELECT COUNT(*) FROM checklists WHERE completed = 0").fetchone()[0],
        "high_risk_documents": db.execute("SELECT COUNT(*) FROM pii_reports WHERE risk_level = 'HIGH'").fetchone()[0],
    }
    db.close()
    return context


def reason_about_hr_context(context):
    if context["high_risk_documents"]:
        return {
            "intent": "document_risk_review",
            "reason": "High-risk PII reports need immediate HR verification.",
        }
    if context["pending_onboarding"] or context["open_checklist_items"]:
        return {
            "intent": "onboarding_follow_up",
            "reason": "There are pending onboarding workflows or checklist items.",
        }
    return {
        "intent": "daily_hr_planning",
        "reason": "No critical blockers found, so HR can focus on planned activity.",
    }


def act_on_hr_decision(database_path, decision):
    if decision["intent"] == "document_risk_review":
        return prioritize_hr_tasks(database_path)
    if decision["intent"] == "onboarding_follow_up":
        return send_hr_alerts(database_path)
    return generate_hr_schedule(database_path)


def reflect_on_action(context, decision, action):
    return {
        "summary": f"AI loop selected {decision['intent']} because {decision['reason']}",
        "next_best_action": action[0] if action else "Review HR dashboard.",
        "confidence": "High" if context["high_risk_documents"] or context["pending_onboarding"] else "Medium",
    }


def run_hr_ai_loop(database_path):
    context = perceive_hr_context(database_path)
    decision = reason_about_hr_context(context)
    action = act_on_hr_decision(database_path, decision)
    reflection = reflect_on_action(context, decision, action)
    activity = track_hr_activity(database_path)
    return {
        "loop_name": "HR AI Decision Loop",
        "steps": ["Perceive HR context", "Reason about urgency", "Act with HR tools", "Reflect next action"],
        "context": context,
        "decision": decision,
        "action": action,
        "reflection": reflection,
        "activity": activity,
    }
