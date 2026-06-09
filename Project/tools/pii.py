import re
from datetime import UTC, datetime

PII_PATTERNS = {
    "Email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "Phone Number": re.compile(r"(?<!\d)(?:\+91[-\s]?)?[6-9]\d{9}(?!\d)"),
    "PAN Number": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
    "Aadhaar Number": re.compile(r"(?<!\d)\d{4}\s?\d{4}\s?\d{4}(?!\d)"),
    "Bank Account Number": re.compile(r"(?<!\d)\d{9,18}(?!\d)"),
    "Address": re.compile(r"\b(?:street|road|avenue|nagar|colony|layout|apartment|flat|city|district|state|pincode)\b", re.I),
}


def mask_email(value):
    text = str(value)
    user, domain = text.split("@", 1)
    return f"{user[:1]}****@{domain}"


def mask_phone(value):
    digits = re.sub(r"\D", "", str(value))
    return f"XXXXXX{digits[-4:]}"


def mask_pan(value):
    text = str(value).upper()
    return f"{text[:5]}****{text[-1:]}"


def mask_aadhaar(value):
    digits = re.sub(r"\D", "", str(value))
    return f"XXXXXXXX{digits[-4:]}"


def mask_bank(value):
    digits = re.sub(r"\D", "", str(value))
    return f"{'X' * max(len(digits) - 4, 4)}{digits[-4:]}"


def mask_address(value):
    text = str(value)
    return text[:8] + "..." if len(text) > 8 else "REDACTED"


MASKERS = {
    "Email": mask_email,
    "Phone Number": mask_phone,
    "PAN Number": mask_pan,
    "Aadhaar Number": mask_aadhaar,
    "Bank Account Number": mask_bank,
    "Address": mask_address,
}


def detect_value(value):
    text = str(value)
    if not text or text.lower() == "nan":
        return []
    detected = []
    for pii_type, pattern in PII_PATTERNS.items():
        if pattern.search(text):
            detected.append(pii_type)
    if "Aadhaar Number" in detected and "Bank Account Number" in detected:
        detected.remove("Bank Account Number")
    return detected


def detect_and_mask_dataframe(df, file_name):
    if isinstance(df, list):
        return detect_and_mask_records(df, file_name)

    masked = df.copy()
    pii_types = set()

    for column in masked.columns:
        for index, value in masked[column].items():
            detected = detect_value(value)
            if not detected:
                continue
            pii_type = detected[0]
            pii_types.update(detected)
            masked.at[index, column] = MASKERS[pii_type](value)

    risk_level = "LOW"
    if len(pii_types) >= 3:
        risk_level = "HIGH"
    elif pii_types:
        risk_level = "MEDIUM"

    report = {
        "file_name": file_name,
        "rows_processed": int(len(df)),
        "pii_types_found": sorted(pii_types),
        "risk_level": risk_level,
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    return masked, report


def detect_and_mask_records(records, file_name):
    masked = [dict(row) for row in records]
    pii_types = set()

    for row in masked:
        for column, value in row.items():
            detected = detect_value(value)
            if not detected:
                continue
            pii_type = detected[0]
            pii_types.update(detected)
            row[column] = MASKERS[pii_type](value)

    risk_level = "LOW"
    if len(pii_types) >= 3:
        risk_level = "HIGH"
    elif pii_types:
        risk_level = "MEDIUM"

    report = {
        "file_name": file_name,
        "rows_processed": int(len(records)),
        "pii_types_found": sorted(pii_types),
        "risk_level": risk_level,
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    return masked, report
