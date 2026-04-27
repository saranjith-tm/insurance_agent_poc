"""
Business Rules Agent (Phase 3)
--------------------------------
Validates policy-level business rules on extracted and validated data.
All rules are independent of field format; they evaluate business logic.
"""

import re
from typing import Any, Optional

# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_number(val) -> Optional[float]:
    if val is None:
        return None
    s = str(val).replace(",", "").replace("₹", "").replace("Rs", "").strip()
    try:
        return float(s)
    except ValueError:
        m = re.search(r"[\d.]+", s)
        return float(m.group()) if m else None


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", str(name or "").strip().lower())


def _rule(name: str, passed: bool, message: str, severity: str = "error", code: str = None) -> dict:
    status = "pass" if passed else severity
    return {
        "rule": name,
        "code": code or "",
        "status": status,
        "severity": severity,
        "message": message,
    }


def _warn(name: str, message: str) -> dict:
    return {"rule": name, "code": "", "status": "warn", "severity": "warn", "message": message}


# ── Main ─────────────────────────────────────────────────────────────────────

def check_business_rules(extracted_data: dict, parsed_values: dict = None) -> dict:
    """
    Run business rule validations on extracted document data.

    Parameters
    ----------
    extracted_data : dict
        Merged extracted JSON from Phase 1.
    parsed_values : dict, optional
        Pre-parsed typed values from Phase 2 (_parsed key).
        Keys: age, sum_assured, height_cm, weight_kg, loan_tenure_months, dob.

    Returns
    -------
    dict:
        rules   : list of rule result dicts
        summary : {"pass": int, "error": int, "warn": int}
        status  : "pass" | "error" | "warn"
        bmi     : float | None
    """
    pv = parsed_values or {}
    rules = []

    # Resolve values from parsed cache or re-parse raw data
    age = pv.get("age")
    sa = pv.get("sum_assured") or _parse_number(extracted_data.get("sum_assured"))
    h = pv.get("height_cm") or _parse_number(extracted_data.get("height_cm"))
    w = pv.get("weight_kg") or _parse_number(extracted_data.get("weight_kg"))
    loan_tenure = pv.get("loan_tenure_months") or _parse_number(extracted_data.get("loan_tenure"))

    # ── Rule 1: Maximum Insurable Age ≤ 70 ───────────────────────────────────
    if age is not None:
        ok = age <= 70
        rules.append(_rule(
            "Maximum Insurable Age (≤ 70)", ok,
            f"Age {age} is within maximum insurable age of 70." if ok
            else f"Age {age} exceeds maximum insurable age of 70.",
        ))
    else:
        rules.append(_warn("Maximum Insurable Age (≤ 70)", "Date of birth not available — cannot verify age."))

    # ── Rule 2 & 3: Sum Assured vs Loan Amount ───────────────────────────────
    loan_amount = _parse_number(extracted_data.get("loan_amount"))
    if sa is not None and loan_amount is not None:
        ratio = sa / loan_amount
        pct = f"{ratio * 100:.0f}%"
        rules.append(_rule(
            "Sum Assured ≥ 50% of Loan Amount",
            ratio >= 0.5,
            f"Sum Assured is {pct} of Loan Amount — acceptable." if ratio >= 0.5
            else f"Sum Assured ₹{sa:,.0f} is only {pct} of Loan Amount ₹{loan_amount:,.0f} — below 50% minimum.",
            code="SUM_ASSURED_TOO_LOW" if ratio < 0.5 else "",
        ))
        rules.append(_rule(
            "Sum Assured ≤ 120% of Loan Amount",
            ratio <= 1.2,
            f"Sum Assured is {pct} of Loan Amount — within 120% norm." if ratio <= 1.2
            else f"Sum Assured ₹{sa:,.0f} is {pct} of Loan Amount ₹{loan_amount:,.0f} — exceeds 120% norm.",
            code="SUM_ASSURED_EXCEEDS_NORM" if ratio > 1.2 else "",
        ))
    else:
        rules.append(_warn(
            "Sum Assured vs Loan Amount",
            "Loan Amount not found in extracted data — ratio cannot be verified.",
        ))

    # ── Rule 4: Age > 55 AND Sum Assured > ₹50L ──────────────────────────────
    if age is not None and sa is not None:
        breach = age > 55 and sa > 5_000_000
        rules.append(_rule(
            "Age > 55 with SA > ₹50L (Not Allowed)", not breach,
            "Age and Sum Assured combination is acceptable." if not breach
            else f"Age {age} > 55 AND Sum Assured ₹{sa:,.0f} > ₹50L — combination not allowed.",
        ))
    else:
        rules.append(_warn("Age > 55 with SA > ₹50L", "Age or Sum Assured not available."))

    # ── Rule 5: Nominee ≠ Applicant ──────────────────────────────────────────
    applicant_raw = extracted_data.get("master_policy_holder")
    nominee_raw = extracted_data.get("nominee_name")
    if applicant_raw and nominee_raw:
        same = _normalize_name(applicant_raw) == _normalize_name(nominee_raw)
        rules.append(_rule(
            "Nominee ≠ Applicant", not same,
            "Nominee and applicant are different persons." if not same
            else f"Nominee '{nominee_raw}' matches applicant '{applicant_raw}' — not allowed.",
        ))
    else:
        rules.append(_warn("Nominee ≠ Applicant", "Applicant or nominee name not found in extracted data."))

    # ── Rule 6: Moratorium Period < Loan Tenure ───────────────────────────────
    moratorium_raw = extracted_data.get("moratorium_period")
    moratorium = _parse_number(moratorium_raw)
    if moratorium is not None and loan_tenure is not None:
        ok = moratorium < loan_tenure
        rules.append(_rule(
            "Moratorium Period < Loan Tenure", ok,
            f"Moratorium {moratorium:.0f} months < Loan Tenure {loan_tenure:.0f} months — OK." if ok
            else f"Moratorium ({moratorium:.0f} months) must be less than Loan Tenure ({loan_tenure:.0f} months).",
        ))
    else:
        rules.append(_warn("Moratorium Period < Loan Tenure", "Moratorium or loan tenure not available."))

    # ── Rule 7: BMI ≥ 30 AND any DGH = Yes ───────────────────────────────────
    bmi = None
    if h and w and h > 0:
        bmi = w / ((h / 100) ** 2)

    # Check specific history fields from custom model
    health_history_fields = [
        "chronic_disease_history",
        "recent_hospitalization_or_surgery",
        "physical_disability_or_birth_defect",
        "major_disease_history",
        "ongoing_medication_or_tests"
    ]
    
    any_dgh_yes = False
        
    # Check the specific custom history fields
    for field_name in health_history_fields:
        val = extracted_data.get(field_name)
        if val and str(val).lower() in ("yes", "true", "t", "y"):
            any_dgh_yes = True
            break

    if bmi is not None:
        if bmi >= 30 and any_dgh_yes:
            rules.append(_rule(
                "BMI ≥ 30 with Adverse DGH Answer (Not Allowed)", False,
                f"BMI {bmi:.1f} ≥ 30 AND one or more DGH questions answered YES — not allowed.",
            ))
        elif bmi >= 30:
            rules.append(_warn(
                "BMI ≥ 30 (No Adverse DGH)",
                f"BMI {bmi:.1f} ≥ 30 but no adverse DGH answers — review recommended.",
            ))
        else:
            rules.append(_rule(
                "BMI Check", True,
                f"BMI {bmi:.1f} is within acceptable range (< 30).",
                severity="error",
            ))
    else:
        rules.append(_warn("BMI Check", "Height or weight not available — BMI cannot be calculated."))

    # ── Rule 8: PPT Format ────────────────────────────────────────────────────
    ppt_raw = extracted_data.get("premium_paying_term")
    if ppt_raw:
        ppt_str = str(ppt_raw).lower()
        ppt_ok = bool(
            re.search(r"\d+\s*yr", ppt_str) or
            re.search(r"\d+\s*month", ppt_str) or
            re.fullmatch(r"\d+", ppt_str.strip())
        )
        rules.append(_rule(
            "PPT Format (years / monthly)", ppt_ok,
            f"PPT '{ppt_raw}' is in recognised format." if ppt_ok
            else f"PPT '{ppt_raw}' is not in recognised format — expected e.g. '10 yrs' or '120 months'.",
            severity="warn",
        ))
    else:
        rules.append(_warn("PPT Format", "Premium Paying Term not found in extracted data."))

    # ── Summary ───────────────────────────────────────────────────────────────
    pass_n = sum(1 for r in rules if r["status"] == "pass")
    error_n = sum(1 for r in rules if r["status"] == "error")
    warn_n = sum(1 for r in rules if r["status"] == "warn")
    overall = "error" if error_n > 0 else ("warn" if warn_n > 0 else "pass")

    return {
        "rules": rules,
        "summary": {"pass": pass_n, "error": error_n, "warn": warn_n},
        "status": overall,
        "bmi": round(bmi, 1) if bmi else None,
    }

    # ── Summary ───────────────────────────────────────────────────────────────
    pass_n = sum(1 for r in rules if r["status"] == "pass")
    error_n = sum(1 for r in rules if r["status"] == "error")
    warn_n = sum(1 for r in rules if r["status"] == "warn")
    overall = "error" if error_n > 0 else ("warn" if warn_n > 0 else "pass")

    return {
        "rules": rules,
        "summary": {"pass": pass_n, "error": error_n, "warn": warn_n},
        "status": overall,
        "bmi": round(bmi, 1) if bmi else None,
    }
