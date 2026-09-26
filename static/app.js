/**
 * AuthDoc — Frontend Dashboard Controller
 * Manages 1-click hackathon demo scenarios, live webcam stream,
 * forensic visualization, ELA heatmaps, and ICAO 9303 checksum tracing.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const clockEl = document.getElementById("clock-display");
  const scenarioBtns = document.querySelectorAll(".scenario-btn");
  const docFileInput = document.getElementById("doc-file-input");
  const docDropzone = document.getElementById("doc-dropzone");
  const docPrompt = document.getElementById("doc-dropzone-prompt");
  const docPreviewContainer = document.getElementById("doc-preview-container");
  const docPreviewImg = document.getElementById("doc-preview-img");
  const btnClearDoc = document.getElementById("btn-clear-doc");

  // Webcam Elements
  const tabWebcam = document.getElementById("tab-webcam");
  const tabUpload = document.getElementById("tab-upload");
  const webcamSection = document.getElementById("webcam-section");
  const selfieDropzone = document.getElementById("selfie-dropzone");
  const selfieFileInput = document.getElementById("selfie-file-input");
  const videoEl = document.getElementById("webcam-video");
  const canvasEl = document.getElementById("webcam-canvas");
  const webcamPlaceholder = document.getElementById("webcam-placeholder");
  const webcamActions = document.getElementById("webcam-actions");
  const btnStartCamera = document.getElementById("btn-start-camera");
  const btnCaptureSelfie = document.getElementById("btn-capture-selfie");
  const btnStopCamera = document.getElementById("btn-stop-camera");
  const selfiePreviewContainer = document.getElementById("selfie-preview-container");
  const selfiePreviewImg = document.getElementById("selfie-preview-img");
  const btnClearSelfie = document.getElementById("btn-clear-selfie");

  // Verification & Display Elements
  const verifyForm = document.getElementById("verify-form");
  const btnRunVerify = document.getElementById("btn-run-verify");
  const verifySpinner = document.getElementById("verify-spinner");
  const riskGauge = document.getElementById("risk-gauge");
  const gaugeScore = document.getElementById("gauge-score");
  const verdictDecision = document.getElementById("verdict-decision");
  const verdictText = document.getElementById("verdict-text");
  const overallBadge = document.getElementById("overall-status-badge");

  // Breakdown Bars
  const scoreValText = document.getElementById("score-val-text");
  const barVal = document.getElementById("bar-val");
  const scoreTamperText = document.getElementById("score-tamper-text");
  const barTamper = document.getElementById("bar-tamper");
  const scoreFaceText = document.getElementById("score-face-text");
  const barFace = document.getElementById("bar-face");
  const reasonsContainer = document.getElementById("reasons-list-container");

  // Detail Tabs
  const navTabs = document.querySelectorAll(".nav-tab");
  const tabPanes = document.querySelectorAll(".tab-pane");

  // Identity Fields
  const fName = document.getElementById("f-name");
  const fDocNum = document.getElementById("f-docnum");
  const fNat = document.getElementById("f-nat");
  const fDob = document.getElementById("f-dob");
  const fExp = document.getElementById("f-exp");
  const fSex = document.getElementById("f-sex");
  const fIssuer = document.getElementById("f-issuer");
  const fEngine = document.getElementById("f-engine");
  const checkdigitTbody = document.getElementById("checkdigit-tbody");
  const mrzStreamDisplay = document.getElementById("mrz-stream-display");

  // ELA Views
  const elaOrigView = document.getElementById("ela-orig-view");
  const elaHeatmapView = document.getElementById("ela-heatmap-view");
  const metricPar = document.getElementById("metric-par");
  const metricElaScore = document.getElementById("metric-ela-score");
  const metricExifStatus = document.getElementById("metric-exif-status");
  const metricSoftwareDesc = document.getElementById("metric-software-desc");

  // Biometrics
  const bioDocFace = document.getElementById("bio-doc-face");
  const bioSelfieFace = document.getElementById("bio-selfie-face");
  const bioSimVal = document.getElementById("bio-sim-val");
  const bioMatchVerdict = document.getElementById("bio-match-verdict");
  const bioEngineName = document.getElementById("bio-engine-name");
  const bioDistance = document.getElementById("bio-distance");
  const bioThreshold = document.getElementById("bio-threshold");

  // Watchlist Modal
  const btnOpenWatchlist = document.getElementById("btn-open-watchlist");
  const btnCloseWatchlist = document.getElementById("btn-close-watchlist");
  const watchlistModal = document.getElementById("watchlist-modal");
  const modalBlacklistTbody = document.getElementById("modal-blacklist-tbody");
  const modalWatchlistTbody = document.getElementById("modal-watchlist-tbody");

  let webcamStream = null;
  let capturedSelfieBase64 = null;

  // 1. Live UTC Clock
  function updateClock() {
    const now = new Date();
    clockEl.textContent = now.toISOString().substring(11, 19) + " UTC";
  }
  setInterval(updateClock, 1000);
  updateClock();

  // 2. Tab Navigation
  navTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      navTabs.forEach(t => t.classList.remove("active"));
      tabPanes.forEach(p => p.classList.remove("active"));
      tab.classList.add("active");
      const targetPane = document.getElementById(tab.getAttribute("data-tab"));
      if (targetPane) targetPane.classList.add("active");
    });
  });

  // 3. Document Drag & Drop
  docFileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      showDocPreview(e.target.files[0]);
    }
  });

  function showDocPreview(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      docPreviewImg.src = e.target.result;
      docPrompt.classList.add("hidden");
      docPreviewContainer.classList.remove("hidden");
    };
    reader.readAsDataURL(file);
  }

  btnClearDoc.addEventListener("click", (e) => {
    e.stopPropagation();
    docFileInput.value = "";
    docPreviewImg.src = "";
    docPreviewContainer.classList.add("hidden");
    docPrompt.classList.remove("hidden");
  });

  // 4. Webcam Capture Logic
  tabWebcam.addEventListener("click", () => {
    tabWebcam.classList.add("active");
    tabUpload.classList.remove("active");
    webcamSection.classList.remove("hidden");
    selfieDropzone.classList.add("hidden");
  });

  tabUpload.addEventListener("click", () => {
    tabUpload.classList.add("active");
    tabWebcam.classList.remove("active");
    selfieDropzone.classList.remove("hidden");
    webcamSection.classList.add("hidden");
    stopWebcam();
  });

  btnStartCamera.addEventListener("click", async () => {
    try {
      webcamStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
      videoEl.srcObject = webcamStream;
      webcamPlaceholder.classList.add("hidden");
      webcamActions.classList.remove("hidden");
    } catch (err) {
      alert("Unable to access camera: " + err.message);
    }
  });

  btnStopCamera.addEventListener("click", stopWebcam);

  function stopWebcam() {
    if (webcamStream) {
      webcamStream.getTracks().forEach(track => track.stop());
      webcamStream = null;
    }
    videoEl.srcObject = null;
    webcamPlaceholder.classList.remove("hidden");
    webcamActions.classList.add("hidden");
  }

  btnCaptureSelfie.addEventListener("click", () => {
    if (!videoEl.videoWidth) return;
    canvasEl.width = videoEl.videoWidth;
    canvasEl.height = videoEl.videoHeight;
    const ctx = canvasEl.getContext("2d");
    ctx.drawImage(videoEl, 0, 0);
    capturedSelfieBase64 = canvasEl.toDataURL("image/jpeg", 0.9);
    selfiePreviewImg.src = capturedSelfieBase64;
    selfiePreviewContainer.classList.remove("hidden");
    stopWebcam();
  });

  btnClearSelfie.addEventListener("click", () => {
    capturedSelfieBase64 = null;
    selfiePreviewImg.src = "";
    selfiePreviewContainer.classList.add("hidden");
    selfieFileInput.value = "";
  });

  selfieFileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      const reader = new FileReader();
      reader.onload = (evt) => {
        capturedSelfieBase64 = evt.target.result;
        selfiePreviewImg.src = capturedSelfieBase64;
        selfiePreviewContainer.classList.remove("hidden");
      };
      reader.readAsDataURL(e.target.files[0]);
    }
  });

  // 5. 1-Click Demo Scenarios
  scenarioBtns.forEach(btn => {
    btn.addEventListener("click", async () => {
      const scenarioId = btn.getAttribute("data-scenario");
      scenarioBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      await loadAndVerifyScenario(scenarioId);
    });
  });

  async function loadAndVerifyScenario(scenarioId) {
    setLoadingState(true);
    try {
      const res = await fetch(`/api/samples/verify/${scenarioId}`, { method: "POST" });
      if (!res.ok) throw new Error("Failed to load scenario: " + res.statusText);
      const data = await res.json();
      renderVerificationResults(data);
    } catch (err) {
      alert("Error executing scenario: " + err.message);
    } finally {
      setLoadingState(false);
    }
  }

  // 6. Manual Verification Form Submission
  verifyForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!docFileInput.files[0] && !docPreviewImg.src) {
      alert("Please upload a document image first or select a demo scenario.");
      return;
    }

    setLoadingState(true);
    const formData = new FormData();
    if (docFileInput.files[0]) {
      formData.append("document", docFileInput.files[0]);
    } else {
      // If image loaded from preview, convert base64 to blob
      const blob = await fetch(docPreviewImg.src).then(r => r.blob());
      formData.append("document", blob, "uploaded_doc.jpg");
    }

    if (capturedSelfieBase64) {
      formData.append("selfie_base64", capturedSelfieBase64);
    } else if (selfieFileInput.files[0]) {
      formData.append("selfie", selfieFileInput.files[0]);
    }

    try {
      const res = await fetch("/api/verify", {
        method: "POST",
        body: formData
      });
      if (!res.ok) throw new Error("Audit failed: " + res.statusText);
      const data = await res.json();
      renderVerificationResults(data);
    } catch (err) {
      alert("Verification error: " + err.message);
    } finally {
      setLoadingState(false);
    }
  });

  function setLoadingState(loading) {
    if (loading) {
      btnRunVerify.disabled = true;
      verifySpinner.classList.remove("hidden");
      btnRunVerify.querySelector(".btn-text").textContent = "AUDITING FORENSIC SIGNALS...";
    } else {
      btnRunVerify.disabled = false;
      verifySpinner.classList.add("hidden");
      btnRunVerify.querySelector(".btn-text").textContent = "⚡ RUN FORENSIC AUDIT";
    }
  }

  // 7. Render Complete Results Payload
  function renderVerificationResults(data) {
    const risk = data.risk || {};
    const ocr = data.ocr || {};
    const val = data.validation || {};
    const tamper = data.tamper || {};
    const face = data.face || {};

    // Document & Selfie Previews
    if (data.document_preview_base64) {
      docPreviewImg.src = data.document_preview_base64;
      docPrompt.classList.add("hidden");
      docPreviewContainer.classList.remove("hidden");
      elaOrigView.src = data.document_preview_base64;
    }
    if (data.selfie_preview_base64) {
      selfiePreviewImg.src = data.selfie_preview_base64;
      selfiePreviewContainer.classList.remove("hidden");
    }

    // Risk Gauge & Decision
    const scoreVal = risk.overall_risk_score !== undefined ? risk.overall_risk_score : 50;
    gaugeScore.textContent = Math.round(scoreVal);
    const deg = Math.round((scoreVal / 100) * 360);
    riskGauge.style.setProperty("--risk-deg", `${deg}deg`);

    const verdict = risk.verdict || "UNKNOWN";
    verdictDecision.textContent = verdict.replace("_", " ");
    verdictDecision.className = "verdict-status-title " + (verdict === "APPROVED" ? "approved" : (verdict === "MANUAL_REVIEW" ? "review" : "rejected"));
    verdictText.textContent = risk.verdict_text || "";

    overallBadge.textContent = verdict;
    overallBadge.className = "badge " + (verdict === "APPROVED" ? "badge-subtle" : (verdict === "MANUAL_REVIEW" ? "badge-accent" : "badge-accent"));

    // Breakdown Bars
    const bd = risk.breakdown || {};
    const valRisk = bd.validation ? bd.validation.risk_contribution : 0;
    const tamperRisk = bd.tampering ? bd.tampering.risk_contribution : 0;
    const faceRisk = bd.biometrics ? bd.biometrics.risk_contribution : 0;

    scoreValText.textContent = `${valRisk}% Risk`;
    barVal.style.width = `${Math.min(100, valRisk * 2.5)}%`;
    barVal.style.backgroundColor = valRisk > 10 ? "var(--color-fail)" : "var(--color-pass)";

    scoreTamperText.textContent = `${tamperRisk}% Risk`;
    barTamper.style.width = `${Math.min(100, tamperRisk * 2.5)}%`;
    barTamper.style.backgroundColor = tamperRisk > 15 ? "var(--color-fail)" : "var(--color-pass)";

    scoreFaceText.textContent = `${faceRisk}% Risk`;
    barFace.style.width = `${Math.min(100, faceRisk * 2.5)}%`;
    barFace.style.backgroundColor = faceRisk > 10 ? "var(--color-fail)" : "var(--color-pass)";

    // Flagged Reasons
    renderFlaggedReasons(risk.flagged_reasons || []);

    // Identity Fields
    const fields = ocr.fields || {};
    fName.textContent = fields.full_name || fields.surname || "NOT DETECTED";
    fDocNum.textContent = fields.document_number || "NOT DETECTED";
    fNat.textContent = fields.nationality || "USA";
    fDob.textContent = fields.date_of_birth_formatted || fields.date_of_birth || "--";
    fExp.textContent = fields.expiry_date_formatted || fields.expiry_date || "--";
    fSex.textContent = fields.sex || "Unspecified";
    fIssuer.textContent = fields.issuing_country || "USA";
    fEngine.textContent = ocr.ocr_engine || "heuristic";

    // ICAO 9303 Checksum Table
    renderCheckDigitsTable(val.check_digits || {});

    // Raw MRZ Stream
    const rawLines = ocr.raw_mrz_lines || [];
    mrzStreamDisplay.textContent = rawLines.length > 0 ? rawLines.join("\n") : "No MRZ lines detected.";

    // ELA Visualizer
    if (tamper.ela && tamper.ela.heatmap_base64) {
      elaHeatmapView.src = tamper.ela.heatmap_base64;
    }
    const stats = (tamper.ela && tamper.ela.stats) || {};
    metricPar.textContent = stats.peak_to_avg_ratio ? `${stats.peak_to_avg_ratio}x` : "--";
    metricElaScore.textContent = tamper.ela && tamper.ela.score !== undefined ? tamper.ela.score : "--";

    const meta = tamper.metadata || {};
    const software = meta.details && meta.details.tampering_software_detected;
    if (software && software.length > 0) {
      metricExifStatus.textContent = "TAMPERED ⚠️";
      metricExifStatus.style.color = "var(--color-fail)";
      metricSoftwareDesc.textContent = software.join(", ");
    } else {
      metricExifStatus.textContent = "CLEAN ✅";
      metricExifStatus.style.color = "var(--color-pass)";
      metricSoftwareDesc.textContent = meta.details && meta.details.camera_hardware ? meta.details.camera_hardware : "Standard Camera EXIF";
    }

    // Biometrics Card
    if (face.doc_face_crop_base64) {
      bioDocFace.src = face.doc_face_crop_base64;
    } else {
      bioDocFace.src = data.document_preview_base64 || "";
    }

    if (face.selfie_face_crop_base64) {
      bioSelfieFace.src = face.selfie_face_crop_base64;
    } else if (data.selfie_preview_base64) {
      bioSelfieFace.src = data.selfie_preview_base64;
    }

    const simScore = face.face_match_score !== undefined ? Math.round(face.face_match_score * 100) : 0;
    bioSimVal.textContent = `${simScore}% SIMILARITY`;
    bioMatchVerdict.textContent = face.is_match ? "VERIFIED MATCH" : "MISMATCH";
    bioMatchVerdict.style.color = face.is_match ? "var(--color-pass)" : "var(--color-fail)";
    bioEngineName.textContent = `Engine: ${face.engine || 'DeepFace'}`;
    bioDistance.textContent = face.distance !== undefined ? face.distance : "--";
    bioThreshold.textContent = `Threshold: ${face.threshold !== undefined ? face.threshold : '0.40'}`;
  }

  function renderFlaggedReasons(reasons) {
    if (!reasons || reasons.length === 0) {
      reasonsContainer.innerHTML = `<div class="reason-card info"><div class="reason-header">STATUS: ALL CLEAR</div><div class="reason-body">No critical tamper signals, expired credentials, or watchlist matches identified.</div></div>`;
      return;
    }
    reasonsContainer.innerHTML = reasons.map(r => {
      const cls = r.severity === "CRITICAL" ? "critical" : (r.severity === "WARNING" ? "warning" : "info");
      return `
        <div class="reason-card ${cls}">
          <div class="reason-header">
            <span>[${r.category}] ${r.severity}</span>
            <span>${r.module}</span>
          </div>
          <div class="reason-body">${escapeHtml(r.message)}</div>
        </div>
      `;
    }).join("");
  }

  function renderCheckDigitsTable(checkDigits) {
    const keys = Object.keys(checkDigits);
    if (keys.length === 0) {
      checkdigitTbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No MRZ check digits found.</td></tr>`;
      return;
    }

    checkdigitTbody.innerHTML = keys.map(k => {
      const item = checkDigits[k];
      const isPass = item.is_valid;
      return `
        <tr>
          <td><strong>${escapeHtml(item.field)}</strong></td>
          <td class="mono">${escapeHtml(item.raw_data || '')}</td>
          <td class="mono"><strong>${item.calculated_check_digit}</strong></td>
          <td class="mono">${item.expected_check_digit}</td>
          <td>
            <span class="badge-status ${isPass ? 'pass' : 'fail'}">
              ${isPass ? 'PASS ✓' : 'FAIL ✗ (MISMATCH)'}
            </span>
          </td>
        </tr>
      `;
    }).join("");
  }

  // 8. Watchlist Modal Logic
  btnOpenWatchlist.addEventListener("click", async () => {
    watchlistModal.classList.remove("hidden");
    try {
      const res = await fetch("/api/blacklist");
      const data = await res.json();
      renderWatchlistModal(data);
    } catch (err) {
      console.error(err);
    }
  });

  btnCloseWatchlist.addEventListener("click", () => {
    watchlistModal.classList.add("hidden");
  });

  function renderWatchlistModal(data) {
    const docs = data.documents || [];
    const persons = data.persons || [];

    modalBlacklistTbody.innerHTML = docs.map(d => `
      <tr>
        <td class="mono"><strong>${escapeHtml(d.doc_number)}</strong></td>
        <td>${escapeHtml(d.country)}</td>
        <td>${escapeHtml(d.reason)}</td>
        <td class="mono">${escapeHtml(d.flagged_date)}</td>
        <td><span class="btn-tag fail">${escapeHtml(d.severity)}</span></td>
      </tr>
    `).join("");

    modalWatchlistTbody.innerHTML = persons.map(p => `
      <tr>
        <td><strong>${escapeHtml(p.name)}</strong></td>
        <td>${escapeHtml(p.nationality || '')}</td>
        <td class="mono">${escapeHtml(p.dob || '')}</td>
        <td>${escapeHtml(p.reason)}</td>
        <td><span class="btn-tag ${p.risk_level === 'CRITICAL' ? 'crit' : 'fail'}">${escapeHtml(p.risk_level)}</span></td>
      </tr>
    `).join("");
  }

  function escapeHtml(text) {
    if (!text) return "";
    return text.toString()
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Auto-load Scenario 1 upon initial page load for instant live demonstration!
  setTimeout(() => {
    const btnFirst = document.querySelector(".scenario-btn");
    if (btnFirst) btnFirst.click();
  }, 350);
});
