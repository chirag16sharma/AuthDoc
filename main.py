"""
FastAPI Server: Document Authenticity & Identity Verification System
Exposes REST endpoints for:
- Document & live selfie verification
- 1-Click hackathon demo scenarios
- ELA Heatmap generation
- ICAO 9303 checksum validation
- Blacklist/Watchlist database management
- Interactive Border Control Dashboard Web UI
"""

import os
import io
import base64
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

# Import system modules
from modules.ocr import extract_document
from modules.validation import validate_document
from modules.tamper import analyze_tampering
from modules.face_verification import verify_faces
from modules.risk_scorer import compute_risk_score
from modules.blacklist_db import get_all_blacklist, add_blacklist_document
from modules.sample_generator import generate_all_demo_samples, SAMPLES_DIR

app = FastAPI(
    title="AuthDoc — Document Authenticity & Identity Verification",
    description="Automated Border Security & KYC Fraud Detection Engine",
    version="1.0.0"
)

# Enable CORS for developer ease
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static folder
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
async def startup_event():
    """Generates sample test documents on boot."""
    try:
        generate_all_demo_samples()
    except Exception as e:
        print(f"Warning initializing samples: {e}")


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serves the main Border Control Dashboard UI."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>AuthDoc System Active. Please create static/index.html</h1>")


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "AuthDoc Identity Verification",
        "version": "1.0.0",
        "icao_compliance": "ICAO Doc 9303 (TD1, TD2, TD3)",
        "modules_active": ["OCR", "Validation", "ELA_Tamper", "Biometrics", "ExplainableRisk"]
    }


@app.get("/api/samples")
async def list_demo_samples():
    """Returns the list of 5 ground-truth demo scenarios for 1-click hackathon evaluation."""
    samples = generate_all_demo_samples()
    output = []
    for s in samples:
        output.append({
            "id": s["id"],
            "title": s["title"],
            "description": s["description"],
            "expected_verdict": s["expected_verdict"],
            "expected_risk": s["expected_risk"]
        })
    return {"samples": output}


@app.post("/api/samples/verify/{sample_id}")
async def verify_sample_by_id(sample_id: str):
    """Executes instant end-to-end verification on a built-in demo scenario."""
    samples = generate_all_demo_samples()
    matched = next((s for s in samples if s["id"] == sample_id), None)
    if not matched:
        raise HTTPException(status_code=404, detail=f"Demo sample '{sample_id}' not found.")

    doc_path = matched["doc_file"]
    selfie_path = matched["selfie_file"]

    # 1. OCR Extraction
    ocr_result = extract_document(doc_path, "auto")

    # 2. Document Validation
    val_result = validate_document(ocr_result)

    # 3. Tampering Analysis
    tamper_result = analyze_tampering(doc_path)

    # 4. Biometric Face Verification
    face_result = verify_faces(doc_path, selfie_path, face_boxes=matched.get("face_boxes"))

    # 5. Risk Scoring Engine
    risk_summary = compute_risk_score(val_result, tamper_result, face_result, has_selfie=True)

    # Also include original doc base64 preview for UI rendering
    with open(doc_path, "rb") as f:
        doc_b64 = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode('utf-8')}"
    with open(selfie_path, "rb") as f:
        selfie_b64 = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode('utf-8')}"

    return {
        "sample_id": sample_id,
        "sample_meta": {
            "title": matched["title"],
            "expected_verdict": matched["expected_verdict"],
            "expected_risk": matched["expected_risk"]
        },
        "document_preview_base64": doc_b64,
        "selfie_preview_base64": selfie_b64,
        "ocr": ocr_result,
        "validation": val_result,
        "tamper": tamper_result,
        "face": face_result,
        "risk": risk_summary
    }


@app.post("/api/verify")
async def verify_uploaded_document(
    document: UploadFile = File(...),
    selfie: Optional[UploadFile] = File(None),
    selfie_base64: Optional[str] = Form(None),
    doc_type_hint: Optional[str] = Form("auto")
):
    """Full End-to-End Verification Pipeline for live user uploads & webcam captures."""
    # 1. Read document bytes
    doc_bytes = await document.read()
    if not doc_bytes:
        raise HTTPException(status_code=400, detail="Empty document image uploaded.")

    # 2. Handle selfie (either file upload or base64 webcam frame)
    selfie_bytes = None
    if selfie and selfie.filename:
        selfie_bytes = await selfie.read()
    elif selfie_base64 and len(selfie_base64) > 30:
        try:
            # Strip data URL header if present
            if "," in selfie_base64:
                selfie_base64 = selfie_base64.split(",", 1)[1]
            selfie_bytes = base64.b64decode(selfie_base64)
        except Exception:
            selfie_bytes = None

    has_selfie = bool(selfie_bytes is not None and len(selfie_bytes) > 0)

    # Step 1: Module 1 — OCR & MRZ Extraction
    ocr_result = extract_document(doc_bytes, doc_type_hint or "auto")

    # Step 2: Module 2 — Document Validation (ICAO 9303, Expiry, Watchlist)
    val_result = validate_document(ocr_result)

    # Step 3: Module 3 — Tampering Detection (ELA + EXIF Forensics)
    tamper_result = analyze_tampering(doc_bytes)

    # Step 4: Module 4 — Biometric Face Verification
    face_result = None
    if has_selfie:
        face_result = verify_faces(doc_bytes, selfie_bytes)

    # Step 5: Explainable Risk Scoring Engine
    risk_summary = compute_risk_score(val_result, tamper_result, face_result, has_selfie=has_selfie)

    # Preview base64 strings
    doc_preview_b64 = f"data:image/jpeg;base64,{base64.b64encode(doc_bytes).decode('utf-8')}"
    selfie_preview_b64 = f"data:image/jpeg;base64,{base64.b64encode(selfie_bytes).decode('utf-8')}" if has_selfie else None

    return {
        "status": "success",
        "document_preview_base64": doc_preview_b64,
        "selfie_preview_base64": selfie_preview_b64,
        "ocr": ocr_result,
        "validation": val_result,
        "tamper": tamper_result,
        "face": face_result,
        "risk": risk_summary
    }


@app.get("/api/blacklist")
async def get_blacklist():
    """Inspects the SQLite stolen documents & watchlist records."""
    return get_all_blacklist()


@app.post("/api/blacklist")
async def add_blacklist_entry(
    doc_number: str = Form(...),
    country: str = Form(...),
    reason: str = Form(...),
    severity: str = Form("HIGH")
):
    """Adds a document to the local watchlist database."""
    success = add_blacklist_document(doc_number, country, reason, severity)
    return {"success": success, "message": f"Document {doc_number} added to watchlist."}


if __name__ == "__main__":
    import uvicorn
    print("\n=======================================================")
    print("🚀 Starting AuthDoc Identity Verification Server...")
    print("🌐 Dashboard UI: http://localhost:8000")
    print("📖 API Swagger:  http://localhost:8000/docs")
    print("=======================================================\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
