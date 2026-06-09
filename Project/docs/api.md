# API Documentation

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/login` | Portal selector for Employee and HR login |
| POST | `/employee/login` | Employee email/password login |
| POST | `/hr/login` | HR email/password login |
| POST | `/employee/create` | Create employee and run onboarding agent |
| POST | `/agent/run` | Rerun onboarding agent |
| POST | `/upload` | Upload CSV/JSON and generate masked file |
| POST | `/employee/chat` | Ask Employee AI Assistant |
| POST | `/hr/chat` | Ask HR AI Assistant for status, schedule, alerts, priorities, or policy |
| GET | `/dashboard` | HR dashboard |
| GET | `/reports` | PII reports list |
