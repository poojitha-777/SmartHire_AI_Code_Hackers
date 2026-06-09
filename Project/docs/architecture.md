# Architecture Diagram

```text
Browser UI
   |
   v
Flask Routes in app.py
   |------------------ Employee + Agent Workflow
   |                         |
   |                         v
   |                  agents/onboarding_agent.py
   |                         |
   |                         v
   |                  tools/onboarding_tools.py
   |
   |------------------ PII Upload + Masking
   |                         |
   |                         v
   |                  tools/pii.py + Pandas + Regex
   |
   |------------------ HR Chatbot
                             |
                             v
                      FAQ SQLite Search
                             |
                             v
                      Gemini API fallback

All modules persist operational data in SQLite through database/db.py.
```
