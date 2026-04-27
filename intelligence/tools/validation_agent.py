"""
Field-Level Validation Agent (Phase 2)
---------------------------------------
Validates individual field values extracted from a document.
All checks are data-format / logical checks, independent of business policy.
"""

import re
from datetime import date, datetime
from typing import Any, Optional

# ── Helpers ──────────────────────────────────────────────────────────────────

def _find(data: dict, *keys: str) -> Any:
    """Search a (possibly nested) dict for the first key that contains any of
    *keys* as a case-insensitive substring. Returns the value or None."""
    for k, v in data.items():
        for target in keys:
            if target.lower() in k.lower():
                return v
        if isinstance(v, dict):
            result = _find(v, *keys)
            if result is not None:
                return result
    return None


def _parse_number(val) -> Optional[float]:
    """Parse strings like '67,00,000' or '₹50 L' to float."""
    if val is None:
        return None
    s = str(val).replace(",", "").replace("₹", "").replace("Rs", "").strip()
    try:
        return float(s)
    except ValueError:
        m = re.search(r"[\d.]+", s)
        return float(m.group()) if m else None


def _parse_date(val) -> Optional[date]:
    """Try common date formats. Returns a date or None."""
    if not val:
        return None
    s = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", str(val).strip(), flags=re.IGNORECASE)
    for fmt in [
        "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
        "%d %B %Y", "%d %b %Y", "%B %d, %Y",
        "%d %B %y", "%d/%m/%y",
    ]:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    try:
        from dateutil import parser as dp
        return dp.parse(s, dayfirst=True).date()
    except Exception:
        return None


def _age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _check(name: str, value, valid: bool, message: str) -> dict:
    return {
        "check": name,
        "value": str(value) if value is not None else "—",
        "status": "pass" if valid else "fail",
        "message": message,
    }


def _skip(name: str, reason: str) -> dict:
    return {"check": name, "value": "—", "status": "warn", "message": reason}


# ── Main ─────────────────────────────────────────────────────────────────────

def validate_fields(extracted_data: dict) -> dict:
    """
    Run field-level validations on extracted document data.

    Returns
    -------
    dict:
        checks  : list of check result dicts
        summary : {"pass": int, "fail": int, "warn": int}
        status  : "pass" | "fail" | "warn"
        _parsed : typed values passed to the business rules agent
    """
    checks = []

    # Aadhaar
    aadhaar_raw = _find(extracted_data, "aadhaar")
    aadhaar_clean = re.sub(r"[\s\-]", "", str(aadhaar_raw or ""))
    aadhaar_ok = bool(re.fullmatch(r"\d{12}", aadhaar_clean))
    checks.append(_check(
        "Aadhaar Number Format", aadhaar_raw, aadhaar_ok,
        "Valid 12-digit Aadhaar." if aadhaar_ok else f"Expected 12 digits, got: '{aadhaar_raw}'",
    ))

    # PAN
    pan_raw = _find(extracted_data, "pan")
    pan_clean = str(pan_raw or "").strip().upper()
    pan_ok = bool(re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan_clean))
    checks.append(_check(
        "PAN Card Format", pan_raw, pan_ok,
        "Valid PAN format." if pan_ok else f"Expected ABCDE1234F, got: '{pan_raw}'",
    ))

    # Mobile
    mobile_raw = _find(extracted_data, "mobile")
    mobile_clean = re.sub(r"[\s\-+]", "", str(mobile_raw or ""))
    if mobile_clean.startswith("91") and len(mobile_clean) == 12:
        mobile_clean = mobile_clean[2:]
    mobile_ok = bool(re.fullmatch(r"[6-9]\d{9}", mobile_clean))
    checks.append(_check(
        "Mobile Number", mobile_raw, mobile_ok,
        "Valid 10-digit mobile." if mobile_ok else f"Expected 10-digit Indian number, got: '{mobile_raw}'",
    ))

    # Email
    email_raw = _find(extracted_data, "email")
    email_ok = bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", str(email_raw or "")))
    checks.append(_check(
        "Email Address", email_raw, email_ok,
        "Valid email format." if email_ok else f"Invalid email: '{email_raw}'",
    ))

    # Date of Birth
    dob_raw = _find(extracted_data, "dob", "date_of_birth", "birth")
    dob = _parse_date(dob_raw)
    checks.append(_check(
        "Date of Birth Parseable", dob_raw, dob is not None,
        f"Parsed as {dob}." if dob else f"Cannot parse '{dob_raw}' as a date.",
    ))
    age = None
    if dob:
        age = _age(dob)
        age_ok = 18 <= age <= 70
        checks.append(_check(
            "Age at Entry (18–70)", f"{age} yrs", age_ok,
            f"Age {age} is within range." if age_ok else f"Age {age} is outside acceptable range 18–70.",
        ))

    # Gender
    gender_raw = _find(extracted_data, "gender")
    gender_ok = str(gender_raw or "").strip().lower() in ("male", "female", "other", "transgender")
    checks.append(_check(
        "Gender Valid", gender_raw, gender_ok,
        "Recognised gender value." if gender_ok else f"Unrecognised value: '{gender_raw}'",
    ))

    # Pincode
    pin_raw = _find(extracted_data, "pincode", "pin_code", "postal")
    pin_clean = re.sub(r"\s", "", str(pin_raw or ""))
    pin_ok = bool(re.fullmatch(r"[1-9]\d{5}", pin_clean))
    checks.append(_check(
        "Pincode Format", pin_raw, pin_ok,
        "Valid 6-digit pincode." if pin_ok else f"Expected 6-digit pincode, got: '{pin_raw}'",
    ))

    # Sum Assured
    sa_raw = _find(extracted_data, "sum_assured")
    sa = _parse_number(sa_raw)
    sa_ok = sa is not None and sa > 0
    checks.append(_check(
        "Sum Assured Numeric", sa_raw, sa_ok,
        f"Parsed as ₹{sa:,.0f}." if sa_ok else f"Cannot parse sum assured: '{sa_raw}'",
    ))

    # Height
    h_raw = _find(extracted_data, "height")
    h = _parse_number(h_raw)
    h_ok = h is not None and 100 <= h <= 250
    checks.append(_check(
        "Height (cm)", h_raw, h_ok,
        f"{h} cm is plausible." if h_ok else f"Height '{h_raw}' seems invalid.",
    ))

    # Weight
    w_raw = _find(extracted_data, "weight")
    w = _parse_number(w_raw)
    w_ok = w is not None and 20 <= w <= 300
    checks.append(_check(
        "Weight (kg)", w_raw, w_ok,
        f"{w} kg is plausible." if w_ok else f"Weight '{w_raw}' seems invalid.",
    ))

    # Loan Tenure
    tenure_raw = _find(extracted_data, "loan_tenure", "tenure_months", "tenure")
    tenure = _parse_number(tenure_raw)
    tenure_ok = tenure is not None and tenure > 0
    checks.append(_check(
        "Loan Tenure (months)", tenure_raw, tenure_ok,
        f"Loan tenure: {tenure} months." if tenure_ok else f"Cannot parse loan tenure: '{tenure_raw}'",
    ))

    # Summary
    pass_n = sum(1 for c in checks if c["status"] == "pass")
    fail_n = sum(1 for c in checks if c["status"] == "fail")
    warn_n = sum(1 for c in checks if c["status"] == "warn")
    status = "fail" if fail_n > 0 else ("warn" if warn_n > 0 else "pass")

    return {
        "checks": checks,
        "summary": {"pass": pass_n, "fail": fail_n, "warn": warn_n},
        "status": status,
        "_parsed": {
            "dob": dob,
            "age": age,
            "sum_assured": sa,
            "height_cm": h,
            "weight_kg": w,
            "loan_tenure_months": tenure,
        },
    }
