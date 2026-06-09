# SmartHire AI - Secure Employee Onboarding Concierge

SmartHire AI is a runnable Flask prototype for the AI Prototype Challenge. It automates employee onboarding, tracks workflow progress, detects and masks personal information, recommends training, and provides an HR chatbot with FAQ-first answers and optional Gemini fallback.

## Features

- AI onboarding agent orchestration using Python tool functions.
- Dual login portals for employees and HR with role-based routing.
- Independent Employee AI Assistant and HR AI Assistant.
- HR agent layer for daily schedules, live alerts, task prioritization, and activity tracking.
- Compulsory AI loop integration: HR AI Decision Loop with perceive, reason, act, and reflect steps.
- SQLite persistence for employees, workflow status, checklists, reports, FAQ, and training recommendations.
- CSV/JSON PII detector using Pandas and Regex.
- Masking for email, phone, PAN, Aadhaar, bank account numbers, and address-like values.
- HR dashboard, employee dashboard, checklist, upload, report, download, and chatbot pages.
- Pytest tests for login, employee creation, agent workflow, PII detection, masking, chatbot, and database insert.

## Installation

```bash
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
```

On Windows, you can also run `setup.bat`.

Optional Gemini fallback:

```bash
set GEMINI_API_KEY=your_api_key_here
```

## Run

```bash
py app.py
```

Open `http://127.0.0.1:5000`.

On Windows, you can also run `run.bat`.

Demo credentials:

- HR portal: `hr@smarthire.local` / `hr123`
- Employee portal: `employee@smarthire.local` / `emp123`

## Test

```bash
py -m pytest
```

## Project Structure

```text
SmartHire-AI/
  app.py
  requirements.txt
  README.md
  agents/
  chatbot/
  database/
  docs/
  frontend/
    templates/
    static/
  masked_files/
  reports/
  tests/
  tools/
  uploads/
```

## API Documentation

- `POST /login` authenticates a local demo HR user.
- `POST /employee/login` authenticates employee users and redirects to the employee dashboard.
- `POST /hr/login` authenticates HR users and redirects to the HR dashboard.
- `POST /employee/create` creates an employee and runs onboarding.
- `POST /agent/run` reruns the onboarding workflow for an employee.
- `POST /upload` uploads CSV/JSON, scans PII, masks data, and stores a report.
- `POST /employee/chat` answers onboarding support questions from FAQ JSON or Gemini fallback.
- `POST /hr/chat` answers HR management questions, schedules, alerts, priorities, status, documents, or Gemini fallback.
- `GET /dashboard` shows HR analytics and onboarding progress.
- `GET /reports` lists PII scan reports.

## Demo Script

1. Login with any username and password.
2. Enter the HR portal and show today's AI-generated HR schedule, alerts, and priorities.
3. Create a new employee: Poojitha, AI & DS, Data Analyst.
4. Open the agent status page and show logs for account creation, laptop request, license assignment, welcome email, and completion.
5. Upload a CSV containing email, phone, PAN, and Aadhaar values.
6. Review the risk report and download the masked CSV.
7. Ask the HR assistant: `Generate today's HR schedule`.
8. Log out, enter the employee portal, and ask the Employee Assistant: `What should I do on my first day?`

## AI Usage Note

The employee onboarding agent is deterministic and demonstrates tool orchestration through Python functions. The HR agent layer generates schedules, alerts, priorities, and activity summaries from current SQLite data. The Employee AI Assistant checks `chatbot/employee_faq.json` first. The HR AI Assistant uses HR-specific rules first. If `GEMINI_API_KEY` is set, unknown questions are sent to Gemini.
