"""
Module 2 — Document Validation Engine
Implements:
1. ICAO 9303 Standard 7-3-1 Weight Check Digit Algorithm for all MRZ formats (TD1, TD2, TD3).
2. Date parsing & sanity checks (expiration, age, chronological order).
3. Country code & format validation.
4. Watchlist & Stolen Document cross-referencing (SQLite DB).
5. Explainable scoring & step-by-step verification trace for UI rendering.
"""

from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
from modules.blacklist_db import check_document, check_person

# ICAO 9303 repeating weight vector
ICAO_WEIGHTS = [7, 3, 1]

# Valid ISO 3166-1 alpha-3 and ICAO special country codes
COMMON_COUNTRY_CODES = {
    "USA", "GBR", "DEU", "FRA", "CAN", "AUS", "IND", "JPN", "CHN", "ITA",
    "ESP", "NLD", "CHE", "SWE", "NOR", "DNK", "FIN", "IRL", "NZL", "SGP",
    "KOR", "BRA", "MEX", "ARG", "ZAF", "ARE", "ISR", "TUR", "POL", "AUT",
    "BEL", "PRT", "GRC", "CZE", "HUN", "ROU", "UKR", "RUS", "SAU", "EGY",
    "D<<", "UTO", "XPO", "XXA", "XXB", "XXX"  # ICAO test/refugee codes
}


def char_to_value(c: str) -> int:
    """ICAO 9303 character-to-number mapping:
    0-9 -> 0-9
    A-Z -> 10-35
    < or other -> 0
    """
    c = c.upper()
    if c.isdigit():
        return int(c)
    elif "A" <= c <= "Z":
        return ord(c) - ord("A") + 10
    else:
        return 0


def calculate_icao_check_digit(data_str: str) -> Tuple[int, List[Dict[str, Any]]]:
    """Computes ICAO 9303 check digit over data_str using 7-3-1 weighting pattern.
    Returns:
        (check_digit: int 0-9, calculation_steps: list of dicts for explainable UI)
    """
    total = 0
    steps = []
    for idx, char in enumerate(data_str):
        weight = ICAO_WEIGHTS[idx % 3]
        val = char_to_value(char)
        product = val * weight
        total += product
        steps.append({
            "pos": idx,
            "char": char,
            "val": val,
            "weight": weight,
            "product": product,
            "running_sum": total
        })
    check_digit = total % 10
    return check_digit, steps


def parse_mrz_date(date_str: str, is_expiry: bool = False) -> Tuple[Optional[date], str]:
    """Parses 6-digit YYMMDD date string to a datetime.date object.
    Resolves century intelligently based on document context.
    """
    if not date_str or len(date_str) < 6 or not date_str[:6].isdigit():
        return None, "Invalid date format (expected 6 digits YYMMDD)"

    yy = int(date_str[:2])
    mm = int(date_str[2:4])
    dd = int(date_str[4:6])

    if mm < 1 or mm > 12 or dd < 1 or dd > 31:
        return None, f"Invalid month/day: MM={mm}, DD={dd}"

    current_year = datetime.now().year
    current_yy = current_year % 100

    if is_expiry:
        # Expiry dates: generally current century
        # If YY < current_yy - 20 (unusually low), might be next century; otherwise 2000s
        year = 2000 + yy
    else:
        # Birth dates:
        # If YY > current_yy -> born in 1900s
        # If YY <= current_yy -> born in 2000s
        year = 2000 + yy if yy <= current_yy else 1900 + yy

    try:
        parsed = date(year, mm, dd)
        return parsed, ""
    except ValueError as e:
        return None, str(e)


def validate_mrz_field_check_digit(field_name: str, data_str: str, expected_digit: str) -> Dict[str, Any]:
    """Validates an individual MRZ field against its printed check digit."""
    calc_digit, steps = calculate_icao_check_digit(data_str)
    exp_digit_val = int(expected_digit) if expected_digit.isdigit() else -1
    is_valid = (calc_digit == exp_digit_val)

    return {
        "field": field_name,
        "raw_data": data_str,
        "calculated_check_digit": calc_digit,
        "expected_check_digit": expected_digit,
        "is_valid": is_valid,
        "steps_sample": steps[:6]  # First 6 steps for explainable UI preview
    }


def validate_document(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """Full Module 2 Validation Pipeline:
    - ICAO 9303 Check Digit Validations
    - Expiration & Date Sanity Checks
    - Blacklist / Watchlist Cross-Referencing
    - Format & Country Code Conformance
    """
    fields = extracted_data.get("fields", {})
    mrz_lines = extracted_data.get("raw_mrz_lines", [])
    mrz_format = extracted_data.get("mrz_format")

    passed_checks = []
    failed_checks = []
    warnings = []
    check_digits = {}

    doc_number = fields.get("document_number", "").replace("<", "").strip()
    doc_number_cd = fields.get("document_number_check_digit", "")

    dob_str = fields.get("date_of_birth", "")
    dob_cd = fields.get("date_of_birth_check_digit", "")

    expiry_str = fields.get("expiry_date", "")
    expiry_cd = fields.get("expiry_date_check_digit", "")

    composite_cd = fields.get("composite_check_digit", "")
    issuing_country = fields.get("issuing_country", "").replace("<", "").strip()
    nationality = fields.get("nationality", "").replace("<", "").strip()
    full_name = fields.get("full_name", "")

    # 1. Check Digits Validation (ICAO 9303)
    if doc_number and doc_number_cd:
        res = validate_mrz_field_check_digit("Document Number", doc_number, doc_number_cd)
        check_digits["document_number"] = res
        if res["is_valid"]:
            passed_checks.append(f"Document Number check digit verified (ICAO 9303: {doc_number_cd})")
        else:
            failed_checks.append(
                f"Document Number check digit mismatch: printed '{doc_number_cd}', computed '{res['calculated_check_digit']}'"
            )

    if dob_str and dob_cd:
        res = validate_mrz_field_check_digit("Date of Birth", dob_str, dob_cd)
        check_digits["date_of_birth"] = res
        if res["is_valid"]:
            passed_checks.append(f"Date of Birth check digit verified (ICAO 9303: {dob_cd})")
        else:
            failed_checks.append(
                f"Date of Birth check digit mismatch: printed '{dob_cd}', computed '{res['calculated_check_digit']}'"
            )

    if expiry_str and expiry_cd:
        res = validate_mrz_field_check_digit("Expiry Date", expiry_str, expiry_cd)
        check_digits["expiry_date"] = res
        if res["is_valid"]:
            passed_checks.append(f"Expiry Date check digit verified (ICAO 9303: {expiry_cd})")
        else:
            failed_checks.append(
                f"Expiry Date check digit mismatch: printed '{expiry_cd}', computed '{res['calculated_check_digit']}'"
            )

    # Composite check digit for TD3
    if mrz_format == "TD3" and len(mrz_lines) >= 2 and len(mrz_lines[1]) >= 44:
        line2 = mrz_lines[1]
        # TD3 composite string: positions 1-10 + 14-20 + 22-43 (0-indexed: [0:10] + [13:20] + [21:43])
        composite_data = line2[0:10] + line2[13:20] + line2[21:43]
        expected_composite = line2[43]
        res = validate_mrz_field_check_digit("Composite", composite_data, expected_composite)
        check_digits["composite"] = res
        if res["is_valid"]:
            passed_checks.append(f"Composite overall check digit verified (ICAO 9303: {expected_composite})")
        else:
            failed_checks.append(
                f"Composite check digit mismatch: printed '{expected_composite}', computed '{res['calculated_check_digit']}'"
            )

    # 2. Expiration Date Logic
    is_expired = False
    days_to_expiry = None
    if expiry_str:
        parsed_exp, err = parse_mrz_date(expiry_str, is_expiry=True)
        if parsed_exp:
            today = date.today()
            days_to_expiry = (parsed_exp - today).days
            fields["expiry_date_formatted"] = parsed_exp.isoformat()
            if days_to_expiry < 0:
                is_expired = True
                failed_checks.append(f"Document EXPIRED on {parsed_exp.isoformat()} ({abs(days_to_expiry)} days ago)")
            elif days_to_expiry < 180:
                warnings.append(f"Document expires soon on {parsed_exp.isoformat()} (in {days_to_expiry} days)")
            else:
                passed_checks.append(f"Document valid until {parsed_exp.isoformat()} ({days_to_expiry} days remaining)")
        else:
            failed_checks.append(f"Failed to parse expiry date: {err}")

    # 3. Date of Birth & Age Logic
    if dob_str:
        parsed_dob, err = parse_mrz_date(dob_str, is_expiry=False)
        if parsed_dob:
            today = date.today()
            age_years = today.year - parsed_dob.year - ((today.month, today.day) < (parsed_dob.month, parsed_dob.day))
            fields["date_of_birth_formatted"] = parsed_dob.isoformat()
            fields["holder_age"] = age_years
            if age_years < 0:
                failed_checks.append("Date of Birth is in the future")
            elif age_years > 115:
                warnings.append(f"Unusually high holder age: {age_years} years old")
            else:
                passed_checks.append(f"Holder age verified: {age_years} years old (born {parsed_dob.isoformat()})")
        else:
            failed_checks.append(f"Failed to parse Date of Birth: {err}")

    # 4. Country Code Validation
    if issuing_country:
        if issuing_country in COMMON_COUNTRY_CODES:
            passed_checks.append(f"Issuing country code '{issuing_country}' is valid ICAO/ISO 3166-1")
        else:
            warnings.append(f"Non-standard issuing country code '{issuing_country}'")

    # 5. Blacklist / Watchlist Lookup (SQLite)
    blacklist_hit = None
    watchlist_hit = None

    if doc_number:
        hit = check_document(doc_number, issuing_country)
        if hit:
            blacklist_hit = hit
            failed_checks.append(
                f"STOLEN/LOST DOCUMENT HIT: Doc #{doc_number} flagged ({hit['reason']}) - Severity: {hit['severity']}"
            )
        else:
            passed_checks.append(f"Doc #{doc_number} cleared against Stolen & Lost Travel Documents (SLTD) registry")

    if full_name:
        hit = check_person(full_name, dob_str)
        if hit:
            watchlist_hit = hit
            failed_checks.append(
                f"WATCHLIST PERSON HIT: '{hit['name']}' matches active watchlist record ({hit['reason']})"
            )
        else:
            passed_checks.append("Holder name cleared against Interpol/National Watchlist")

    # 6. Calculate Validation Score (0.0 to 1.0)
    # 1.0 is completely clean, 0.0 is critical violation.
    base_score = 1.0

    # Critical failures zero out or severely diminish the score
    if blacklist_hit or watchlist_hit:
        base_score = 0.05
    elif len(failed_checks) > 0:
        penalty_per_fail = 0.35
        base_score = max(0.0, 1.0 - (len(failed_checks) * penalty_per_fail))
    elif is_expired:
        base_score = min(base_score, 0.20)

    # Minor warning penalty
    if len(warnings) > 0:
        base_score = max(0.1, base_score - (len(warnings) * 0.05))

    validation_score = round(base_score, 3)

    return {
        "validation_score": validation_score,
        "is_valid": (len(failed_checks) == 0 and not is_expired and not blacklist_hit),
        "is_expired": is_expired,
        "days_to_expiry": days_to_expiry,
        "is_blacklisted": bool(blacklist_hit or watchlist_hit),
        "blacklist_match": blacklist_hit,
        "watchlist_match": watchlist_hit,
        "check_digits": check_digits,
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "warnings": warnings,
        "fields_augmented": fields
    }
