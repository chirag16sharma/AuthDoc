"""
Explainable Risk Scoring Engine
Implements:
1. Transparent weighted risk formula:
   risk = 0.3 * (1 - validation_score) + 0.4 * tamper_score + 0.3 * (1 - face_match_score)
2. Graceful mode switching if selfie is not provided (50/50 doc integrity & tamper).
3. Clear human-readable explainability trace & prioritized risk signals for border officers.
"""

from typing import Dict, Any, List, Optional


def compute_risk_score(
    validation_result: Dict[str, Any],
    tamper_result: Dict[str, Any],
    face_result: Optional[Dict[str, Any]] = None,
    has_selfie: bool = True
) -> Dict[str, Any]:
    """Computes transparent, explainable risk score and generates decision payload."""
    val_score = float(validation_result.get("validation_score", 0.5))
    tamper_score = float(tamper_result.get("tamper_score", 0.5))

    if has_selfie and face_result is not None:
        face_score = float(face_result.get("face_match_score", 0.0))
        # Standard 3-component weighted formula
        w_val = 0.30
        w_tamper = 0.40
        w_face = 0.30

        raw_risk = (
            w_val * (1.0 - val_score) +
            w_tamper * tamper_score +
            w_face * (1.0 - face_score)
        )
    else:
        # 2-component document-only mode
        face_score = None
        w_val = 0.45
        w_tamper = 0.55
        w_face = 0.0

        raw_risk = (
            w_val * (1.0 - val_score) +
            w_tamper * tamper_score
        )

    # Scale to 0 - 100
    overall_risk = round(min(100.0, max(0.0, raw_risk * 100.0)), 1)

    # Determine risk category & decision
    if overall_risk < 25.0:
        verdict = "APPROVED"
        verdict_badge = "success"
        verdict_text = "Identity Document Genuine & Verified"
    elif overall_risk < 60.0:
        verdict = "MANUAL_REVIEW"
        verdict_badge = "warning"
        verdict_text = "Suspicious Signals Detected - Escalate to Secondary Inspection"
    else:
        verdict = "REJECTED"
        verdict_badge = "danger"
        verdict_text = "High Fraud Probability - Document / Identity Rejected"

    # Compile human-readable explainability items
    flagged_reasons: List[Dict[str, Any]] = []

    # 1. Validation Flags
    for err in validation_result.get("failed_checks", []):
        flagged_reasons.append({
            "severity": "CRITICAL",
            "category": "Validation",
            "message": err,
            "module": "Module 2 (ICAO 9303 / Rules)"
        })

    for warn in validation_result.get("warnings", []):
        flagged_reasons.append({
            "severity": "WARNING",
            "category": "Validation",
            "message": warn,
            "module": "Module 2 (Rules)"
        })

    # 2. Tamper Flags
    for sig in tamper_result.get("flagged_signals", []):
        is_crit = "splicing" in sig.lower() or "photoshop" in sig.lower() or "gimp" in sig.lower()
        flagged_reasons.append({
            "severity": "CRITICAL" if is_crit else "WARNING",
            "category": "Tampering",
            "message": sig,
            "module": "Module 3 (ELA & Forensics)"
        })

    # 3. Biometric Flags
    if has_selfie and face_result is not None:
        if not face_result.get("is_match", False):
            flagged_reasons.append({
                "severity": "CRITICAL",
                "category": "Biometrics",
                "message": f"Biometric mismatch: Live selfie did not match passport portrait (similarity: {round(face_score * 100, 1)}%)",
                "module": "Module 4 (DeepFace Biometrics)"
            })
        else:
            flagged_reasons.append({
                "severity": "INFO",
                "category": "Biometrics",
                "message": f"Biometric match confirmed (confidence: {round(face_score * 100, 1)}%)",
                "module": "Module 4 (DeepFace Biometrics)"
            })

    # Sort flagged reasons: CRITICAL first, then WARNING, then INFO
    order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    flagged_reasons.sort(key=lambda r: order.get(r["severity"], 3))

    return {
        "overall_risk_score": overall_risk,
        "verdict": verdict,
        "verdict_badge": verdict_badge,
        "verdict_text": verdict_text,
        "weights": {
            "validation_weight": w_val,
            "tamper_weight": w_tamper,
            "face_weight": w_face
        },
        "breakdown": {
            "validation": {
                "score": round(val_score, 3),
                "risk_contribution": round(w_val * (1.0 - val_score) * 100, 1),
                "weight_percent": int(w_val * 100)
            },
            "tampering": {
                "score": round(tamper_score, 3),
                "risk_contribution": round(w_tamper * tamper_score * 100, 1),
                "weight_percent": int(w_tamper * 100)
            },
            "biometrics": {
                "score": round(face_score, 3) if face_score is not None else None,
                "risk_contribution": round(w_face * (1.0 - face_score) * 100, 1) if face_score is not None else 0.0,
                "weight_percent": int(w_face * 100) if has_selfie else 0
            }
        },
        "flagged_reasons": flagged_reasons
    }
