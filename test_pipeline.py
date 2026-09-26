"""
Command-Line End-to-End Pipeline Verification Test
Usage:
    python test_pipeline.py [doc_image_path] [selfie_image_path]
    python test_pipeline.py --demo [scenario_1|scenario_2|scenario_3|scenario_4|scenario_5]
"""

import sys
import json
import os
from modules.ocr import extract_document
from modules.validation import validate_document
from modules.tamper import analyze_tampering
from modules.face_verification import verify_faces
from modules.risk_scorer import compute_risk_score
from modules.sample_generator import generate_all_demo_samples, SAMPLES_DIR


def run_pipeline(doc_path: str, selfie_path: str = None) -> dict:
    print(f"\n==================================================================")
    print(f"🛡️  DOCUMENT AUTHENTICITY & IDENTITY VERIFICATION PIPELINE")
    print(f"==================================================================")
    print(f"📁 Document: {doc_path}")
    print(f"👤 Selfie:   {selfie_path or 'None (Document-Only Mode)'}")

    # 1. Module 1: OCR Extraction
    print(f"\n--- [MODULE 1: OCR & MRZ EXTRACTION] ---")
    ocr_result = extract_document(doc_path, "auto")
    print(f"Engine:       {ocr_result.get('ocr_engine')}")
    print(f"MRZ Detected: {ocr_result.get('mrz_detected')} ({ocr_result.get('mrz_format')})")
    fields = ocr_result.get("fields", {})
    print(f"Full Name:    {fields.get('full_name')}")
    print(f"Doc Number:   {fields.get('document_number')} (CD: {fields.get('document_number_check_digit')})")
    print(f"Nationality:  {fields.get('nationality')}")
    print(f"DOB:          {fields.get('date_of_birth')}")
    print(f"Expiry Date:  {fields.get('expiry_date')}")

    # 2. Module 2: Document Validation
    print(f"\n--- [MODULE 2: DOCUMENT VALIDATION (ICAO 9303)] ---")
    val_result = validate_document(ocr_result)
    print(f"Validation Score: {val_result.get('validation_score') * 100:.1f}%")
    print(f"Passed Checks:    {len(val_result.get('passed_checks', []))}")
    for p in val_result.get('passed_checks', []):
        print(f"  ✅ {p}")
    if val_result.get('failed_checks'):
        print(f"Failed Checks:    {len(val_result.get('failed_checks', []))}")
        for f in val_result.get('failed_checks', []):
            print(f"  ❌ {f}")
    if val_result.get('warnings'):
        for w in val_result.get('warnings', []):
            print(f"  ⚠️  {w}")

    # 3. Module 3: Tampering Detection
    print(f"\n--- [MODULE 3: TAMPERING DETECTION (ELA + EXIF)] ---")
    tamper_result = analyze_tampering(doc_path)
    print(f"Tamper Score:     {tamper_result.get('tamper_score') * 100:.1f}% (Is Tampered: {tamper_result.get('is_tampered')})")
    ela = tamper_result.get("ela", {})
    print(f"ELA Anomaly:      {ela.get('score')} (Peak-to-Avg: {ela.get('stats', {}).get('peak_to_avg_ratio')})")
    meta = tamper_result.get("metadata", {})
    print(f"Metadata Score:   {meta.get('score')}")
    for sig in tamper_result.get("flagged_signals", []):
        print(f"  🚨 {sig}")

    # 4. Module 4: Biometric Face Verification
    face_result = None
    if selfie_path and os.path.exists(selfie_path):
        print(f"\n--- [MODULE 4: BIOMETRIC FACE VERIFICATION] ---")
        face_result = verify_faces(doc_path, selfie_path)
        print(f"Match Verdict:    {'MATCH ✅' if face_result.get('is_match') else 'MISMATCH ❌'}")
        print(f"Similarity Score: {face_result.get('face_match_score') * 100:.1f}%")
        print(f"Biometric Dist:   {face_result.get('distance')} (Threshold: {face_result.get('threshold')})")
        print(f"Engine:           {face_result.get('engine')}")

    # 5. Risk Scoring Engine
    print(f"\n--- [EXPLAINABLE RISK SCORING ENGINE] ---")
    risk_summary = compute_risk_score(val_result, tamper_result, face_result, has_selfie=bool(selfie_path))
    verdict = risk_summary.get("verdict")
    risk_score = risk_summary.get("overall_risk_score")
    print(f"Overall Risk Score: {risk_score} / 100")
    print(f"Final Decision:     {verdict} - {risk_summary.get('verdict_text')}")
    print(f"Risk Breakdown:")
    bd = risk_summary.get("breakdown", {})
    print(f"  • Doc Integrity Risk:  {bd.get('validation', {}).get('risk_contribution')}% (Weight {bd.get('validation', {}).get('weight_percent')}%)")
    print(f"  • Tamper Risk:         {bd.get('tampering', {}).get('risk_contribution')}% (Weight {bd.get('tampering', {}).get('weight_percent')}%)")
    if selfie_path:
        print(f"  • Biometric Risk:      {bd.get('biometrics', {}).get('risk_contribution')}% (Weight {bd.get('biometrics', {}).get('weight_percent')}%)")

    print(f"\nFlagged Explanations:")
    for flag in risk_summary.get("flagged_reasons", []):
        icon = "🔴" if flag["severity"] == "CRITICAL" else ("🟠" if flag["severity"] == "WARNING" else "🟢")
        print(f"  {icon} [{flag['category']}] {flag['message']}")

    print(f"==================================================================\n")

    return {
        "ocr": ocr_result,
        "validation": val_result,
        "tamper": tamper_result,
        "biometrics": face_result,
        "risk": risk_summary
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python test_pipeline.py <doc_image_path> [selfie_image_path]")
        print("  python test_pipeline.py --demo [1|2|3|4|5]")
        print("\nRunning default Demo Scenario 1 (Genuine Passport)...")
        samples = generate_all_demo_samples()
        run_pipeline(samples[0]["doc_file"], samples[0]["selfie_file"])
    elif sys.argv[1] == "--demo":
        samples = generate_all_demo_samples()
        idx = int(sys.argv[2]) - 1 if len(sys.argv) > 2 and sys.argv[2].isdigit() else 0
        idx = max(0, min(len(samples) - 1, idx))
        s = samples[idx]
        print(f"Loading {s['title']} - Expected: {s['expected_verdict']}")
        run_pipeline(s["doc_file"], s["selfie_file"])
    else:
        doc = sys.argv[1]
        selfie = sys.argv[2] if len(sys.argv) > 2 else None
        run_pipeline(doc, selfie)
