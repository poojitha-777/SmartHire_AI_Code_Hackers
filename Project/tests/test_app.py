import io

from app import create_app
from agents.ai_loop import run_hr_ai_loop
from database.db import get_db
from tools.pii import detect_and_mask_dataframe, mask_aadhaar, mask_email, mask_pan, mask_phone


def make_app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "test.db"),
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
            "MASKED_FOLDER": str(tmp_path / "masked"),
            "REPORT_FOLDER": str(tmp_path / "reports"),
        }
    )


def login_hr(client):
    return client.post("/hr-login", data={"email": "hr@smarthire.local", "password": "hr123"})


def login_employee(client):
    return client.post("/employee-login", data={"email": "employee@smarthire.local", "password": "emp123"})


def test_landing_page_has_only_login_options(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Login as HR" in response.data
    assert b"Login as Employee" in response.data
    assert b"PII Detector" not in response.data


def test_dual_login_redirects_by_role(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    response = login_hr(client)
    assert "/hr-dashboard" in response.location or "/dashboard" in response.location
    client.get("/logout")
    response = login_employee(client)
    assert "/employee-dashboard" in response.location or "/employee" in response.location


def test_role_guard_blocks_employee_from_hr_dashboard(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    login_employee(client)
    response = client.get("/hr-dashboard")
    assert response.status_code == 302
    assert response.location == "/"


def test_employee_creation_runs_agent(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    login_hr(client)
    response = client.post(
        "/employee/create",
        data={
            "name": "Poojitha",
            "email": "poojitha@company.local",
            "department": "AI & DS",
            "role": "Data Analyst",
        },
    )
    assert response.status_code == 302
    db = get_db(app.config["DATABASE"])
    workflow = db.execute("SELECT * FROM workflow_status").fetchone()
    logs = db.execute("SELECT COUNT(*) FROM workflow_logs").fetchone()[0]
    db.close()
    assert workflow["overall_status"] == "Completed"
    assert workflow["progress_percentage"] == 100
    assert logs >= 5


def test_pii_detection_and_masking():
    df = [{
        "Name": "Poojitha",
        "Email": "pooji@gmail.com",
        "Phone": "6369875736",
        "PAN": "ABCDE1234F",
        "Aadhaar": "123456789012",
    }]
    masked, report = detect_and_mask_dataframe(df, "sample.csv")
    assert masked[0]["Email"] == "p****@gmail.com"
    assert masked[0]["Phone"] == "XXXXXX5736"
    assert masked[0]["PAN"] == "ABCDE****F"
    assert masked[0]["Aadhaar"] == "XXXXXXXX9012"
    assert report["risk_level"] == "HIGH"


def test_masking_helpers():
    assert mask_email("pooji@gmail.com") == "p****@gmail.com"
    assert mask_phone("6369875736") == "XXXXXX5736"
    assert mask_pan("ABCDE1234F") == "ABCDE****F"
    assert mask_aadhaar("123456789012") == "XXXXXXXX9012"


def test_employee_chatbot_faq(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    login_employee(client)
    response = client.post("/employee/chat", data={"question": "What is leave policy?"})
    assert response.status_code == 200
    assert b"paid annual leave" in response.data


def test_hr_chatbot_schedule_and_priorities(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    login_hr(client)
    response = client.post("/hr/chat", data={"question": "Generate today's HR schedule"})
    assert response.status_code == 200
    assert b"HR Standup Meeting" in response.data
    response = client.post("/hr/chat", data={"question": "Prioritize critical HR tasks"})
    assert response.status_code == 200
    assert b"Review today" in response.data or b"Critical" in response.data
    response = client.post("/hr/chat", data={"question": "Run HR AI loop"})
    assert response.status_code == 200
    assert b"HR AI Decision Loop" in response.data


def test_hr_ai_loop_runs(tmp_path):
    app = make_app(tmp_path)
    loop = run_hr_ai_loop(app.config["DATABASE"])
    assert loop["loop_name"] == "HR AI Decision Loop"
    assert loop["steps"] == ["Perceive HR context", "Reason about urgency", "Act with HR tools", "Reflect next action"]
    assert "next_best_action" in loop["reflection"]


def test_upload_creates_report(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    login_hr(client)
    data = {
        "file": (
            io.BytesIO(b"Name,Email,Phone,PAN,Aadhaar\nPoojitha,pooji@gmail.com,6369875736,ABCDE1234F,123456789012\n"),
            "sample.csv",
        )
    }
    response = client.post("/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 302
    db = get_db(app.config["DATABASE"])
    report = db.execute("SELECT * FROM pii_reports").fetchone()
    db.close()
    assert report["rows_processed"] == 1
    assert report["risk_level"] == "HIGH"


def test_hr_can_create_sample_privacy_report(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    login_hr(client)
    response = client.post("/reports/sample")
    assert response.status_code == 302
    db = get_db(app.config["DATABASE"])
    report = db.execute("SELECT * FROM pii_reports WHERE file_name = ?", ("sample_employee_pii.csv",)).fetchone()
    db.close()
    assert report["rows_processed"] == 3
    assert report["risk_level"] == "HIGH"
