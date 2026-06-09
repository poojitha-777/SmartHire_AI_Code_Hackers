# Flow Diagram

```text
New Employee Created
  -> create_account()
  -> request_laptop()
  -> assign_license()
  -> send_welcome_email()
  -> update workflow_status
  -> create onboarding checklist

Upload File
  -> Read CSV/JSON with Pandas
  -> Detect columns and values
  -> Regex scan
  -> Identify PII
  -> Mask data
  -> Store report
  -> Download masked CSV

User Question
  -> Employee portal: FAQ JSON search
  -> Employee answer found: return onboarding support
  -> Employee answer not found: Gemini fallback when API key exists

HR Question
  -> HR management intent detection
  -> Schedule, alerts, priority, status, or document answer
  -> Policy FAQ search
  -> Not found: Gemini fallback when API key exists

HR Agent Layer
  -> generate_hr_schedule()
  -> send_hr_alerts()
  -> prioritize_hr_tasks()
  -> track_hr_activity()
```
