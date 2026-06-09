ROLE_RECOMMENDATIONS = {
    "data analyst": ["Python", "SQL", "Power BI"],
    "ai engineer": ["Python", "Machine Learning", "Deep Learning", "MLOps"],
    "software engineer": ["Git", "Secure Coding", "API Design"],
    "hr executive": ["HRMS", "Compliance Basics", "Employee Engagement"],
}


def recommendations_for_role(role):
    return ROLE_RECOMMENDATIONS.get(str(role).lower(), ["Security Awareness", "Company Policies", "Communication Basics"])
