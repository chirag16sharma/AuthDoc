"""
Module 3 — Tampering Detection Engine
Implements:
1. Error Level Analysis (ELA):
   - JPEG recompression differential calculation.
   - Thermal heatmap generation (OpenCV COLORMAP_JET / COLORMAP_TURBO).
   - Anomaly detection via local variance & peak-to-background ratio.
2. Metadata Forensics:
   - EXIF parsing for photo editing software signatures (Photoshop, GIMP, Canva, etc.).
   - Timestamp chronological discrepancy detection.
   - Missing/stripped metadata anomaly signals.
3. Base64 visual artifacts for direct frontend dashboard rendering.
"""

import io
import os
import base64
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
from typing import Dict, Any, Tuple, List, Optional

# Try importing OpenCV for heatmap coloring
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

SUSPICIOUS_SOFTWARE_SIGNATURES = [
    "PHOTOSHOP", "GIMP", "CANVA", "PAINT.NET", "AFFINITY", "PIXELMATOR",
    "LIGHTROOM", "CORELDRAW", "ILLUSTRATOR", "PHOTO-PAINT", "SNAPSEED",
    "PICSART", "MEITU", "BEFUNKY", "IPHOTO", "MSPAINT", "MICROSOFT PAINT"
]


def perform_ela(
    image_input,
    quality: int = 90,
    scale_factor: int = 15
) -> Tuple[float, Image.Image, np.ndarray, Dict[str, Any]]:
    """Performs Error Level Analysis (ELA).
    Args:
        image_input: File path (str), PIL.Image.Image, or bytes.
        quality: JPEG compression quality for differential check.
        scale_factor: Multiplier to amplify subtle compression discrepancies.
    Returns:
        (ela_score: float 0-1, ela_diff_image: PIL Image, diff_array: np.ndarray, stats: dict)
    """
    if isinstance(image_input, str):
        orig_img = Image.open(image_input).convert("RGB")
    elif isinstance(image_input, bytes):
        orig_img = Image.open(io.BytesIO(image_input)).convert("RGB")
    elif isinstance(image_input, Image.Image):
        orig_img = image_input.convert("RGB")
    else:
        raise ValueError("Unsupported image input type for ELA")

    # Re-compress in memory to temporary buffer
    buffer = io.BytesIO()
    orig_img.save(buffer, "JPEG", quality=quality)
    buffer.seek(0)
    recompressed_img = Image.open(buffer).convert("RGB")

    # Absolute difference
    diff = ImageChops.difference(orig_img, recompressed_img)
    diff_arr = np.array(diff, dtype=np.float32)

    # Calculate statistics across channels
    channel_diff = np.mean(diff_arr, axis=2)  # 2D grayscale representation
    mean_val = float(np.mean(channel_diff))
    max_val = float(np.max(channel_diff))
    std_val = float(np.std(channel_diff))

    # Divide image into grid patches to detect localized editing hotspots
    h, w = channel_diff.shape
    patch_size = max(16, min(h, w) // 10)
    local_variances = []
    
    for y in range(0, h - patch_size + 1, patch_size):
        for x in range(0, w - patch_size + 1, patch_size):
            patch = channel_diff[y:y + patch_size, x:x + patch_size]
            local_variances.append(np.mean(patch))

    if local_variances:
        max_patch_mean = max(local_variances)
        avg_patch_mean = sum(local_variances) / len(local_variances)
        peak_to_avg_ratio = (max_patch_mean / (avg_patch_mean + 1e-5))
    else:
        peak_to_avg_ratio = 1.0

    # Tamper heuristic:
    # Natural untouched JPEG photos exhibit smooth, uniform compression noise (peak_to_avg < 2.2).
    # Spliced / photoshopped regions produce localized spikes where peak_to_avg > 3.0 or std is high.
    anomaly_factor = max(0.0, (peak_to_avg_ratio - 1.5) / 3.0)
    noise_factor = min(1.0, std_val / 18.0)
    
    # Combined ELA score between 0.0 and 1.0
    ela_score = round(min(1.0, max(0.0, 0.6 * anomaly_factor + 0.4 * noise_factor)), 3)

    # Scale the visual difference image for presentation
    # Extrema multiplier: scale so max diff is clearly visible
    scale = scale_factor
    extrema = diff.getextrema()
    max_diff = max([ex[1] for ex in extrema])
    if max_diff > 0:
        scale = max(scale_factor, int(255.0 / max_diff * 0.8))
    
    scale = min(scale, 35)  # Cap scale factor
    enhanced_diff = ImageEnhance.Brightness(diff).enhance(scale)

    stats = {
        "mean_error": round(mean_val, 2),
        "max_error": round(max_val, 2),
        "std_error": round(std_val, 2),
        "peak_to_avg_ratio": round(peak_to_avg_ratio, 2),
        "ela_score": ela_score
    }

    return ela_score, enhanced_diff, channel_diff, stats


def generate_ela_heatmap(orig_img: Image.Image, channel_diff: np.ndarray) -> str:
    """Generates an enhanced visual thermal heatmap overlay for judges & officers.
    Returns: Base64 data URL string (data:image/jpeg;base64,...)
    """
    orig_np = np.array(orig_img.convert("RGB"))

    if HAS_OPENCV:
        # Normalize diff to 0-255
        norm_diff = cv2.normalize(channel_diff, None, 0, 255, cv2.NORM_MINMAX)
        norm_diff_uint8 = norm_diff.astype(np.uint8)

        # Apply JET or TURBO colormap
        heatmap = cv2.applyColorMap(norm_diff_uint8, cv2.COLORMAP_JET)
        heatmap_rgb = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)

        # Blend 45% original document with 55% thermal heatmap
        overlay = cv2.addWeighted(orig_np, 0.45, heatmap_rgb, 0.55, 0)
        output_img = Image.fromarray(overlay)
    else:
        # Fallback to enhanced grayscale difference PIL
        diff_scaled = np.clip(channel_diff * 12, 0, 255).astype(np.uint8)
        output_img = Image.fromarray(diff_scaled).convert("RGB")

    buffered = io.BytesIO()
    output_img.save(buffered, format="JPEG", quality=85)
    img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{img_b64}"


def inspect_metadata(image_input) -> Tuple[float, Dict[str, Any], List[str]]:
    """Extracts EXIF and checks for tampering signatures and anomalies.
    Returns:
        (metadata_score: float 0-1, metadata_dict: dict, flagged_reasons: list)
    """
    if isinstance(image_input, str):
        img = Image.open(image_input)
    elif isinstance(image_input, bytes):
        img = Image.open(io.BytesIO(image_input))
    elif isinstance(image_input, Image.Image):
        img = image_input
    else:
        return 0.5, {}, ["Unknown image format"]

    metadata = {}
    flagged = []
    meta_score = 0.0

    # 1. Inspect PIL info dict (contains PNG text chunks, JPEG comments, etc.)
    info = img.info or {}
    for k, v in info.items():
        if isinstance(v, (str, int, float)):
            metadata[str(k)] = str(v)

    # 2. Extract standard EXIF tags
    exif_data = img.getexif()
    has_exif = bool(exif_data and len(exif_data) > 0)
    metadata["has_exif"] = has_exif

    software_tag = ""
    make_tag = ""
    model_tag = ""
    modify_date = ""
    original_date = ""

    if has_exif:
        from PIL.ExifTags import TAGS
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, str(tag_id))
            val_str = str(value).strip()
            metadata[tag_name] = val_str

            tag_lower = tag_name.lower()
            if tag_lower == "software":
                software_tag = val_str
            elif tag_lower == "make":
                make_tag = val_str
            elif tag_lower == "model":
                model_tag = val_str
            elif tag_lower == "datetime":
                modify_date = val_str
            elif tag_lower in ("datetimeoriginal", "datetimedigitized"):
                original_date = val_str

    # Check for software signatures indicating digital manipulation
    combined_text = f"{software_tag} {metadata.get('ImageDescription', '')} {metadata.get('UserComment', '')}".upper()

    detected_software = []
    for sig in SUSPICIOUS_SOFTWARE_SIGNATURES:
        if sig in combined_text:
            detected_software.append(sig)

    if detected_software:
        meta_score = max(meta_score, 0.85)
        soft_list = ", ".join(detected_software)
        flagged.append(f"Image editing software detected in EXIF: '{soft_list}'")
        metadata["tampering_software_detected"] = detected_software

    # Check timestamp mismatch (e.g. modified date vs original date)
    if modify_date and original_date and modify_date != original_date:
        flagged.append(f"Timestamp anomaly: Photo taken {original_date} but modified on {modify_date}")
        meta_score = max(meta_score, 0.45)

    # Check for stripped EXIF in scanned / photo ID
    if not has_exif:
        metadata["exif_status"] = "STRIPPED_OR_ABSENT"
        metadata_notes = "Metadata absent (common in web exports or canvas-edited images)"
        metadata["notes"] = metadata_notes
        # Mild risk signal: genuine phone/camera photos of passports have EXIF
        meta_score = max(meta_score, 0.20)
    else:
        metadata["exif_status"] = "PRESENT"
        if make_tag or model_tag:
            metadata["camera_hardware"] = f"{make_tag} {model_tag}".strip()

    return round(meta_score, 3), metadata, flagged


def analyze_tampering(image_input) -> Dict[str, Any]:
    """Module 3 Main Entrypoint:
    Runs ELA and Metadata Forensics, generating unified tamper score & visual heatmap.
    """
    if isinstance(image_input, str):
        orig_img = Image.open(image_input).convert("RGB")
    elif isinstance(image_input, bytes):
        orig_img = Image.open(io.BytesIO(image_input)).convert("RGB")
    elif isinstance(image_input, Image.Image):
        orig_img = image_input.convert("RGB")
    else:
        raise ValueError("Invalid image input for tampering analysis")

    # 1. Error Level Analysis
    ela_score, diff_img, channel_diff, ela_stats = perform_ela(orig_img)
    heatmap_b64 = generate_ela_heatmap(orig_img, channel_diff)

    # 2. Metadata Forensics
    meta_score, meta_dict, meta_flags = inspect_metadata(image_input)

    # 3. Synthesize Tamper Score
    # ELA represents physical compression artifacts (65% weight)
    # Metadata forensics represents provenance trails (35% weight)
    # If software signature is definitively found, force high tamper score
    if "tampering_software_detected" in meta_dict:
        tamper_score = max(0.85, 0.6 * ela_score + 0.4 * meta_score)
    else:
        tamper_score = 0.65 * ela_score + 0.35 * meta_score

    tamper_score = round(min(1.0, max(0.0, tamper_score)), 3)

    tamper_flags = list(meta_flags)
    if ela_score >= 0.70:
        tamper_flags.append(
            f"High compression variance detected in ELA ({ela_stats['peak_to_avg_ratio']}x peak ratio) - indicates digital splicing"
        )
    elif ela_score >= 0.45:
        tamper_flags.append(
            f"Moderate compression anomaly in ELA (ELA score {ela_score}) - localized recompression observed"
        )

    is_tampered = tamper_score >= 0.50

    return {
        "tamper_score": tamper_score,
        "is_tampered": is_tampered,
        "ela": {
            "score": ela_score,
            "stats": ela_stats,
            "heatmap_base64": heatmap_b64
        },
        "metadata": {
            "score": meta_score,
            "details": meta_dict
        },
        "flagged_signals": tamper_flags
    }
