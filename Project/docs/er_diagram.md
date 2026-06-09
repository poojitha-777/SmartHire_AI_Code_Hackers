# Database ER Diagram

```text
employees 1---1 workflow_status
employees 1---N workflow_logs
employees 1---N documents
employees 1---N checklists

pii_reports stores upload scan outputs.
faq stores chatbot knowledge base.
training_recommendations stores role-to-course mappings.
```
