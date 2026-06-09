# SmartHire AI Test Cases

This document lists functional, role-based, and data-protection test cases for the SmartHire AI Flask project.

## Test Environment

- Application: SmartHire AI - Secure Employee Onboarding Concierge
- Framework: Flask
- Database: SQLite
- Test command: `py -m pytest`
- Local URL: `http://127.0.0.1:5000`
- HR credentials: `hr@smarthire.local` / `hr123`
- Employee credentials: `employee@smarthire.local` / `emp123`

## Automated Test Coverage

Run:

```bash
py -m pytest
```

Expected result:

```text
All tests pass.
```

Current automated areas include login routing, role guards, employee creation, onboarding workflow logs, PII detection, masking helpers, chatbot responses, HR AI loop, upload handling, and sample report generation.

## Functional Test Cases

| Test Case ID | Module | Scenario | Test Steps | Expected Result | Priority |
| --- | --- | --- | --- | --- | --- |
| TC-001 | Landing Page | Verify landing page shows only role login options | 1. Open `/`.<br>2. Check visible options. | Page shows `Login as HR` and `Login as Employee`. PII Detector or dashboard links are not directly exposed. | High |
| TC-002 | HR Login | Verify valid HR login redirects to HR dashboard | 1. Open `/hr-login`.<br>2. Enter valid HR credentials.<br>3. Submit form. | User is redirected to `/hr-dashboard` or `/dashboard`. HR sidebar and dashboard are visible. | High |
| TC-003 | Employee Login | Verify valid employee login redirects to employee dashboard | 1. Open `/employee-login`.<br>2. Enter valid employee credentials.<br>3. Submit form. | User is redirected to `/employee-dashboard` or `/employee`. Employee workspace is visible. | High |
| TC-004 | Authentication | Verify invalid login is rejected | 1. Open `/hr-login` or `/employee-login`.<br>2. Enter invalid email/password.<br>3. Submit form. | User remains on login page and an error/flash message is shown. | High |
| TC-005 | Role Guard | Verify employee cannot access HR dashboard | 1. Login as employee.<br>2. Navigate to `/hr-dashboard`. | Request is redirected to `/`; HR dashboard is not shown. | High |
| TC-006 | Logout | Verify logout clears session | 1. Login as HR or employee.<br>2. Click Logout.<br>3. Try to open a protected page. | User is returned to landing/login page and protected page access is blocked. | High |
| TC-007 | HR Dashboard | Verify dashboard loads HR analytics | 1. Login as HR.<br>2. Open `/dashboard`. | HR dashboard displays employee stats, onboarding progress, risk dashboard, attendance monitoring, and HR widgets. | Medium |
| TC-008 | Employee Dashboard | Verify employee dashboard loads employee modules once | 1. Login as employee.<br>2. Open `/employee-dashboard`.<br>3. Inspect navigation and profile area. | Dashboard, Attendance, Shift Details, Learning, Goals, Roadmap, Documents, Team, Achievements, Feedback, Notifications, and AI Assistant appear once in the main sidebar. Profile appears through the top avatar drawer, not as a duplicate main card. | High |
| TC-009 | Profile Drawer | Verify employee profile drawer opens | 1. Login as employee.<br>2. Click the top avatar/profile button. | Profile drawer opens and shows employee ID, DOB, department, designation, joining date, manager, email, phone, shift, and skills. | Medium |
| TC-010 | Notification Drawer | Verify notification drawer opens | 1. Login as employee.<br>2. Click the notification/bell button. | Notification drawer opens with unread notifications and HR communication items. | Medium |

## Employee Onboarding Test Cases

| Test Case ID | Module | Scenario | Test Steps | Expected Result | Priority |
| --- | --- | --- | --- | --- | --- |
| TC-011 | Employee Creation | Verify HR can create employee | 1. Login as HR.<br>2. Open `/employee/create`.<br>3. Enter name, email, department, and role.<br>4. Submit. | Employee is created and user is redirected. Database stores the employee. | High |
| TC-012 | Agent Workflow | Verify onboarding agent runs after employee creation | 1. Create a new employee.<br>2. Open agent status page for that employee. | Workflow status is `Completed`, progress is `100%`, and workflow logs include onboarding steps. | High |
| TC-013 | Agent Rerun | Verify HR can rerun onboarding workflow | 1. Login as HR.<br>2. Submit `/agent/run` for an employee. | Workflow runs again and status/logs are updated. | Medium |
| TC-014 | Checklist | Verify employee checklist opens | 1. Login as employee or HR.<br>2. Open `/checklist/<employee_id>`. | Checklist page loads with onboarding tasks. | Medium |
| TC-015 | Checklist Update | Verify checklist task status can be updated | 1. Open checklist page.<br>2. Mark a task complete.<br>3. Submit. | Task status is saved and progress reflects the updated state. | Medium |

## PII Detection and Reporting Test Cases

| Test Case ID | Module | Scenario | Test Steps | Expected Result | Priority |
| --- | --- | --- | --- | --- | --- |
| TC-016 | PII Upload | Verify HR can upload CSV with PII | 1. Login as HR.<br>2. Open `/upload`.<br>3. Upload CSV with email, phone, PAN, and Aadhaar.<br>4. Submit. | Upload succeeds, PII scan runs, masked file is generated, and report is stored. | High |
| TC-017 | PII Masking | Verify email masking | 1. Scan `pooji@gmail.com`. | Output is masked as `p****@gmail.com`. | High |
| TC-018 | PII Masking | Verify phone masking | 1. Scan `6369875736`. | Output is masked as `XXXXXX5736`. | High |
| TC-019 | PII Masking | Verify PAN masking | 1. Scan `ABCDE1234F`. | Output is masked as `ABCDE****F`. | High |
| TC-020 | PII Masking | Verify Aadhaar masking | 1. Scan `123456789012`. | Output is masked as `XXXXXXXX9012`. | High |
| TC-021 | Risk Report | Verify high-risk report creation | 1. Upload file containing multiple PII values.<br>2. Open `/reports`. | Report appears with correct file name, rows processed, and risk level `HIGH`. | High |
| TC-022 | Report Details | Verify report detail page | 1. Login as HR.<br>2. Open `/reports/<report_id>`. | Report detail page displays scan summary, detected PII, risk level, and download option. | Medium |
| TC-023 | Masked Download | Verify masked file download | 1. Open a report detail page.<br>2. Click/download masked output. | Masked file downloads successfully and does not expose raw PII values. | High |
| TC-024 | Sample Report | Verify HR can create sample privacy report | 1. Login as HR.<br>2. Submit `/reports/sample`. | Sample report is created with file name `sample_employee_pii.csv`, 3 rows processed, and risk level `HIGH`. | Medium |

## Chatbot and AI Assistant Test Cases

| Test Case ID | Module | Scenario | Test Steps | Expected Result | Priority |
| --- | --- | --- | --- | --- | --- |
| TC-025 | Employee AI Assistant | Verify employee FAQ response | 1. Login as employee.<br>2. Open `/employee/chat`.<br>3. Ask `What is leave policy?`. | Assistant responds with leave policy information, including paid annual leave. | High |
| TC-026 | Employee AI Assistant | Verify first-day onboarding question | 1. Login as employee.<br>2. Ask `What should I do on my first day?`. | Assistant returns onboarding guidance from FAQ or fallback. | Medium |
| TC-027 | HR AI Assistant | Verify HR schedule generation | 1. Login as HR.<br>2. Open `/hr/chat`.<br>3. Ask `Generate today's HR schedule`. | Response includes `HR Standup Meeting` or schedule items. | High |
| TC-028 | HR AI Assistant | Verify HR task prioritization | 1. Login as HR.<br>2. Ask `Prioritize critical HR tasks`. | Response includes critical priorities or review tasks. | High |
| TC-029 | HR AI Loop | Verify HR AI decision loop response | 1. Login as HR.<br>2. Ask `Run HR AI loop`. | Response includes `HR AI Decision Loop` with perceive, reason, act, and reflect behavior. | High |
| TC-030 | Gemini Fallback | Verify unknown chatbot question fallback | 1. Configure `GEMINI_API_KEY`.<br>2. Ask a question not covered by FAQ/rules. | Assistant returns a fallback Gemini-generated answer. If key is missing, app should handle gracefully. | Low |

## Employee Workspace Test Cases

| Test Case ID | Module | Scenario | Test Steps | Expected Result | Priority |
| --- | --- | --- | --- | --- | --- |
| TC-031 | Attendance | Verify attendance module display | 1. Login as employee.<br>2. Click Attendance. | Attendance percentage, present days, absent days, late entries, today status, and monthly calendar are visible. | Medium |
| TC-032 | Shift Details | Verify shift module display | 1. Login as employee.<br>2. Click Shift Details. | Assigned shift and available shifts are visible. Active shift is highlighted. | Medium |
| TC-033 | Learning | Verify learning recommendations | 1. Login as employee.<br>2. Click Learning Recommendations. | Recommended courses, assigned courses, completed courses, pending courses, and progress are visible. | Medium |
| TC-034 | Goals | Verify employee goals | 1. Login as employee.<br>2. Click Employee Goals. | Goal names, statuses, and progress bars are visible. | Medium |
| TC-035 | Roadmap | Verify employee roadmap | 1. Login as employee.<br>2. Click Employee Roadmap. | Roadmap steps are shown with completed steps marked. | Medium |
| TC-036 | Documents | Verify document center | 1. Login as employee.<br>2. Click Document Center. | Document list, verification status, and employee access are visible. | Medium |
| TC-037 | Team Introduction | Verify team section | 1. Login as employee.<br>2. Click Team Introduction. | Reporting manager, department, and team member cards are visible. | Medium |
| TC-038 | Achievement Bucket | Verify achievement badges | 1. Login as employee.<br>2. Click Achievement Bucket. | Earned and pending achievement badges are displayed. | Low |
| TC-039 | Feedback | Verify employee can submit feedback | 1. Login as employee.<br>2. Open Feedback & Suggestions.<br>3. Enter message and submit. | Feedback is submitted to HR and success confirmation appears. | Medium |

## Negative and Edge Test Cases

| Test Case ID | Module | Scenario | Test Steps | Expected Result | Priority |
| --- | --- | --- | --- | --- | --- |
| TC-040 | Upload Validation | Upload unsupported file type | 1. Login as HR.<br>2. Upload unsupported file format. | Upload is rejected or handled with a clear error message. | Medium |
| TC-041 | Upload Validation | Upload empty CSV | 1. Login as HR.<br>2. Upload an empty CSV file. | App handles the file safely and shows validation feedback. | Medium |
| TC-042 | Reports | Access invalid report ID | 1. Login as HR.<br>2. Open `/reports/999999`. | App returns a safe not-found response or redirect without crashing. | Medium |
| TC-043 | Checklist | Access invalid employee checklist | 1. Login as HR or employee.<br>2. Open `/checklist/999999`. | App handles missing employee safely. | Medium |
| TC-044 | Security | Direct download path traversal attempt | 1. Try to open `/download/../app.py`. | App must not expose files outside the allowed masked/report folders. | High |
| TC-045 | Session Security | Access protected route without login | 1. Open `/dashboard`, `/employee-dashboard`, `/upload`, or `/reports` without session. | User is redirected to landing/login page. | High |

## Exit Criteria

- All high-priority test cases pass.
- `py -m pytest` passes successfully.
- No protected HR page is accessible from an employee session.
- Uploaded PII is masked before download.
- Employee dashboard does not show duplicate navigation/profile sections.
- Chatbot features respond without application errors.
