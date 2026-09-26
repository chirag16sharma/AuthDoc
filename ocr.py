"""
Module 1 -- OCR Extraction

Two paths:
  - MRZ path (passport / visa) via PassportEye -> structured, checksum-validated fields
  - General OCR path (national ID / license / permit) via EasyOCR -> raw text + regex guesses
"""

import re
from datetime import datetime
from passporteye import read_mrz
import easyocr

_reader = None  # lazy-loaded singleton -- EasyOCR model load is slow, do it once


def get_easyocr_reader():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(["en"], gpu=False)
    return _reader


def _mrz_date_to_iso(raw: str, field: str) -> str:
    """MRZ dates are YYMMDD with no century digit -- infer it."""
    if not raw or len(raw) != 6 or not raw.isdigit():
        return ""
    yy, mm, dd = int(raw[:2]), int(raw[2:4]), int(raw[4:6])
    current_yy = datetime.now().year % 100
    # expiry dates on ICAO documents are always post-2000; DOB needs a real guess
    century = 2000 if field == "expiry" else (1900 if yy > current_yy else 2000)
    try:
        return datetime(century + yy, mm, dd).strftime("%Y-%m-%d")
    except ValueError:
        return raw  # malformed -- surface raw value, let Module 2 flag it


def extract_mrz(image_path: str, doc_type_hint: str = "passport") -> dict:
    """Extract + checksum-validate fields from a passport or visa MRZ."""
    mrz = read_mrz(image_path)
    if mrz is None:
        return {"mrz_found": False}

    d = mrz.to_dict()
    mrz_type = d.get("mrz_type")
    # ICAO 9303 mrz_type tells us the real document category -- trust it over the hint
    if mrz_type == "TD3":
        detected_type = "passport"
    elif mrz_type in ("MRVA", "MRVB"):
        detected_type = "visa"
    elif mrz_type in ("TD1", "TD2"):
        detected_type = "id_card"
    else:
        detected_type = doc_type_hint

    # NOTE: per ICAO 9303, visa MRZ (MRVA/MRVB) only carries name, number, DOB,
    # nationality, sex, expiry -- "Visa Type", "Entry Validation" and "Stay
    # Duration" live in the visible zone, not the MRZ. Pull those via
    # extract_general() on the same image and merge if you need them.
    return {
        "doc_type": detected_type,
        "mrz_found": True,
        "name": f"{d.get('names', '').strip()} {d.get('surname', '').strip()}".strip(),
        "doc_number": d.get("number", "").strip(),
        "nationality": d.get("nationality", "").strip(),
        "dob": _mrz_date_to_iso(d.get("date_of_birth", ""), "dob"),
        "expiry": _mrz_date_to_iso(d.get("expiration_date", ""), "expiry"),
        "gender": d.get("sex", "").strip(),
        # checksum flags -- these are real ICAO check-digit results, feed
        # straight into Module 2, not a mock validation
        "valid_number": bool(d.get("valid_number")),
        "valid_dob": bool(d.get("valid_date_of_birth")),
        "valid_expiry": bool(d.get("valid_expiration_date")),
        "valid_composite": bool(d.get("valid_composite")),
    }


_DATE_RE = re.compile(r"\b(\d{2}[/-]\d{2}[/-]\d{4}|\d{4}[/-]\d{2}[/-]\d{2})\b")
_ID_RE = re.compile(r"\b[A-Z0-9]{6,12}\b")


def extract_general(image_path: str) -> dict:
    """Extract raw text + candidate fields from a national ID / license / permit."""
    lines = get_easyocr_reader().readtext(image_path, detail=0)
    full_text = " ".join(lines)
    return {
        "doc_type": "national_id",
        "mrz_found": False,
        "raw_text": lines,
        "candidate_dates": _DATE_RE.findall(full_text),
        "candidate_id_numbers": _ID_RE.findall(full_text.replace(" ", "")),
        # reliable name extraction needs a per-country layout template --
        # out of scope for a prototype, flag for manual review in the demo
        "name": None,
        "needs_manual_review": True,
    }


def extract_document(image_path: str, doc_type_hint: str = "auto") -> dict:
    """Single entry point the rest of the pipeline calls."""
    if doc_type_hint in ("passport", "visa", "auto"):
        hint = doc_type_hint if doc_type_hint != "auto" else "passport"
        result = extract_mrz(image_path, hint)
        if result["mrz_found"]:
            return result
    return extract_general(image_path)
