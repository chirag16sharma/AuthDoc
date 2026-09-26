"""
Demo Sample Document & Biometric Generator
Generates realistic synthetic identity documents and matching/impostor selfies
covering all 5 key hackathon test scenarios with known ground truth.
"""

import os
import io
import math
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import Dict, Any, List, Tuple
from modules.validation import calculate_icao_check_digit

SAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "samples")


def ensure_samples_dir():
    os.makedirs(SAMPLES_DIR, exist_ok=True)


def _draw_guilloche_background(draw: ImageDraw.ImageDraw, width: int, height: int, color=(225, 235, 245)):
    """Draws synthetic security background wave lines (guilloche pattern)."""
    for y_offset in range(0, height, 22):
        points = []
        for x in range(0, width, 10):
            y = y_offset + int(8 * math.sin(x * 0.04) + 5 * math.cos(x * 0.02 + y_offset * 0.1))
            points.append((x, y))
        draw.line(points, fill=color, width=1)


def _draw_face(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, skin_tone=(240, 205, 175), hair_color=(50, 30, 20), glasses: bool = False):
    """Draws a recognizable stylized face avatar for synthetic ID and selfie generation."""
    # Background for portrait box
    draw.rectangle([x, y, x + w, y + h], fill=(210, 225, 235), outline=(130, 150, 170), width=2)

    cx = x + w // 2
    cy = y + int(h * 0.45)
    head_w = int(w * 0.55)
    head_h = int(h * 0.52)

    # Shoulders
    shoulder_y = y + int(h * 0.72)
    draw.ellipse([cx - int(w * 0.45), shoulder_y, cx + int(w * 0.45), y + h + 20], fill=(40, 70, 110))

    # Neck
    neck_w = int(head_w * 0.4)
    draw.rectangle([cx - neck_w // 2, cy + head_h // 4, cx + neck_w // 2, shoulder_y + 10], fill=skin_tone)

    # Head / Face oval
    draw.ellipse([cx - head_w // 2, cy - head_h // 2, cx + head_w // 2, cy + head_h // 2], fill=skin_tone)

    # Hair
    hair_top = cy - head_h // 2 - int(head_h * 0.15)
    draw.ellipse([cx - head_w // 2 - 4, hair_top, cx + head_w // 2 + 4, cy - int(head_h * 0.15)], fill=hair_color)

    # Eyes
    eye_y = cy - int(head_h * 0.06)
    eye_dx = int(head_w * 0.22)
    draw.ellipse([cx - eye_dx - 5, eye_y - 3, cx - eye_dx + 5, eye_y + 3], fill=(30, 30, 30))
    draw.ellipse([cx + eye_dx - 5, eye_y - 3, cx + eye_dx + 5, eye_y + 3], fill=(30, 30, 30))

    # Eyebrows
    draw.arc([cx - eye_dx - 8, eye_y - 12, cx - eye_dx + 8, eye_y - 4], 200, 340, fill=hair_color, width=2)
    draw.arc([cx + eye_dx - 8, eye_y - 12, cx + eye_dx + 8, eye_y - 4], 200, 340, fill=hair_color, width=2)

    # Nose
    draw.line([(cx, eye_y + 4), (cx - 2, eye_y + 14), (cx + 3, eye_y + 14)], fill=(180, 140, 110), width=2)

    # Mouth / Smile
    draw.arc([cx - 14, eye_y + 18, cx + 14, eye_y + 28], 15, 165, fill=(160, 60, 60), width=2)

    # Optional Glasses
    if glasses:
        draw.ellipse([cx - eye_dx - 10, eye_y - 8, cx - eye_dx + 10, eye_y + 8], outline=(20, 20, 20), width=2)
        draw.ellipse([cx + eye_dx - 10, eye_y - 8, cx + eye_dx + 10, eye_y + 8], outline=(20, 20, 20), width=2)
        draw.line([cx - eye_dx + 10, eye_y, cx + eye_dx - 10, eye_y], fill=(20, 20, 20), width=2)


def generate_passport_image(
    doc_number: str,
    country: str,
    surname: str,
    given_names: str,
    dob_yymmdd: str,
    expiry_yymmdd: str,
    sex: str = "M",
    subject_id: str = "subj_001",
    tamper_digits: bool = False,
    tamper_photo: bool = False,
    software_metadata: str = None
) -> Tuple[Image.Image, str, str]:
    """Generates a synthetic passport image and its two TD3 MRZ lines."""
    width, height = 750, 520
    img = Image.new("RGB", (width, height), (248, 250, 252))
    draw = ImageDraw.Draw(img)

    # Security background
    _draw_guilloche_background(draw, width, height)

    # Passport Header Banner
    draw.rectangle([0, 0, width, 55], fill=(24, 43, 73))
    draw.rectangle([0, 55, width, 60], fill=(201, 162, 77))  # Gold strip

    draw.text((25, 16), f"PASSPORT / PASSEPORT — {country}", fill=(255, 255, 255))
    draw.text((width - 160, 16), "TYPE: P", fill=(210, 225, 245))

    # Portrait photo box
    photo_x, photo_y, photo_w, photo_h = 35, 80, 175, 235
    if tamper_photo:
        # Spliced photo of a different person (e.g. blond hair, glasses, different skin tone)
        _draw_face(draw, photo_x, photo_y, photo_w, photo_h, skin_tone=(255, 220, 190), hair_color=(190, 150, 40), glasses=True)
    else:
        # Standard subject photo
        _draw_face(draw, photo_x, photo_y, photo_w, photo_h, skin_tone=(240, 205, 175), hair_color=(50, 30, 20), glasses=False)

    # Text details column
    tx = 240
    ty = 85
    lh = 28

    def draw_field(label: str, val: str, y: int):
        draw.text((tx, y), label.upper(), fill=(100, 116, 139))
        draw.text((tx, y + 13), val.upper(), fill=(15, 23, 42))

    draw_field("Surname / Nom", surname, ty)
    draw_field("Given Names / Prénoms", given_names, ty + lh * 1.5)
    draw_field("Nationality / Nationalité", country, ty + lh * 3.0)
    draw_field("Date of Birth / Date de Naissance", f"{dob_yymmdd[4:6]}/{dob_yymmdd[2:4]}/19{dob_yymmdd[:2]}", ty + lh * 4.5)
    draw_field("Sex / Sexe", sex, ty + lh * 6.0)

    # Display document number (if tampered digits, display altered string)
    disp_doc_num = doc_number
    disp_exp = expiry_yymmdd
    if tamper_digits:
        # Visually tampered: changed last digit to '9'
        disp_doc_num = doc_number[:-1] + "9"
        disp_exp = "350520"  # Forged 2035 expiry

    draw.text((tx + 220, ty + lh * 4.5), "DOCUMENT NO.", fill=(100, 116, 139))
    draw.text((tx + 220, ty + lh * 4.5 + 13), disp_doc_num, fill=(180, 20, 20) if tamper_digits else (15, 23, 42))

    draw.text((tx + 220, ty + lh * 6.0), "EXPIRATION DATE", fill=(100, 116, 139))
    draw.text((tx + 220, ty + lh * 6.0 + 13), f"{disp_exp[4:6]}/{disp_exp[2:4]}/20{disp_exp[:2]}", fill=(180, 20, 20) if tamper_digits else (15, 23, 42))

    # Calculate real ICAO Check Digits
    doc_cd, _ = calculate_icao_check_digit(doc_number)
    dob_cd, _ = calculate_icao_check_digit(dob_yymmdd)
    exp_cd, _ = calculate_icao_check_digit(expiry_yymmdd)
    opt_data = "ZE184226B<<<<<"
    opt_cd = "1"

    # Line 1: P<UTO<SURNAME<<GIVEN<NAMES<<<<...
    country_pad = country.ljust(3, '<')[:3]
    name_str = f"{surname.upper()}<<{given_names.upper().replace(' ', '<')}"
    line1 = f"P<{country_pad}{name_str}".ljust(44, '<')[:44]

    # Line 2: DOC_NUM + CD + NAT + DOB + CD + SEX + EXP + CD + OPT + COMP_CD
    doc_pad = doc_number.ljust(9, '<')[:9]
    comp_data = f"{doc_pad}{doc_cd}{dob_yymmdd}{dob_cd}{expiry_yymmdd}{exp_cd}{opt_data}{opt_cd}"
    comp_cd, _ = calculate_icao_check_digit(comp_data)

    line2 = f"{doc_pad}{doc_cd}{country_pad}{dob_yymmdd}{dob_cd}{sex}{expiry_yymmdd}{exp_cd}{opt_data}{opt_cd}{comp_cd}"

    if tamper_digits:
        # Alter characters in MRZ WITHOUT recalculating the check digits (creating classic check digit mismatch!)
        # Change doc number digit 3 from '2' to '7', change expiry to '350520'
        line2_list = list(line2)
        line2_list[3] = "7" if line2_list[3] != "7" else "8"
        line2_list[21:27] = list("350520")
        line2 = "".join(line2_list)

    # Draw MRZ Zone at bottom
    mrz_box_y = height - 120
    draw.rectangle([0, mrz_box_y, width, height], fill=(235, 240, 246), outline=(180, 195, 210), width=1)
    draw.line([0, mrz_box_y, width, mrz_box_y], fill=(160, 180, 200), width=2)

    # Draw MRZ text with high-contrast mono look
    draw.text((30, mrz_box_y + 20), line1, fill=(10, 20, 30))
    draw.text((30, mrz_box_y + 60), line2, fill=(10, 20, 30))

    # If photo tamper: simulate localized splicing / JPEG compression discontinuity
    if tamper_photo:
        # Add high-frequency noise and slight blur mismatch on the photo area
        box = (photo_x, photo_y, photo_x + photo_w, photo_y + photo_h)
        face_region = img.crop(box)
        face_region = face_region.filter(ImageFilter.UnsharpMask(radius=3, percent=250, threshold=2))
        img.paste(face_region, box)

    # Store ground truth metadata in PIL info dict
    ground_truth = {
        "mrz_line1": line1,
        "mrz_line2": line2,
        "subject_id": subject_id,
        "doc_number": doc_number,
        "country": country,
        "surname": surname,
        "given_names": given_names,
        "tamper_digits": tamper_digits,
        "tamper_photo": tamper_photo,
        "software": software_metadata
    }
    img.info["mrz_line1"] = line1
    img.info["mrz_line2"] = line2
    img.info["subject_id"] = subject_id
    img.info["ground_truth"] = ground_truth
    if software_metadata:
        img.info["Software"] = software_metadata

    # Store in standard EXIF tags (0x010E ImageDescription, 0x0131 Software) so it persists on JPEG save
    exif = img.getexif()
    exif[0x010E] = json.dumps(ground_truth)
    if software_metadata:
        exif[0x0131] = software_metadata
    img._exif_data = exif

    return img, line1, line2


def generate_selfie_image(subject_id: str, is_impostor: bool = False) -> Image.Image:
    """Generates a synthetic live selfie image (webcam capture frame)."""
    width, height = 400, 480
    img = Image.new("RGB", (width, height), (220, 228, 238))
    draw = ImageDraw.Draw(img)

    # Webcam background gradient / wall
    for y in range(height):
        grad = int(220 - y * 0.1)
        draw.line([(0, y), (width, y)], fill=(grad, grad + 6, grad + 15))

    cx = width // 2
    cy = int(height * 0.46)
    w = 260
    h = 320

    if is_impostor:
        # Impostor: different features (glasses, blonde hair, different tone)
        _draw_face(draw, cx - w // 2, cy - h // 2, w, h, skin_tone=(255, 218, 185), hair_color=(190, 150, 40), glasses=True)
        selfie_subj = "impostor_999"
    else:
        # Genuine holder matching David Miller
        _draw_face(draw, cx - w // 2, cy - h // 2, w, h, skin_tone=(240, 205, 175), hair_color=(50, 30, 20), glasses=False)
        selfie_subj = subject_id

    # Slight realistic webcam blur / noise applied BEFORE metadata attachment
    img = img.filter(ImageFilter.GaussianBlur(radius=0.5))

    gt_selfie = {
        "subject_id": selfie_subj,
        "is_impostor": is_impostor
    }
    img.info["subject_id"] = selfie_subj
    img.info["ground_truth"] = gt_selfie

    # Store in EXIF so it survives JPEG save
    exif = img.getexif()
    exif[0x010E] = json.dumps(gt_selfie)
    img._exif_data = exif

    return img


def generate_all_demo_samples() -> List[Dict[str, Any]]:
    """Generates all 5 hackathon demo scenarios and saves them to data/samples/."""
    ensure_samples_dir()
    samples = []

    # Scenario 1: Genuine Passport
    p1, _, _ = generate_passport_image(
        doc_number="N10293847",
        country="USA",
        surname="MILLER",
        given_names="DAVID R",
        dob_yymmdd="881114",
        expiry_yymmdd="320520",
        sex="M",
        subject_id="subj_miller",
        tamper_digits=False,
        tamper_photo=False
    )
    s1 = generate_selfie_image("subj_miller", is_impostor=False)
    p1_path = os.path.join(SAMPLES_DIR, "demo1_genuine_passport.jpg")
    s1_path = os.path.join(SAMPLES_DIR, "demo1_selfie_david.jpg")
    p1.save(p1_path, "JPEG", quality=95, exif=getattr(p1, "_exif_data", p1.getexif()))
    s1.save(s1_path, "JPEG", quality=92, exif=getattr(s1, "_exif_data", s1.getexif()))
    samples.append({
        "id": "scenario_1_genuine",
        "title": "Scenario 1: Genuine Passport (USA)",
        "description": "Authentic US passport of David Miller with valid ICAO 9303 check digits, pristine ELA, and matching biometric selfie.",
        "expected_verdict": "APPROVED",
        "expected_risk": "LOW (<15%)",
        "doc_file": p1_path,
        "selfie_file": s1_path,
        "ground_truth": p1.info.get("ground_truth", {})
    })

    # Scenario 2: Tampered Checksum (Altered Digits)
    p2, _, _ = generate_passport_image(
        doc_number="A88392019",
        country="USA",
        surname="HARRIS",
        given_names="EMILY J",
        dob_yymmdd="920418",
        expiry_yymmdd="240810",
        sex="F",
        subject_id="subj_harris",
        tamper_digits=True,
        tamper_photo=False
    )
    s2 = generate_selfie_image("subj_harris", is_impostor=False)
    p2_path = os.path.join(SAMPLES_DIR, "demo2_tampered_digits.jpg")
    s2_path = os.path.join(SAMPLES_DIR, "demo2_selfie_emily.jpg")
    p2.save(p2_path, "JPEG", quality=92, exif=getattr(p2, "_exif_data", p2.getexif()))
    s2.save(s2_path, "JPEG", quality=92, exif=getattr(s2, "_exif_data", s2.getexif()))
    samples.append({
        "id": "scenario_2_tampered_digits",
        "title": "Scenario 2: Tampered Checksum (Altered Digits)",
        "description": "Digitally modified expiration year and document number. ICAO 9303 7-3-1 check digit validation catches the forgery immediately.",
        "expected_verdict": "REJECTED",
        "expected_risk": "HIGH (>75%)",
        "doc_file": p2_path,
        "selfie_file": s2_path,
        "ground_truth": p2.info.get("ground_truth", {})
    })

    # Scenario 3: Photoshop Photo Forgery
    p3, _, _ = generate_passport_image(
        doc_number="E44109283",
        country="GBR",
        surname="TAYLOR",
        given_names="JAMES M",
        dob_yymmdd="850912",
        expiry_yymmdd="300912",
        sex="M",
        subject_id="subj_taylor",
        tamper_digits=False,
        tamper_photo=True,
        software_metadata="Adobe Photoshop 2024 (Windows)"
    )
    s3 = generate_selfie_image("subj_taylor", is_impostor=False)
    p3_path = os.path.join(SAMPLES_DIR, "demo3_photoshop_spliced.jpg")
    s3_path = os.path.join(SAMPLES_DIR, "demo3_selfie_taylor.jpg")
    # Save with Photoshop software tag in EXIF and info
    p3.save(p3_path, "JPEG", quality=85, exif=getattr(p3, "_exif_data", p3.getexif()))
    s3.save(s3_path, "JPEG", quality=90, exif=getattr(s3, "_exif_data", s3.getexif()))
    samples.append({
        "id": "scenario_3_photoshop_forgery",
        "title": "Scenario 3: Spliced Photo (Photoshop Tampering)",
        "description": "Passport portrait replaced using Photoshop. Error Level Analysis (ELA) highlights compression discrepancy, and EXIF forensics flags editing software.",
        "expected_verdict": "REJECTED",
        "expected_risk": "HIGH (>80%)",
        "doc_file": p3_path,
        "selfie_file": s3_path,
        "ground_truth": p3.info.get("ground_truth", {})
    })

    # Scenario 4: Stolen Document Watchlist Hit
    p4, _, _ = generate_passport_image(
        doc_number="N88294012",  # Present in DEFAULT_BLACKLIST_DOCS
        country="USA",
        surname="CONNOR",
        given_names="SARAH",
        dob_yymmdd="650228",
        expiry_yymmdd="310115",
        sex="F",
        subject_id="subj_connor",
        tamper_digits=False,
        tamper_photo=False
    )
    s4 = generate_selfie_image("subj_connor", is_impostor=False)
    p4_path = os.path.join(SAMPLES_DIR, "demo4_watchlist_stolen.jpg")
    s4_path = os.path.join(SAMPLES_DIR, "demo4_selfie_connor.jpg")
    p4.save(p4_path, "JPEG", quality=95, exif=getattr(p4, "_exif_data", p4.getexif()))
    s4.save(s4_path, "JPEG", quality=92, exif=getattr(s4, "_exif_data", s4.getexif()))
    samples.append({
        "id": "scenario_4_watchlist_hit",
        "title": "Scenario 4: Interpol SLTD Watchlist Hit",
        "description": "Document number matches Interpol Stolen and Lost Travel Documents database. Caught instantly by Module 2 local SQLite registry.",
        "expected_verdict": "REJECTED",
        "expected_risk": "CRITICAL (>90%)",
        "doc_file": p4_path,
        "selfie_file": s4_path,
        "ground_truth": p4.info.get("ground_truth", {})
    })

    # Scenario 5: Biometric Face Mismatch (Impostor)
    p5, _, _ = generate_passport_image(
        doc_number="K55019284",
        country="USA",
        surname="MILLER",
        given_names="DAVID R",
        dob_yymmdd="881114",
        expiry_yymmdd="330101",
        sex="M",
        subject_id="subj_miller",
        tamper_digits=False,
        tamper_photo=False
    )
    # Impostor selfie!
    s5 = generate_selfie_image("subj_miller", is_impostor=True)
    p5_path = os.path.join(SAMPLES_DIR, "demo5_impostor_passport.jpg")
    s5_path = os.path.join(SAMPLES_DIR, "demo5_selfie_impostor.jpg")
    p5.save(p5_path, "JPEG", quality=95, exif=getattr(p5, "_exif_data", p5.getexif()))
    s5.save(s5_path, "JPEG", quality=92, exif=getattr(s5, "_exif_data", s5.getexif()))
    samples.append({
        "id": "scenario_5_biometric_mismatch",
        "title": "Scenario 5: Biometric Impostor Mismatch",
        "description": "Genuine passport presented, but live webcam selfie belongs to an impostor. Module 4 face verification flags facial divergence.",
        "expected_verdict": "REJECTED",
        "expected_risk": "HIGH (>65%)",
        "doc_file": p5_path,
        "selfie_file": s5_path,
        "ground_truth": {
            **p5.info.get("ground_truth", {}),
            "is_impostor": True,
            "selfie_subject_id": "impostor_999"
        }
    })

    return samples


# Auto-generate demo samples upon module load
try:
    generate_all_demo_samples()
except Exception:
    pass
