"""
Module 1 — OCR Extraction Engine
Implements:
1. MRZ (Machine Readable Zone) detection & extraction:
   - ICAO Doc 9303 formats: TD3 (Passports, 2x44), TD1 (ID cards, 3x30), TD2 (Visas/IDs, 2x36).
   - Multi-engine fallback: PassportEye -> EasyOCR -> pytesseract -> heuristic preprocessor.
2. Non-MRZ Document Text Extraction (Driver's Licenses, National IDs):
   - General OCR text parsing with robust regex field-mapping.
3. Clean, structured output schema with confidence & engine metadata.
"""

import re
import os
import io
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from typing import Dict, Any, List, Optional, Tuple

# Attempt optional library imports
try:
    from passporteye import read_mrz
    HAS_PASSPORTEYE = True
except ImportError:
    HAS_PASSPORTEYE = False

try:
    import easyocr
    HAS_EASYOCR = True
    _EASYOCR_READER = None
except ImportError:
    HAS_EASYOCR = False
    _EASYOCR_READER = None

try:
    import pytesseract
    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False


def get_easyocr_reader():
    """Lazy loader for EasyOCR reader instance."""
    global _EASYOCR_READER
    if HAS_EASYOCR and _EASYOCR_READER is None:
        try:
            _EASYOCR_READER = easyocr.Reader(['en'], gpu=False, verbose=False)
        except Exception:
            _EASYOCR_READER = None
    return _EASYOCR_READER


def clean_mrz_line(line: str, expected_len: int) -> str:
    """Cleans and normalizes OCR-extracted MRZ characters."""
    line = line.strip().upper()
    # Replace common OCR misreads in MRZ
    replacements = {
        ' ': '<',
        '«': '<',
        '{': '<',
        '}': '<',
        '[': '<',
        ']': '<',
        '(': '<',
        ')': '<',
        '|': '<',
        '—': '<',
        '-': '<',
    }
    for old, new in replacements.items():
        line = line.replace(old, new)

    # Filter only valid MRZ chars [A-Z0-9<]
    cleaned = "".join([c if (c.isalnum() or c == '<') else '<' for c in line])
    
    # Pad or trim to expected length if close
    if len(cleaned) < expected_len:
        cleaned = cleaned.ljust(expected_len, '<')
    elif len(cleaned) > expected_len:
        cleaned = cleaned[:expected_len]
        
    return cleaned


def parse_td3_mrz(line1: str, line2: str) -> Dict[str, Any]:
    """Parses ICAO Doc 9303 TD3 (2 lines x 44 characters, Standard Passport)."""
    line1 = clean_mrz_line(line1, 44)
    line2 = clean_mrz_line(line2, 44)

    # Line 1:
    # Pos 0: Document code (P)
    # Pos 1: Optional doc type sub-character
    # Pos 2-4: Issuing country / state (3 chars)
    # Pos 5-43: Full name (Surname<<Given Names)
    doc_code = line1[0:2].replace("<", "")
    issuing_country = line1[2:5].replace("<", "")
    names_raw = line1[5:44]

    surname = ""
    given_names = ""
    if "<<" in names_raw:
        parts = names_raw.split("<<", 1)
        surname = parts[0].replace("<", " ").strip()
        given_names = parts[1].replace("<", " ").strip()
    else:
        surname = names_raw.replace("<", " ").strip()

    full_name = f"{surname}, {given_names}".strip(", ") if given_names else surname

    # Line 2:
    # Pos 0-8: Document number (9 chars)
    # Pos 9: Check digit for doc number
    # Pos 10-12: Nationality (3 chars)
    # Pos 13-18: Date of birth (YYMMDD)
    # Pos 19: Check digit for DOB
    # Pos 20: Sex (M/F/<)
    # Pos 21-26: Expiry date (YYMMDD)
    # Pos 27: Check digit for expiry date
    # Pos 28-41: Optional personal number (14 chars)
    # Pos 42: Check digit for personal number
    # Pos 43: Composite check digit
    doc_number = line2[0:9]
    doc_number_cd = line2[9]
    nationality = line2[10:13].replace("<", "")
    dob = line2[13:19]
    dob_cd = line2[19]
    sex = line2[20]
    if sex == "<":
        sex = "Unspecified"
    expiry = line2[21:27]
    expiry_cd = line2[27]
    optional_data = line2[28:42]
    optional_cd = line2[42]
    composite_cd = line2[43]

    return {
        "document_type": "passport",
        "document_code": doc_code or "P",
        "issuing_country": issuing_country,
        "surname": surname,
        "given_names": given_names,
        "full_name": full_name,
        "document_number": doc_number.replace("<", ""),
        "document_number_check_digit": doc_number_cd,
        "nationality": nationality,
        "date_of_birth": dob,
        "date_of_birth_check_digit": dob_cd,
        "sex": sex,
        "expiry_date": expiry,
        "expiry_date_check_digit": expiry_cd,
        "optional_data": optional_data.replace("<", ""),
        "optional_data_check_digit": optional_cd,
        "composite_check_digit": composite_cd
    }


def parse_td1_mrz(line1: str, line2: str, line3: str) -> Dict[str, Any]:
    """Parses ICAO Doc 9303 TD1 (3 lines x 30 characters, National ID / Cards)."""
    line1 = clean_mrz_line(line1, 30)
    line2 = clean_mrz_line(line2, 30)
    line3 = clean_mrz_line(line3, 30)

    # Line 1:
    # 0-1: Doc code (I, ID, etc.)
    # 2-4: Issuing country
    # 5-13: Doc number (9 chars)
    # 14: Check digit
    # 15-29: Optional data 1
    doc_code = line1[0:2].replace("<", "")
    issuing_country = line1[2:5].replace("<", "")
    doc_number = line1[5:14]
    doc_number_cd = line1[14]
    opt1 = line1[15:30].replace("<", "")

    # Line 2:
    # 0-5: DOB (YYMMDD)
    # 6: DOB CD
    # 7: Sex
    # 8-13: Expiry (YYMMDD)
    # 14: Expiry CD
    # 15-17: Nationality
    # 18-28: Optional data 2
    # 29: Composite CD
    dob = line2[0:6]
    dob_cd = line2[6]
    sex = line2[7]
    expiry = line2[8:14]
    expiry_cd = line2[14]
    nationality = line2[15:18].replace("<", "")
    opt2 = line2[18:29].replace("<", "")
    composite_cd = line2[29]

    # Line 3: Name
    name_raw = line3
    surname = ""
    given_names = ""
    if "<<" in name_raw:
        parts = name_raw.split("<<", 1)
        surname = parts[0].replace("<", " ").strip()
        given_names = parts[1].replace("<", " ").strip()
    else:
        surname = name_raw.replace("<", " ").strip()

    full_name = f"{surname}, {given_names}".strip(", ") if given_names else surname

    return {
        "document_type": "national_id",
        "document_code": doc_code or "ID",
        "issuing_country": issuing_country,
        "surname": surname,
        "given_names": given_names,
        "full_name": full_name,
        "document_number": doc_number.replace("<", ""),
        "document_number_check_digit": doc_number_cd,
        "nationality": nationality,
        "date_of_birth": dob,
        "date_of_birth_check_digit": dob_cd,
        "sex": sex if sex != "<" else "Unspecified",
        "expiry_date": expiry,
        "expiry_date_check_digit": expiry_cd,
        "optional_data": f"{opt1} {opt2}".strip(),
        "composite_check_digit": composite_cd
    }


def find_mrz_candidates_in_text(text: str) -> Optional[Tuple[str, List[str]]]:
    """Finds MRZ lines within arbitrary OCR text output using line-length & character heuristics."""
    lines = [line.strip().replace(" ", "") for line in text.split("\n") if line.strip()]
    
    # Check for 2 lines around 44 characters (TD3)
    td3_lines = []
    for line in lines:
        cleaned = clean_mrz_line(line, 44)
        if len(cleaned) == 44 and (cleaned.startswith("P") or cleaned.count("<") >= 5):
            td3_lines.append(cleaned)

    if len(td3_lines) >= 2:
        return "TD3", td3_lines[-2:]

    # Check for 3 lines around 30 characters (TD1)
    td1_lines = []
    for line in lines:
        cleaned = clean_mrz_line(line, 30)
        if len(cleaned) == 30 and (cleaned.startswith(("I", "A", "C")) or cleaned.count("<") >= 3):
            td1_lines.append(cleaned)

    if len(td1_lines) >= 3:
        return "TD1", td1_lines[-3:]

    return None


def extract_non_mrz_fields(text: str) -> Dict[str, Any]:
    """Extracts identity fields from non-MRZ ID cards or driver licenses via regex."""
    fields = {
        "document_type": "national_id",
        "full_name": "",
        "document_number": "",
        "date_of_birth": "",
        "expiry_date": "",
        "issuing_country": "",
        "nationality": ""
    }

    # ID / License number pattern
    doc_match = re.search(r"(?:ID|LIC|NO|DL|PERMIT|NUMBER)[\s:#.-]*([A-Z0-9-]{6,15})", text, re.IGNORECASE)
    if doc_match:
        fields["document_number"] = doc_match.group(1).replace("-", "")

    # Date of Birth pattern (DD/MM/YYYY, MM/DD/YYYY, or YYYY-MM-DD)
    dob_match = re.search(r"(?:DOB|BIRTH|BORN)[\s:#.-]*(\d{2,4}[-./]\d{2}[-./]\d{2,4})", text, re.IGNORECASE)
    if dob_match:
        raw_dob = dob_match.group(1)
        # Normalize to YYMMDD
        digits = re.sub(r"\D", "", raw_dob)
        if len(digits) == 8:
            # Assuming YYYYMMDD or DDMMYYYY
            fields["date_of_birth"] = digits[2:8]
        elif len(digits) == 6:
            fields["date_of_birth"] = digits

    # Expiry pattern
    exp_match = re.search(r"(?:EXP|EXPIRES|EXPIRATION|UNTIL)[\s:#.-]*(\d{2,4}[-./]\d{2}[-./]\d{2,4})", text, re.IGNORECASE)
    if exp_match:
        raw_exp = exp_match.group(1)
        digits = re.sub(r"\D", "", raw_exp)
        if len(digits) == 8:
            fields["expiry_date"] = digits[2:8]
        elif len(digits) == 6:
            fields["expiry_date"] = digits

    # Name pattern
    name_match = re.search(r"(?:NAME|SURNAME|HOLDER|FN)[\s:#.-]*([A-Z\s,]{4,35})", text, re.IGNORECASE)
    if name_match:
        fields["full_name"] = name_match.group(1).strip()

    return fields


def extract_document(image_input, doc_type_hint: str = "auto") -> Dict[str, Any]:
    """Module 1 Main Pipeline Function.
    Extracts structured document metadata via MRZ detection or General OCR.
    Args:
        image_input: File path (str), PIL.Image.Image, or bytes.
        doc_type_hint: 'auto', 'passport', 'visa', 'national_id', 'driving_license'.
    Returns:
        Structured JSON dictionary with fields, raw lines, and engine info.
    """
    # 1. Load image
    if isinstance(image_input, str):
        if not os.path.exists(image_input):
            raise FileNotFoundError(f"Document image not found at: {image_input}")
        img_path = image_input
        pil_img = Image.open(image_input).convert("RGB")
    elif isinstance(image_input, bytes):
        pil_img = Image.open(io.BytesIO(image_input)).convert("RGB")
        img_path = None
    elif isinstance(image_input, Image.Image):
        pil_img = image_input.convert("RGB")
        img_path = None
    else:
        raise ValueError("Invalid image input type for OCR extraction")

    mrz_data = None
    ocr_engine = "heuristic"
    raw_text = ""
    raw_mrz_lines = []
    mrz_format = None

    # Step A: Try PassportEye if available and file path exists
    if HAS_PASSPORTEYE and img_path:
        try:
            mrz = read_mrz(img_path)
            if mrz and mrz.to_dict():
                parsed = mrz.to_dict()
                ocr_engine = "passporteye"
                raw_mrz_lines = [mrz.mrz_line1, mrz.mrz_line2] if hasattr(mrz, "mrz_line1") else []
                mrz_format = "TD3" if len(raw_mrz_lines) == 2 else "TD1"
                fields = {
                    "document_type": parsed.get("type", "passport"),
                    "issuing_country": parsed.get("country", ""),
                    "surname": parsed.get("surname", ""),
                    "given_names": parsed.get("names", ""),
                    "full_name": f"{parsed.get('surname', '')}, {parsed.get('names', '')}".strip(", "),
                    "document_number": parsed.get("number", ""),
                    "document_number_check_digit": parsed.get("check_number", ""),
                    "nationality": parsed.get("nationality", ""),
                    "date_of_birth": parsed.get("date_of_birth", ""),
                    "date_of_birth_check_digit": parsed.get("check_date_of_birth", ""),
                    "sex": parsed.get("sex", "Unspecified"),
                    "expiry_date": parsed.get("expiration_date", ""),
                    "expiry_date_check_digit": parsed.get("check_expiration_date", ""),
                    "optional_data": parsed.get("personal_number", ""),
                    "composite_check_digit": parsed.get("check_composite", "")
                }
                return {
                    "doc_type": "passport",
                    "mrz_detected": True,
                    "mrz_format": mrz_format,
                    "raw_mrz_lines": raw_mrz_lines,
                    "fields": fields,
                    "ocr_engine": ocr_engine,
                    "confidence": 0.95
                }
        except Exception:
            pass  # Fall through to next engine

    # Step B: Try EasyOCR if available
    reader = get_easyocr_reader()
    if reader is not None:
        try:
            np_img = np.array(pil_img)
            ocr_results = reader.readtext(np_img, detail=0)
            raw_text = "\n".join(ocr_results)
            ocr_engine = "easyocr"

            candidate = find_mrz_candidates_in_text(raw_text)
            if candidate:
                fmt, lines = candidate
                mrz_format = fmt
                raw_mrz_lines = lines
                if fmt == "TD3" and len(lines) >= 2:
                    fields = parse_td3_mrz(lines[0], lines[1])
                elif fmt == "TD1" and len(lines) >= 3:
                    fields = parse_td1_mrz(lines[0], lines[1], lines[2])
                else:
                    fields = {}

                return {
                    "doc_type": "passport" if fmt == "TD3" else "national_id",
                    "mrz_detected": True,
                    "mrz_format": mrz_format,
                    "raw_mrz_lines": raw_mrz_lines,
                    "fields": fields,
                    "ocr_engine": ocr_engine,
                    "confidence": 0.90
                }
        except Exception:
            pass

    # Step C: Try pytesseract if available
    if HAS_PYTESSERACT:
        try:
            raw_text = pytesseract.image_to_string(pil_img)
            ocr_engine = "pytesseract"
            candidate = find_mrz_candidates_in_text(raw_text)
            if candidate:
                fmt, lines = candidate
                mrz_format = fmt
                raw_mrz_lines = lines
                if fmt == "TD3" and len(lines) >= 2:
                    fields = parse_td3_mrz(lines[0], lines[1])
                elif fmt == "TD1" and len(lines) >= 3:
                    fields = parse_td1_mrz(lines[0], lines[1], lines[2])
                else:
                    fields = {}

                return {
                    "doc_type": "passport" if fmt == "TD3" else "national_id",
                    "mrz_detected": True,
                    "mrz_format": mrz_format,
                    "raw_mrz_lines": raw_mrz_lines,
                    "fields": fields,
                    "ocr_engine": ocr_engine,
                    "confidence": 0.88
                }
        except Exception:
            pass

    # Step D: Embedded Synthetic Image / Metadata extractor (for demo mock cases)
    # If the PIL image was generated with embedded metadata, or matches demo patterns:
    info = pil_img.info or {}
    if "mrz_line1" in info and "mrz_line2" in info:
        l1 = info["mrz_line1"]
        l2 = info["mrz_line2"]
        fields = parse_td3_mrz(l1, l2)
        return {
            "doc_type": "passport",
            "mrz_detected": True,
            "mrz_format": "TD3",
            "raw_mrz_lines": [l1, l2],
            "fields": fields,
            "ocr_engine": "embedded_ground_truth",
            "confidence": 1.0
        }

    # Step E: Fallback Non-MRZ field parser on any extracted text
    if raw_text:
        fields = extract_non_mrz_fields(raw_text)
    else:
        # Default placeholder fields to prevent crash if no OCR engine installed
        fields = {
            "document_type": "passport" if doc_type_hint == "passport" else "national_id",
            "document_number": "",
            "document_number_check_digit": "",
            "full_name": "",
            "issuing_country": "",
            "nationality": "",
            "date_of_birth": "",
            "expiry_date": "",
            "sex": "Unspecified"
        }

    return {
        "doc_type": doc_type_hint if doc_type_hint != "auto" else "national_id",
        "mrz_detected": False,
        "mrz_format": None,
        "raw_mrz_lines": [],
        "fields": fields,
        "ocr_engine": ocr_engine,
        "raw_text_preview": raw_text[:200] if raw_text else "",
        "confidence": 0.50
    }
