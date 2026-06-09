def create_account(employee):
    username = employee["name"].lower().replace(" ", ".")
    return f"Account Created for {employee['name']} ({username}@company.local)"


def request_laptop(employee):
    return f"Laptop Requested for {employee['department']} department"


def assign_license(employee):
    role = employee["role"].lower()
    license_name = "Analytics Suite" if "analyst" in role else "Developer Suite" if "engineer" in role else "Productivity Suite"
    return f"License Assigned: {license_name}"


def send_welcome_email(employee):
    return f"Welcome Email Sent to {employee['name']}"
