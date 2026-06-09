import os
import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from functools import wraps

from flask import Flask, flash, redirect, render_template, request, send_file, send_from_directory, session, url_for
from werkzeug.utils import secure_filename

from agents.ai_loop import run_hr_ai_loop
from agents.hr_agent import generate_hr_schedule, prioritize_hr_tasks, send_hr_alerts, track_hr_activity
from agents.onboarding_agent import run_onboarding_agent
from chatbot.employee_chatbot import answer_employee_question
from chatbot.hr_chatbot import answer_question as answer_hr_question
from config import load_env_file
from database.db import get_db, init_db
from tools.pii import detect_and_mask_dataframe
from tools.training import recommendations_for_role

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
MASKED_DIR = BASE_DIR / "masked_files"
REPORT_DIR = BASE_DIR / "reports"

load_env_file(BASE_DIR / ".env")

try:
    import pandas as pd
except ImportError:
    pd = None


ROADMAP_STEPS = [
    ("Day 1", "Profile Setup"),
    ("Day 2", "Document Verification"),
    ("Day 3", "Security Training"),
    ("Day 4", "Team Introduction"),
    ("Day 5", "Project Assignment"),
]

SAMPLE_EMPLOYEES = [
    {
        "name": "Employee 1",
        "employee_id": "EMP-1001",
        "dob": "1998-04-12",
        "department": "Engineering",
        "designation": "Software Engineer",
        "joining_date": "2026-01-08",
        "manager": "Priya Sharma",
        "email": "aarav.mehta@smarthire.local",
        "phone": "+91 98765 43210",
        "skills": ["Python", "API Design", "Secure Coding"],
        "shift": {"name": "Morning Shift", "start": "09:00 AM", "end": "06:00 PM"},
    },
    {
        "name": "Employee 2",
        "employee_id": "EMP-1002",
        "dob": "1997-09-21",
        "department": "Data Analytics",
        "designation": "Data Analyst",
        "joining_date": "2026-02-15",
        "manager": "Rahul Nair",
        "email": "neha.rao@smarthire.local",
        "phone": "+91 91234 56789",
        "skills": ["SQL", "Power BI", "Python"],
        "shift": {"name": "Morning Shift", "start": "09:00 AM", "end": "06:00 PM"},
    },
    {
        "name": "Employee 3",
        "employee_id": "EMP-1003",
        "dob": "1996-11-03",
        "department": "Operations Support",
        "designation": "Support Specialist",
        "joining_date": "2026-03-04",
        "manager": "Ananya Iyer",
        "email": "vikram.singh@smarthire.local",
        "phone": "+91 99887 76655",
        "skills": ["Incident Response", "Customer Support", "SLA Tracking"],
        "shift": {"name": "Night Shift", "start": "09:00 PM", "end": "06:00 AM"},
    },
    {
        "name": "Employee 4",
        "employee_id": "EMP-1004",
        "dob": "1999-01-18",
        "department": "Human Resources",
        "designation": "HR Executive",
        "joining_date": "2026-04-01",
        "manager": "Meera Joshi",
        "email": "riya.kapoor@smarthire.local",
        "phone": "+91 90123 45678",
        "skills": ["HRMS", "Employee Engagement", "Compliance"],
        "shift": {"name": "Morning Shift", "start": "09:00 AM", "end": "06:00 PM"},
    },
    {
        "name": "Employee 5",
        "employee_id": "EMP-1005",
        "dob": "1995-07-29",
        "department": "AI Research",
        "designation": "AI Engineer",
        "joining_date": "2026-05-20",
        "manager": "Dev Malhotra",
        "email": "mohit.jain@smarthire.local",
        "phone": "+91 90909 88776",
        "skills": ["Machine Learning", "Deep Learning", "MLOps"],
        "shift": {"name": "Morning Shift", "start": "09:00 AM", "end": "06:00 PM"},
    },
]


def sample_profile_for_employee(employee):
    if not employee:
        return None
    email = str(employee["email"] or "").lower()
    for profile in SAMPLE_EMPLOYEES:
        if profile["email"].lower() == email:
            return profile
    try:
        index = int(employee["id"]) - 1
    except (TypeError, ValueError):
        index = -1
    return SAMPLE_EMPLOYEES[index] if 0 <= index < len(SAMPLE_EMPLOYEES) else None


def assigned_shift(employee):
    sample = sample_profile_for_employee(employee)
    if sample:
        return sample["shift"]
    role_text = f"{employee['role']} {employee['department']}".lower() if employee else ""
    if any(term in role_text for term in ("night", "support", "operations")):
        return {"name": "Night Shift", "start": "09:00 PM", "end": "06:00 AM"}
    return {"name": "Morning Shift", "start": "09:00 AM", "end": "06:00 PM"}


def attendance_snapshot(employee):
    seed = int(employee["id"]) if employee else 1
    present_days = 18 + (seed % 5)
    absent_days = seed % 3
    total_days = present_days + absent_days
    percentage = round((present_days / total_days) * 100) if total_days else 0
    return {
        "present_days": present_days,
        "absent_days": absent_days,
        "late_entries": seed % 4,
        "percentage": percentage,
        "today_status": "Present" if seed % 4 else "Pending HR Update",
    }


def sentiment_score(text):
    positive = ("good", "great", "excellent", "happy", "helpful", "smooth", "clear")
    negative = ("issue", "delay", "problem", "confusing", "blocked", "risk", "urgent")
    lowered = str(text or "").lower()
    score = 72
    score += sum(4 for word in positive if word in lowered)
    score -= sum(5 for word in negative if word in lowered)
    return max(0, min(100, score))


def attendance_calendar(employee):
    seed = int(employee["id"]) if employee else 1
    days = []
    for day in range(1, 31):
        if day % 7 in (0, 6):
            status = "Off"
        elif (day + seed) % 9 == 0:
            status = "Absent"
        else:
            status = "Present"
        days.append({"day": day, "status": status})
    return days


def employee_documents(onboarding_progress):
    return [
        {"name": "Resume", "status": "Verified"},
        {"name": "Aadhaar", "status": "Verified" if onboarding_progress >= 40 else "Pending"},
        {"name": "PAN", "status": "Verified" if onboarding_progress >= 40 else "Pending"},
        {"name": "Certificates", "status": "Verified" if onboarding_progress >= 70 else "Pending"},
        {"name": "Offer Letter", "status": "Verified"},
        {"name": "ID Card", "status": "Rejected" if onboarding_progress < 30 else "Pending"},
    ]


def employee_dashboard_context(employee, checklist):
    sample = sample_profile_for_employee(employee)
    total_tasks = len(checklist)
    completed_tasks = sum(1 for task in checklist if task["completed"])
    onboarding_progress = int((completed_tasks / total_tasks) * 100) if total_tasks else 0
    learning = recommendations_for_role(employee["role"]) if employee else []
    learning_progress = min(100, max(25, len(learning) * 20)) if learning else 0
    attendance = attendance_snapshot(employee)
    training_completed = min(len(learning), max(1, completed_tasks // 2)) if learning else 0
    training_pending = max(len(learning) - training_completed, 0)
    overall_score = round((attendance["percentage"] + learning_progress + onboarding_progress) / 3)
    feedback_seed = "Onboarding is clear and helpful."
    badges = [
        {"label": "Profile Completed", "earned": bool(employee)},
        {"label": "Documents Verified", "earned": onboarding_progress >= 40},
        {"label": "Training Completed", "earned": onboarding_progress >= 60},
        {"label": "Onboarding Completed", "earned": onboarding_progress == 100},
        {"label": "Security Awareness Certified", "earned": onboarding_progress >= 60},
        {"label": "Team Introduction Completed", "earned": onboarding_progress >= 80},
        {"label": "Perfect Attendance Badge", "earned": attendance["percentage"] >= 95},
        {"label": "Learning Champion Badge", "earned": learning_progress >= 80},
    ]
    skill_list = list(dict.fromkeys((learning[:3] or ["Documentation", "Workflow Tools"]) + ["Communication", "Collaboration"]))
    profile_shift = assigned_shift(employee)
    display_name = sample["name"] if sample else (employee["name"] if employee else "Employee")
    display_id = sample["employee_id"] if sample else (f"EMP-{int(employee['id']):04d}" if employee else "EMP-0000")
    display_skills = sample["skills"] if sample else skill_list
    return {
        "shift": profile_shift,
        "available_shifts": [
            {"name": "Morning Shift", "start": "09:00 AM", "end": "06:00 PM"},
            {"name": "Night Shift", "start": "09:00 PM", "end": "06:00 AM"},
        ],
        "profile": {
            "name": display_name,
            "employee_id": display_id,
            "dob": sample["dob"] if sample else "1998-04-12",
            "department": sample["department"] if sample else (employee["department"] if employee else "People Operations"),
            "designation": sample["designation"] if sample else (employee["role"] if employee else "Employee"),
            "role": employee["role"] if employee else "Employee",
            "joining_date": sample["joining_date"] if sample else (str(employee["created_at"])[:10] if employee else "Not available"),
            "manager": sample["manager"] if sample else "Priya Sharma",
            "email": sample["email"] if sample else (employee["email"] if employee and employee["email"] else "employee@smarthire.local"),
            "phone": sample["phone"] if sample else "+91 98765 43210",
            "skills": display_skills,
            "photo_initials": "".join(part[:1] for part in display_name.split()[:2]).upper(),
            "current_shift": f"{profile_shift['name']} ({profile_shift['start']} - {profile_shift['end']})",
        },
        "attendance": attendance,
        "attendance_calendar": attendance_calendar(employee),
        "learning": learning,
        "learning_progress": learning_progress,
        "announcements": [
            "HR town hall scheduled for Friday at 4:00 PM.",
            "Holiday notice: Office closed for the upcoming public holiday.",
            "Company update: New learning portal is available for all employees.",
        ],
        "events": [
            {"name": "Security Training", "time": "Today, 3:00 PM", "type": "Training"},
            {"name": "Team Sync", "time": "Tomorrow, 11:00 AM", "type": "Meeting"},
            {"name": "Company Connect", "time": "Friday, 4:00 PM", "type": "Event"},
        ],
        "leave_balance": [
            {"type": "Casual Leave", "used": 3, "total": 12},
            {"type": "Sick Leave", "used": 1, "total": 10},
            {"type": "Earned Leave", "used": 4, "total": 18},
        ],
        "leave_requests": [
            {"date": "2026-06-12", "type": "Casual Leave", "status": "Approved"},
            {"date": "2026-06-20", "type": "Earned Leave", "status": "Pending"},
            {"date": "2026-05-28", "type": "Sick Leave", "status": "Rejected"},
        ],
        "documents": employee_documents(onboarding_progress),
        "document_actions": ["View", "Upload", "Replace", "Download"],
        "goals": [
            {"name": "Complete onboarding checklist", "progress": onboarding_progress, "status": "In Progress" if onboarding_progress < 100 else "Completed"},
            {"name": "Finish role readiness training", "progress": learning_progress, "status": "Active"},
            {"name": "Submit required documents", "progress": 75 if onboarding_progress >= 40 else 35, "status": "HR Review"},
        ],
        "training_tracker": {
            "assigned": len(learning),
            "completed": training_completed,
            "pending": training_pending,
        },
        "skills": {
            "technical": learning[:3] or ["Documentation", "Workflow Tools"],
            "soft": ["Communication", "Collaboration", "Ownership"],
            "certifications": ["Security Awareness", "Data Privacy Basics"],
        },
        "career": [
            "Role-specific advanced learning path",
            "Security Awareness certification",
            "Leadership fundamentals for project ownership",
        ],
        "notifications": [
            "New Training Assigned by HR",
            "3 New Notifications",
            "New announcement from HR",
            "Training reminder: Security Training today",
            f"{max(total_tasks - completed_tasks, 0)} pending onboarding tasks",
        ],
        "unread_notifications": 3,
        "productivity": {
            "attendance": attendance["percentage"],
            "training": learning_progress,
            "onboarding": onboarding_progress,
            "overall": overall_score,
        },
        "ai": {
            "sentiment_score": sentiment_score(feedback_seed),
            "smart_recommendation": f"Prioritize {learning[0] if learning else 'Security Awareness'} this week.",
            "risk_prediction": "Low delay risk" if onboarding_progress >= 60 else "Medium delay risk: finish pending documents.",
            "weekly_summary": f"{employee['name'] if employee else 'Employee'} is {onboarding_progress}% through onboarding with {training_pending} pending courses.",
            "insights": ["Learning progress is on track.", "Complete document verification to reduce onboarding risk."],
        },
        "onboarding_progress": onboarding_progress,
        "roadmap": [
            {"day": day, "title": title, "done": index < completed_tasks}
            for index, (day, title) in enumerate(ROADMAP_STEPS)
        ],
        "badges": badges,
        "team": {
            "manager": sample["manager"] if sample else "Priya Sharma",
            "members": [member["name"] for member in SAMPLE_EMPLOYEES if not sample or member["employee_id"] != sample["employee_id"]][:3],
            "department": sample["department"] if sample else (employee["department"] if employee else "People Operations"),
            "contact": "teamdesk@smarthire.local",
        },
    }


def hr_dashboard_context(employees, reports, stats, hr_panel):
    new_joiners = min(stats["employees"], 3)
    completed_tasks = sum(1 for employee in employees if employee["overall_status"] == "Completed")
    pending_tasks = stats["pending"] + stats["high"] + stats["medium"]
    approval_items = [
        {"type": "Document Verification Requests", "count": stats["pending"], "priority": "High"},
        {"type": "Laptop Requests", "count": sum(1 for employee in employees if not employee["laptop_requested"]), "priority": "Medium"},
        {"type": "Account Creation Requests", "count": sum(1 for employee in employees if not employee["account_created"]), "priority": "High"},
        {"type": "Software License Requests", "count": sum(1 for employee in employees if not employee["license_assigned"]), "priority": "Medium"},
        {"type": "Onboarding Approval Requests", "count": stats["pending"], "priority": "High"},
    ]
    departments = {}
    department_status = {}
    for employee in employees:
        departments[employee["department"]] = departments.get(employee["department"], 0) + 1
        status = employee["overall_status"] or "Pending"
        if employee["department"] not in department_status:
            department_status[employee["department"]] = {"Completed": 0, "Pending": 0, "Running": 0}
        department_status[employee["department"]][status if status in department_status[employee["department"]] else "Pending"] += 1
    priorities = {
        "High Priority Tasks": ["Approve onboarding for employee.", "Review high-risk document report."],
        "Medium Priority Tasks": ["Schedule training session.", "Verify laptop provisioning queue."],
        "Low Priority Tasks": ["Update onboarding FAQ.", "Review weekly attendance summary."],
    }
    alert_center = [
        "Meeting starts in 15 minutes",
        "New employee joined",
        "High-risk document detected" if stats["high"] else "No high-risk document detected today",
        "Pending onboarding approval",
        "Missing employee documents",
    ]
    return {
        "alerts": alert_center,
        "approvals": approval_items,
        "departments": departments,
        "priorities": priorities,
        "overview": {
            "meetings": len(hr_panel["schedule"]),
            "pending_approvals": sum(item["count"] for item in approval_items),
            "high_risk_alerts": stats["high"],
            "new_joiners_today": new_joiners,
        },
        "executive_summary": {
            "total_employees": stats["employees"],
            "active_employees": completed_tasks,
            "new_joiners": new_joiners,
            "pending_tasks": pending_tasks,
        },
        "analytics": {
            "new_joiners": new_joiners,
            "attendance": 92,
            "training": 78,
        },
        "department_status": department_status,
        "training_management": {
            "assigned": max(stats["employees"] * 3, 0),
            "completed": max(completed_tasks * 2, 0),
            "pending": max((stats["employees"] * 3) - (completed_tasks * 2), 0),
        },
        "leave": {"pending": 4, "approved": 12, "rejected": 2},
        "attendance_monitoring": {
            "daily_present": max(stats["employees"] - 1, 0),
            "daily_absent": 1 if stats["employees"] else 0,
            "monthly_attendance": 92,
            "absent_employees": [employee["name"] for employee in employees[:2]],
        },
        "engagement": {
            "training_participation": 81,
            "feedback_positive": 74,
            "feedback_neutral": 18,
            "feedback_negative": 8,
        },
        "lifecycle": {
            "Joined": stats["employees"],
            "Onboarding": stats["pending"],
            "Active": completed_tasks,
            "Completed": completed_tasks,
        },
        "compliance": {
            "missing_documents": stats["pending"],
            "pending_verifications": stats["pending"] + stats["medium"],
            "expiring_documents": 2,
        },
        "interviews": [
            {"candidate": "Riya Kapoor", "role": "Data Analyst", "time": "Today, 2:30 PM", "status": "Scheduled"},
            {"candidate": "Mohit Jain", "role": "AI Engineer", "time": "Tomorrow, 10:00 AM", "status": "Panel Pending"},
        ],
        "resources": {
            "laptops": sum(1 for employee in employees if employee["laptop_requested"]),
            "licenses": sum(1 for employee in employees if employee["license_assigned"]),
            "assets_tracked": stats["employees"] * 2,
        },
        "activity_log": [
            "Approved laptop request for onboarding queue.",
            "Reviewed latest PII document report.",
            "Rejected incomplete document verification request.",
            "Sent training deadline reminder.",
        ],
        "efficiency": {
            "pending_tasks": pending_tasks,
            "completed_tasks": completed_tasks,
            "response_time": "2.4 hrs",
            "rating": 86 if pending_tasks else 96,
        },
        "ai": {
            "employee_sentiment": sentiment_score("Feedback is helpful and onboarding is smooth."),
            "smart_recommendations": ["Assign training to pending joiners.", "Review medium-risk PII reports today."],
            "risk_prediction": "Medium onboarding delay risk" if stats["pending"] else "Low onboarding delay risk",
            "weekly_summary": f"{stats['employees']} employees tracked, {stats['completed']} completed onboarding, {stats['pending']} pending.",
            "insights": ["Training participation is trending upward.", "Pending approvals are the largest HR bottleneck."],
        },
        "talent_radar": [
            {"label": "Retention Confidence", "score": 88, "status": "Stable"},
            {"label": "Skill Coverage", "score": 76, "status": "Needs training"},
            {"label": "Onboarding Velocity", "score": 82, "status": "Improving"},
        ],
        "recent_reports": reports[:5],
    }


def read_table(path):
    if pd is not None:
        return pd.read_json(path) if str(path).lower().endswith(".json") else pd.read_csv(path)
    if str(path).lower().endswith(".json"):
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else [data]
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_table(data, path):
    if hasattr(data, "to_csv"):
        data.to_csv(path, index=False)
        return
    rows = list(data)
    fieldnames = list(rows[0].keys()) if rows else []
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def create_app(test_config=None):
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "frontend" / "templates"),
        static_folder=None,
    )
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "smarthire-dev-key"),
        DATABASE=str(BASE_DIR / "database" / "smarthire.db"),
        UPLOAD_FOLDER=str(UPLOAD_DIR),
        MASKED_FOLDER=str(MASKED_DIR),
        REPORT_FOLDER=str(REPORT_DIR),
        TESTING=False,
    )
    if test_config:
        app.config.update(test_config)

    for folder in (
        Path(app.config["UPLOAD_FOLDER"]),
        Path(app.config["MASKED_FOLDER"]),
        Path(app.config["REPORT_FOLDER"]),
        Path(app.config["DATABASE"]).parent,
    ):
        folder.mkdir(parents=True, exist_ok=True)

    @app.route("/static/<path:filename>", endpoint="static")
    def static_files(filename):
        return send_from_directory(BASE_DIR / "frontend" / "static", filename)

    init_db(app.config["DATABASE"])

    def role_required(*roles):
        def decorator(view):
            @wraps(view)
            def wrapped(*args, **kwargs):
                if session.get("role") not in roles:
                    flash("Please sign in with the correct portal.", "error")
                    return redirect(url_for("index"))
                return view(*args, **kwargs)
            return wrapped
        return decorator

    def save_pii_report(filename, source_path):
        df = read_table(source_path)
        masked_df, report = detect_and_mask_dataframe(df, filename)
        masked_name = f"masked_{Path(filename).stem}.csv"
        masked_path = Path(app.config["MASKED_FOLDER"]) / masked_name
        write_table(masked_df, masked_path)
        db = get_db(app.config["DATABASE"])
        cur = db.execute(
            """
            INSERT INTO pii_reports
            (file_name, rows_processed, pii_types, risk_level, masked_file, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                filename,
                report["rows_processed"],
                ", ".join(report["pii_types_found"]) or "None",
                report["risk_level"],
                masked_name,
                report["timestamp"],
            ),
        )
        db.commit()
        db.close()
        return cur.lastrowid

    def authenticate(email, password, expected_role):
        db = get_db(app.config["DATABASE"])
        user = db.execute(
            "SELECT * FROM users WHERE lower(email) = lower(?) AND password = ? AND role = ?",
            (email, password, expected_role),
        ).fetchone()
        db.close()
        if user:
            session["user"] = user["email"]
            session["role"] = user["role"]
            session["employee_id"] = user["employee_id"]
            return True
        return False

    @app.route("/")
    def index():
        return render_template("login.html")

    @app.route("/login")
    def login():
        return render_template("login.html")

    @app.route("/employee-login", methods=["GET", "POST"])
    def employee_login():
        if request.method == "POST":
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "").strip()
            if authenticate(email, password, "employee"):
                return redirect(url_for("employee_dashboard"))
            flash("Invalid employee email or password.", "error")
        return render_template(
            "role_login.html",
            portal="Employee",
            role="employee",
            demo_email="employee1@smarthire.local",
            demo_password="emp123",
            employee_accounts=SAMPLE_EMPLOYEES,
        )

    @app.route("/employee/login", methods=["GET", "POST"])
    def employee_login_legacy():
        return redirect(url_for("employee_login"))

    @app.route("/hr-login", methods=["GET", "POST"])
    def hr_login():
        if request.method == "POST":
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "").strip()
            if authenticate(email, password, "HR"):
                return redirect(url_for("dashboard"))
            flash("Invalid HR email or password.", "error")
        return render_template("role_login.html", portal="HR", role="HR", demo_email="hr@smarthire.local", demo_password="hr123")

    @app.route("/hr/login", methods=["GET", "POST"])
    def hr_login_legacy():
        return redirect(url_for("hr_login"))

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("index"))

    @app.route("/dashboard")
    @app.route("/hr-dashboard")
    @role_required("HR")
    def dashboard():
        db = get_db(app.config["DATABASE"])
        employees = db.execute(
            """
            SELECT e.*, w.account_created, w.laptop_requested, w.license_assigned,
                   w.welcome_email_sent, w.overall_status, w.progress_percentage
            FROM employees e
            LEFT JOIN workflow_status w ON w.employee_id = e.id
            ORDER BY e.created_at DESC
            """
        ).fetchall()
        reports = db.execute("SELECT * FROM pii_reports ORDER BY created_at DESC").fetchall()
        completed = sum(1 for employee in employees if employee["overall_status"] == "Completed")
        stats = {
            "employees": len(employees),
            "completed": completed,
            "pending": max(len(employees) - completed, 0),
            "high": sum(1 for report in reports if report["risk_level"] == "HIGH"),
            "medium": sum(1 for report in reports if report["risk_level"] == "MEDIUM"),
            "low": sum(1 for report in reports if report["risk_level"] == "LOW"),
        }
        hr_panel = {
            "schedule": generate_hr_schedule(app.config["DATABASE"]),
            "alerts": send_hr_alerts(app.config["DATABASE"]),
            "priorities": prioritize_hr_tasks(app.config["DATABASE"]),
            "activity": track_hr_activity(app.config["DATABASE"]),
            "ai_loop": run_hr_ai_loop(app.config["DATABASE"]),
        }
        hr_dashboard = hr_dashboard_context(employees, reports, stats, hr_panel)
        return render_template(
            "dashboard.html",
            employees=employees,
            reports=reports,
            stats=stats,
            hr_panel=hr_panel,
            hr_dashboard=hr_dashboard,
        )

    @app.route("/hr/approval-action", methods=["POST"])
    @role_required("HR")
    def approval_action():
        action = request.form.get("action", "reviewed").title()
        request_type = request.form.get("request_type", "approval request")
        flash(f"{request_type} {action.lower()} by HR.", "success")
        return redirect(url_for("dashboard"))

    @app.route("/hr/communication", methods=["POST"])
    @role_required("HR")
    def hr_communication():
        message_type = request.form.get("message_type", "Notification")
        message = request.form.get("message", "").strip()
        if message:
            flash(f"{message_type} sent to employees.", "success")
        else:
            flash("Add a message before sending HR communication.", "error")
        return redirect(url_for("dashboard"))

    @app.route("/employee/feedback", methods=["POST"])
    @role_required("employee")
    def employee_feedback():
        feedback_type = request.form.get("feedback_type", "feedback")
        message = request.form.get("message", "").strip()
        if message:
            db = get_db(app.config["DATABASE"])
            db.execute(
                """
                INSERT INTO employee_feedback (employee_id, feedback_type, message, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    session.get("employee_id"),
                    feedback_type,
                    message,
                    datetime.now(UTC).isoformat(timespec="seconds"),
                ),
            )
            db.commit()
            db.close()
        flash(f"Your {feedback_type.lower()} was submitted to HR.", "success")
        return redirect(url_for("employee_dashboard"))

    @app.route("/employee/create", methods=["GET", "POST"])
    @role_required("HR")
    def create_employee():
        if request.method == "POST":
            name = request.form["name"].strip()
            email = request.form.get("email", "").strip()
            department = request.form["department"].strip()
            role = request.form["role"].strip()
            db = get_db(app.config["DATABASE"])
            cur = db.execute(
                "INSERT INTO employees (name, email, department, role, created_at) VALUES (?, ?, ?, ?, ?)",
                (name, email, department, role, datetime.now(UTC).isoformat(timespec="seconds")),
            )
            employee_id = cur.lastrowid
            if email:
                db.execute(
                    """
                    INSERT INTO users (email, password, role, employee_id)
                    VALUES (?, ?, 'employee', ?)
                    ON CONFLICT(email) DO UPDATE SET employee_id = excluded.employee_id, role = 'employee'
                    """,
                    (email, "emp123", employee_id),
                )
            db.commit()
            run_onboarding_agent(employee_id, app.config["DATABASE"])
            return redirect(url_for("agent_status", employee_id=employee_id))
        return render_template("employee_create.html")

    @app.route("/agent/run", methods=["POST"])
    @role_required("HR")
    def agent_run():
        employee_id = int(request.form["employee_id"])
        run_onboarding_agent(employee_id, app.config["DATABASE"])
        return redirect(url_for("agent_status", employee_id=employee_id))

    @app.route("/agent/status/<int:employee_id>")
    @role_required("HR")
    def agent_status(employee_id):
        db = get_db(app.config["DATABASE"])
        employee = db.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
        workflow = db.execute("SELECT * FROM workflow_status WHERE employee_id = ?", (employee_id,)).fetchone()
        logs = db.execute(
            "SELECT * FROM workflow_logs WHERE employee_id = ? ORDER BY id",
            (employee_id,),
        ).fetchall()
        checklist = db.execute(
            "SELECT * FROM checklists WHERE employee_id = ? ORDER BY id",
            (employee_id,),
        ).fetchall()
        training = recommendations_for_role(employee["role"]) if employee else []
        return render_template(
            "agent_status.html",
            employee=employee,
            workflow=workflow,
            logs=logs,
            checklist=checklist,
            training=training,
        )

    @app.route("/employee")
    @app.route("/employee-dashboard")
    @role_required("employee")
    def employee_dashboard():
        db = get_db(app.config["DATABASE"])
        if session.get("employee_id"):
            selected = db.execute("SELECT * FROM employees WHERE id = ?", (session["employee_id"],)).fetchone()
        else:
            selected = db.execute("SELECT * FROM employees ORDER BY created_at DESC").fetchone()
        checklist = []
        if selected:
            checklist = db.execute(
                "SELECT * FROM checklists WHERE employee_id = ? ORDER BY id",
                (selected["id"],),
            ).fetchall()
        employee_view = employee_dashboard_context(selected, checklist)
        return render_template(
            "employee_dashboard.html",
            employee=selected,
            checklist=checklist,
            employee_view=employee_view,
        )

    @app.route("/checklist/<int:employee_id>", methods=["GET", "POST"])
    @role_required("employee", "HR")
    def checklist(employee_id):
        if session.get("role") == "employee" and session.get("employee_id") and session.get("employee_id") != employee_id:
            flash("Employees can only access their own checklist.", "error")
            return redirect(url_for("employee_dashboard"))
        db = get_db(app.config["DATABASE"])
        if request.method == "POST":
            completed_ids = set(request.form.getlist("task"))
            tasks = db.execute("SELECT id FROM checklists WHERE employee_id = ?", (employee_id,)).fetchall()
            for task in tasks:
                db.execute(
                    "UPDATE checklists SET completed = ? WHERE id = ?",
                    (1 if str(task["id"]) in completed_ids else 0, task["id"]),
                )
            db.commit()
            flash("Checklist updated.", "success")
        employee = db.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
        tasks = db.execute("SELECT * FROM checklists WHERE employee_id = ? ORDER BY id", (employee_id,)).fetchall()
        done = sum(1 for task in tasks if task["completed"])
        progress = int((done / len(tasks)) * 100) if tasks else 0
        return render_template("checklist.html", employee=employee, tasks=tasks, progress=progress)

    @app.route("/upload", methods=["GET", "POST"])
    @role_required("HR")
    def upload():
        if request.method == "POST":
            file = request.files.get("file")
            if not file or not file.filename:
                flash("Choose a CSV or JSON file.", "error")
                return redirect(url_for("upload"))
            filename = secure_filename(file.filename)
            source_path = Path(app.config["UPLOAD_FOLDER"]) / filename
            file.save(source_path)
            report_id = save_pii_report(filename, source_path)
            return redirect(url_for("pii_result", report_id=report_id))
        return render_template("upload.html")

    @app.route("/reports/sample", methods=["POST"])
    @role_required("HR")
    def create_sample_report():
        filename = "sample_employee_pii.csv"
        source_path = Path(app.config["UPLOAD_FOLDER"]) / filename
        sample_rows = [
            {
                "employee_name": "Aarav Mehta",
                "email": "aarav.mehta@example.com",
                "phone": "9876543210",
                "pan": "ABCDE1234F",
                "aadhaar": "1234 5678 9012",
                "bank_account": "9876543210123456",
                "address": "42 MG Road, Indiranagar, Bengaluru city",
            },
            {
                "employee_name": "Neha Rao",
                "email": "neha.rao@example.com",
                "phone": "+91 9123456789",
                "pan": "FGHIJ5678K",
                "aadhaar": "2345 6789 0123",
                "bank_account": "123456789012",
                "address": "Flat 7, Green Colony, Hyderabad state",
            },
            {
                "employee_name": "Vikram Singh",
                "email": "vikram.singh@example.com",
                "phone": "9988776655",
                "pan": "KLMNO9012P",
                "aadhaar": "3456 7890 1234",
                "bank_account": "456789012345",
                "address": "88 Park Avenue, Delhi district pincode 110001",
            },
        ]
        write_table(sample_rows, source_path)
        report_id = save_pii_report(filename, source_path)
        flash("Sample privacy report created for HR review.", "success")
        return redirect(url_for("pii_result", report_id=report_id))

    @app.route("/reports")
    @role_required("HR")
    def reports():
        db = get_db(app.config["DATABASE"])
        reports = db.execute("SELECT * FROM pii_reports ORDER BY created_at DESC").fetchall()
        return render_template("reports.html", reports=reports)

    @app.route("/reports/<int:report_id>")
    @role_required("HR")
    def pii_result(report_id):
        db = get_db(app.config["DATABASE"])
        report = db.execute("SELECT * FROM pii_reports WHERE id = ?", (report_id,)).fetchone()
        return render_template("pii_result.html", report=report)

    @app.route("/download/<path:filename>")
    @role_required("HR")
    def download(filename):
        return send_file(Path(app.config["MASKED_FOLDER"]) / secure_filename(filename), as_attachment=True)

    @app.route("/chat", methods=["GET", "POST"])
    def chat():
        if session.get("role") == "employee":
            return redirect(url_for("employee_chat"))
        return redirect(url_for("hr_chat"))

    @app.route("/employee/chat", methods=["GET", "POST"])
    @role_required("employee")
    def employee_chat():
        answer = None
        question = ""
        if request.method == "POST":
            question = request.form.get("question", "")
            answer = answer_employee_question(question)
        return render_template("employee_chatbot.html", answer=answer, question=question)

    @app.route("/hr/chat", methods=["GET", "POST"])
    @role_required("HR")
    def hr_chat():
        answer = None
        question = ""
        if request.method == "POST":
            question = request.form.get("question", "")
            answer = answer_hr_question(question, app.config["DATABASE"])
        return render_template("hr_chatbot.html", answer=answer, question=question)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
