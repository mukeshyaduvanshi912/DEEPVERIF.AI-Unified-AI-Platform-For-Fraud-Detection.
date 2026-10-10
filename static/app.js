// ---------- Tab switching ----------
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(btn.dataset.tab).classList.add("active");
    if (btn.dataset.tab === "logs") loadLogs();
    if (btn.dataset.tab === "exposure") loadExposure();
  });
});

// ---------- LIVENESS / rPPG ----------
const video = document.getElementById("webcam");
const startBtn = document.getElementById("startLiveness");
const progress = document.getElementById("livenessProgress");
const bar = document.getElementById("livenessBar");
const livenessResult = document.getElementById("livenessResult");
let stream = null;

async function initWebcam() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { width: 320, height: 240 } });
    video.srcObject = stream;
  } catch (e) {
    livenessResult.innerHTML = `<p class="verdict-warn">⚠️ Camera access denied/unavailable: ${e.message}</p>`;
  }
}
initWebcam();

// ---- mode: own camera vs caller's video via screen share ----
const modeScreenRadio = document.getElementById("modeScreen");
const screenOpts = document.getElementById("screenOpts");
const screenSupported = !!(navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia);
if (!screenSupported) {
  modeScreenRadio.disabled = true;
  document.getElementById("screenUnsupported").style.display = "block";
}
document.querySelectorAll('input[name="liveMode"]').forEach(r => r.addEventListener("change", () => {
  screenOpts.style.display = currentMode() === "screen" ? "block" : "none";
}));
function currentMode() { return document.querySelector('input[name="liveMode"]:checked').value; }

function cropRect(vw, vh, region) {
  if (region === "center") return [vw * 0.25, vh * 0.1, vw * 0.5, vh * 0.8];
  if (region === "left") return [0, 0, vw * 0.5, vh];
  if (region === "right") return [vw * 0.5, 0, vw * 0.5, vh];
  return [0, 0, vw, vh];
}

startBtn.addEventListener("click", async () => {
  const mode = currentMode();
  let screenStream = null;
  try {
    if (mode === "screen") {
      screenStream = await navigator.mediaDevices.getDisplayMedia({ video: { frameRate: 15 }, audio: false });
      video.srcObject = screenStream;
      await new Promise(r => { video.onloadedmetadata = r; setTimeout(r, 1500); });
      await video.play().catch(() => {});
    } else if (!stream) { await initWebcam(); if (!stream) return; }
  } catch (e) {
    livenessResult.innerHTML = `<p class="verdict-warn">⚠️ Screen share cancelled / not allowed: ${e.message}</p>`;
    return;
  }

  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  const region = document.getElementById("screenRegion").value;
  const vw = video.videoWidth || 320, vh = video.videoHeight || 240;
  const [sx, sy, sw, sh] = mode === "screen" ? cropRect(vw, vh, region) : [0, 0, vw, vh];
  if (mode === "screen") {                       // bigger frames so a small caller face is still detectable
    canvas.width = Math.min(800, Math.round(sw)); canvas.height = Math.round(canvas.width * sh / sw);
  } else { canvas.width = 320; canvas.height = 240; }

  const frames = [];
  const totalFrames = 60; // ~6 seconds at ~10fps
  const targetFps = 10;

  progress.style.display = "block";
  livenessResult.innerHTML = `<p class="placeholder">Scanning... ${mode === "screen" ? "keep the caller's tile visible on screen." : "hold still."}</p>`;
  startBtn.disabled = true;

  const t0 = performance.now();
  for (let i = 0; i < totalFrames; i++) {
    ctx.drawImage(video, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height);
    frames.push(canvas.toDataURL("image/jpeg", 0.7));
    bar.style.width = `${((i + 1) / totalFrames) * 100}%`;
    await new Promise(r => setTimeout(r, 1000 / targetFps));
  }
  const fps = Math.round((totalFrames / ((performance.now() - t0) / 1000)) * 10) / 10;   // real measured fps -> accurate BPM

  if (screenStream) {                             // stop sharing, bring own camera preview back
    screenStream.getTracks().forEach(t => t.stop());
    video.srcObject = stream || null;
  }

  livenessResult.innerHTML = `<p class="placeholder">Analyzing pulse signal...</p>`;
  const res = await fetch("/api/liveness/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ frames, fps, source: mode })
  });
  const data = await res.json();
  startBtn.disabled = false;
  progress.style.display = "none";
  bar.style.width = "0%";
  const caveat = data.caveat ? `<p class="hint">ℹ️ ${escapeHtml(data.caveat)}</p>` : "";

  if (data.status === "REAL") {
    livenessResult.innerHTML = `
      <p class="verdict-real">✅ REAL — Live Pulse Detected${mode === "screen" ? " (caller)" : ""}</p>
      <p>Estimated heart rate: <b>${data.estimated_bpm} BPM</b></p>
      <p>Confidence: ${(data.confidence * 100).toFixed(0)}%</p>
      <p class="hint">${escapeHtml(data.reason)}</p>${caveat}`;
  } else if (data.status === "SUSPICIOUS") {
    livenessResult.innerHTML = `
      <p class="verdict-warn">🟡 PULSE NOT DETECTED — be careful</p>
      <p class="hint">${escapeHtml(data.reason)}</p>${caveat}
      <div class="advice-box">Do not decide on this alone. Check the Shield tab for what the caller is asking, never send money on a call, and verify through an official number. 1930 = National Cyber Helpline.</div>`;
  } else if (data.status === "FAKE") {
    livenessResult.innerHTML = `
      <p class="verdict-fake">⚠️ FAKE / SPOOF SUSPECTED</p>
      <p>Confidence: ${(data.confidence * 100).toFixed(0)}%</p>
      <p class="hint">${escapeHtml(data.reason)}</p>
      <div class="advice-box">Disconnect the call immediately. Verify identity through an official channel. Report to 1930 (National Cyber Helpline).</div>`;
  } else {
    livenessResult.innerHTML = `<p class="verdict-warn">⚠️ INCONCLUSIVE</p><p class="hint">${escapeHtml(data.reason || "")}</p>${caveat}`;
  }
});

// ---------- DOCUMENT ----------
const docInput = document.getElementById("docInput");
const docPreview = document.getElementById("docPreview");
const docFileLabel = document.getElementById("docFileLabel");
const docResult = document.getElementById("docResult");
const downloadDocReportBtn = document.getElementById("downloadDocReport");
let docB64 = null;
let docIsPdf = false;
let lastDocReportText = null;
let lastDocFileName = "document";

docInput.addEventListener("change", () => {
  const file = docInput.files[0];
  if (!file) return;
  docIsPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  lastDocFileName = file.name.replace(/\.[^/.]+$/, "") || "document";
  const reader = new FileReader();
  reader.onload = e => {
    docB64 = e.target.result;
    if (docIsPdf) {
      docPreview.style.display = "none";
      docFileLabel.textContent = `📄 ${file.name} selected (PDF)`;
      docFileLabel.style.display = "block";
    } else {
      docPreview.src = docB64;
      docPreview.style.display = "block";
      docFileLabel.style.display = "none";
    }
  };
  reader.readAsDataURL(file);
});

function verdictIcon(score) {
  return score >= 55 ? "⚠️" : (score >= 30 ? "🟡" : "✅");
}
function verdictClass(score) {
  return score >= 55 ? "verdict-fake" : (score >= 30 ? "verdict-warn" : "verdict-real");
}

function renderSourceBlock(source) {
  if (!source) return "";
  return `
    <div class="source-block">
      <h4>🔎 Likely source of the file</h4>
      <p><b>${source.detected_source}</b> &nbsp; <span class="hint">(confidence: ${source.confidence})</span></p>
      ${source.evidence && source.evidence.length ? `<ul class="flag-list">${source.evidence.map(e => `<li>${e}</li>`).join("")}</ul>` : ""}
    </div>`;
}

document.getElementById("analyzeDoc").addEventListener("click", async () => {
  if (!docB64) { docResult.innerHTML = `<p class="verdict-warn">Please upload an image or PDF first.</p>`; return; }
  docResult.innerHTML = `<p class="placeholder">Analyzing${docIsPdf ? " PDF (rendering pages)" : ""}...</p>`;
  downloadDocReportBtn.style.display = "none";

  const payload = docIsPdf ? { pdf: docB64 } : { image: docB64 };
  const res = await fetch("/api/document/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const data = await res.json();

  if (data.error) {
    docResult.innerHTML = `<p class="verdict-warn">⚠️ ${data.error}</p>`;
    return;
  }

  lastDocReportText = data.report_text || null;

  if (data.file_kind === "pdf") {
    const cls = verdictClass(data.fraud_score);
    const metaRows = data.metadata ? `
      <p class="hint">Producer: ${data.metadata.producer || "—"} &nbsp;|&nbsp; Creator: ${data.metadata.creator || "—"}</p>` : "";
    docResult.innerHTML = `
      <p class="${cls}">${verdictIcon(data.fraud_score)} ${data.verdict}</p>
      <p>Fraud Score: <b>${data.fraud_score}%</b> &nbsp; (${data.page_count} page${data.page_count > 1 ? "s" : ""} in PDF)</p>
      ${metaRows}
      ${data.metadata_flags.length ? `<ul class="flag-list">${data.metadata_flags.map(f => `<li>${f}</li>`).join("")}</ul>` : ""}
      ${renderSourceBlock(data.source_analysis)}
      <h4>📄 Per-page Error Level Analysis</h4>
      ${data.pages.map(p => `
        <div class="pdf-page-block">
          <p><b>Page ${p.page}</b> — suspicious area: ${p.suspicious_area_pct}%, error variance: ${p.error_std}</p>
          <img src="${p.heatmap_image_b64}" style="max-width:100%;margin-top:6px;border-radius:8px;" alt="Page ${p.page} ELA heatmap">
        </div>`).join("")}
      <p class="hint">Red regions show compression-level inconsistency (possible edit) on each rendered page.</p>`;
  } else {
    const cls = verdictClass(data.fraud_score);
    docResult.innerHTML = `
      <p class="${cls}">${verdictIcon(data.fraud_score)} ${data.verdict}</p>
      <p>Fraud Score: <b>${data.fraud_score}%</b></p>
      <p>Suspicious area: ${data.suspicious_area_pct}% of image</p>
      ${data.metadata_flags.length ? `<ul class="flag-list">${data.metadata_flags.map(f => `<li>${f}</li>`).join("")}</ul>` : ""}
      ${renderSourceBlock(data.source_analysis)}
      <img src="${data.heatmap_image_b64}" style="max-width:100%;margin-top:10px;border-radius:8px;" alt="ELA heatmap">
      <p class="hint">Red regions show compression-level inconsistency (possible edit).</p>`;
  }

  if (lastDocReportText) downloadDocReportBtn.style.display = "inline-block";
});

downloadDocReportBtn.addEventListener("click", () => {
  if (!lastDocReportText) return;
  const blob = new Blob([lastDocReportText], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${lastDocFileName}-forensic-report.txt`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
});

// ---------- SMS ----------
document.querySelectorAll(".sample-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.getElementById("smsInput").value = btn.dataset.text;
  });
});

const downloadSmsReportBtn = document.getElementById("downloadSmsReport");
let lastSmsReportText = null;

function renderSmsSourceBlock(source) {
  if (!source) return "";
  const cls = source.mismatch_notes && source.mismatch_notes.length ? "verdict-fake" : "";
  return `
    <div class="source-block">
      <h4>🔎 Claimed source / sender</h4>
      <p class="${cls}"><b>${source.source_verdict}</b> &nbsp; <span class="hint">(confidence: ${source.confidence})</span></p>
      ${source.sender_signature_found ? `<p class="hint">Sign-off found in text: "-${source.sender_signature_found}"</p>` : ""}
      ${source.mismatch_notes && source.mismatch_notes.length ? `<ul class="flag-list">${source.mismatch_notes.map(m => `<li>${m}</li>`).join("")}</ul>` : ""}
    </div>`;
}

function renderLinkHistoryBlock(links) {
  if (!links || !links.length) return "";
  return `
    <div class="source-block">
      <h4>🔗 Link history</h4>
      ${links.map(l => `
        <div class="pdf-page-block">
          <p><b>${l.original_url}</b></p>
          ${l.resolved_live && l.final_url && l.final_url !== l.original_url
            ? `<p class="hint">Resolves to: ${l.final_url}</p>` : ""}
          <ul class="flag-list">${l.notes.map(n => `<li>${n}</li>`).join("")}</ul>
        </div>`).join("")}
    </div>`;
}

document.getElementById("analyzeSms").addEventListener("click", async () => {
  const text = document.getElementById("smsInput").value.trim();
  const smsResult = document.getElementById("smsResult");
  if (!text) { smsResult.innerHTML = `<p class="verdict-warn">Please enter an SMS text.</p>`; return; }
  smsResult.innerHTML = `<p class="placeholder">Analyzing (checking any links live, this can take a few seconds)...</p>`;
  downloadSmsReportBtn.style.display = "none";
  const res = await fetch("/api/sms/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text })
  });
  const data = await res.json();
  lastSmsReportText = data.report_text || null;
  const cls = data.fraud_score >= 55 ? "verdict-fake" : (data.fraud_score >= 30 ? "verdict-warn" : "verdict-real");
  smsResult.innerHTML = `
    <p class="${cls}">${data.fraud_score >= 55 ? "⚠️" : data.fraud_score >= 30 ? "🟡" : "✅"} ${data.verdict}</p>
    <p>Fake likelihood: <b>${data.fake_percent}%</b> &nbsp;|&nbsp; Real likelihood: <b>${data.real_percent}%</b> &nbsp; <span class="hint">(ML model: ${data.ml_probability}%)</span></p>
    ${data.red_flags.length ? `<ul class="flag-list">${data.red_flags.map(f => `<li>${f}</li>`).join("")}</ul>` : "<p>No red flags detected.</p>"}
    ${renderSmsSourceBlock(data.source_analysis)}
    ${renderLinkHistoryBlock(data.link_analysis)}
    <div class="advice-box">${data.advice}</div>`;
  if (lastSmsReportText) downloadSmsReportBtn.style.display = "inline-block";
  addAiButton(smsResult, text, data.fraud_score, data.red_flags);
  addFeedback(smsResult, "sms", data.fraud_score >= 55 ? "HIGH" : data.fraud_score >= 30 ? "MEDIUM" : "LOW", data.fraud_score);
  if (data.fraud_score >= 30) {
    raiseAlert({
      level: data.fraud_score >= 55 ? "HIGH" : "MEDIUM",
      title: data.fraud_score >= 55 ? "🚨 This SMS looks FAKE / a scam" : "🟡 This SMS looks suspicious",
      reasons: [...(data.red_flags || []), ...((data.source_analysis && data.source_analysis.mismatch_notes) || [])],
    });
  }
});

downloadSmsReportBtn.addEventListener("click", () => {
  if (!lastSmsReportText) return;
  const blob = new Blob([lastSmsReportText], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "sms-forensic-report.txt";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
});

// ---------- LOGS ----------
async function loadLogs() {
  const res = await fetch("/api/logs");
  const data = await res.json();
  const statusEl = document.getElementById("chainStatus");
  statusEl.innerHTML = data.chain_status.valid
    ? `<span class="chain-valid">✅ Hash chain verified — ${data.chain_status.count} records, no tampering detected.</span>`
    : `<span class="chain-broken">⚠️ Chain broken at record ${data.chain_status.broken_at}! Tampering detected.</span>`;

  const listEl = document.getElementById("logList");
  listEl.innerHTML = data.logs.map(r => `
    <div class="log-entry">
      <span class="mod">[${r.entry.module}]</span> ${new Date(r.entry.timestamp * 1000).toLocaleString()}<br>
      hash: ${r.hash.slice(0, 24)}...<br>
      ${JSON.stringify(r.entry.result).slice(0, 140)}
    </div>`).join("") || "<p class='hint'>No logs yet — run a detection test first.</p>";
}

document.getElementById("refreshLogs").addEventListener("click", loadLogs);

// ---------- DIGITAL ARREST SHIELD ----------
const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
const transcriptEl = document.getElementById("transcript");
const shieldResult = document.getElementById("shieldResult");
const shieldBanner = document.getElementById("shieldBanner");
const micBtn = document.getElementById("micBtn");
let recognizer = null, listening = false, committedText = "", lastShieldRisk = "NONE";
let modalShown = false, analyzeTimer = null;

const SCAM_SAMPLE = "This is a CBI officer speaking. A parcel in your name has been seized and it contains drugs. " +
  "An arrest warrant has been issued against you and you are under digital arrest. Do not cut the call and do not tell anyone, " +
  "this is a national security case. Transfer your money to the RBI safe account immediately for verification.";
const POLITE_SAMPLE = "Good afternoon sir, I am calling from the cyber crime branch. Please do not worry at all, I am only here to help you. " +
  "Just send the money to the safe account for verification, it will be returned to you later. There is no need to tell anyone right now.";
const CASE_STUDY_SAMPLE = "नमस्ते, मैं एटीएस पुणे से अभिषेक यादव बोल रहा हूँ। आपका नंबर आतंकवादी गतिविधियों में पाया गया है और आपके खिलाफ मनी लॉन्ड्रिंग का केस है। " +
  "एनआईए की जांच चल रही है, सुप्रीम कोर्ट का अरेस्ट वारंट निकला है। आप डिजिटल अरेस्ट में हैं, वीडियो कॉल मत काटना और किसी को मत बताना। " +
  "अपनी एफडी तोड़कर पैसे ट्रांसफर करो, जांच के बाद वापस मिल जाएंगे।";
const SAFE_SAMPLE = "Hi, this is Riya from the college office. Your exam form is approved, you can collect the hall ticket tomorrow.";

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function highlightText(text, phrases) {
  let out = escapeHtml(text);
  phrases.forEach(p => {
    const safe = escapeHtml(p).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    out = out.replace(new RegExp(safe, "gi"), m => `<mark>${m}</mark>`);
  });
  return out;
}

if (!SpeechRec) {
  document.getElementById("micSupport").textContent =
    "Live mic needs Chrome / Edge. In this browser use the sample buttons or paste call text.";
  micBtn.disabled = true;
}

function showModal(data) {
  document.getElementById("modalAwareness").textContent = data.awareness || "";
  document.getElementById("modalSteps").innerHTML = (data.action_steps || []).map(s => `<li>${escapeHtml(s)}</li>`).join("");
  document.getElementById("scamModal").style.display = "flex";
}
document.getElementById("modalClose").addEventListener("click", () => {
  document.getElementById("scamModal").style.display = "none";
});

async function analyzeTranscript() {
  const text = transcriptEl.value.trim();
  if (!text) { shieldResult.innerHTML = `<p class="placeholder">Waiting for call audio / text...</p>`; return; }
  const res = await fetch("/api/shield/transcript", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text })
  });
  const d = await res.json();
  lastShieldRisk = d.risk_level;

  const cls = d.risk_level === "HIGH" ? "verdict-fake" : d.risk_level === "MEDIUM" ? "verdict-warn" : "verdict-real";
  const icon = d.risk_level === "HIGH" ? "🚨" : d.risk_level === "MEDIUM" ? "🟡" : "✅";
  shieldResult.innerHTML = `
    <p class="${cls}">${icon} ${d.risk_level} RISK — ${d.risk_score}%</p>
    <p>${escapeHtml(d.message)}</p>
    ${d.tone_note ? `<p class="hint">🎭 ${escapeHtml(d.tone_note)}</p>` : ""}
    ${d.matched_categories.length ? `<ul class="flag-list">${d.matched_categories.map(m =>
      `<li>${escapeHtml(m.label)}: <i>${m.phrases.map(escapeHtml).join(", ")}</i></li>`).join("")}</ul>` : ""}
    ${d.highlights.length ? `<div class="hl-box">${highlightText(text, d.highlights)}</div>` : ""}
    ${d.action_steps ? `<div class="advice-box"><b>${escapeHtml(d.awareness)}</b><ol>${d.action_steps.map(s => `<li>${escapeHtml(s)}</li>`).join("")}</ol></div>` : ""}`;

  if (d.risk_level === "HIGH") {
    shieldBanner.style.display = "block";
    shieldBanner.textContent = "🚨 DIGITAL ARREST SCAM DETECTED — DISCONNECT THE CALL. DO NOT SEND MONEY. CALL 1930.";
    try {
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance("Warning. This call shows signs of a digital arrest scam. Do not send money. End the call and contact 1930.");
        u.lang = "en-IN"; u.rate = 0.95;
        window.speechSynthesis.speak(u);
      }
    } catch (e) {}
    if (!modalShown) { modalShown = true; showModal(d); }
    raiseAlert({ level: "HIGH", title: "🚨 This call looks like a Digital Arrest scam",
                 reasons: d.matched_categories.map(m => m.label) });
  } else {
    shieldBanner.style.display = "none";
  }
}
function scheduleAnalyze() { clearTimeout(analyzeTimer); analyzeTimer = setTimeout(analyzeTranscript, 600); }
transcriptEl.addEventListener("input", scheduleAnalyze);

function startListening() {
  recognizer = new SpeechRec();
  recognizer.lang = document.getElementById("speechLang").value;
  recognizer.continuous = true;
  recognizer.interimResults = true;
  recognizer.onresult = ev => {
    let interim = "";
    for (let i = ev.resultIndex; i < ev.results.length; i++) {
      const t = ev.results[i][0].transcript;
      if (ev.results[i].isFinal) committedText += t + " "; else interim += t;
    }
    transcriptEl.value = committedText + interim;
    scheduleAnalyze();
  };
  recognizer.onerror = e => {
    if (e.error === "not-allowed") { stopListening(); micBtn.textContent = "🎤 Mic blocked — allow permission"; }
  };
  recognizer.onend = () => { if (listening) { try { recognizer.start(); } catch (e) {} } };  // Chrome stops on silence
  recognizer.start();
  listening = true;
  micBtn.textContent = "⏹ Stop Listening";
}
function stopListening() {
  listening = false;
  if (recognizer) recognizer.stop();
  micBtn.textContent = "🎤 Start Listening";
}
micBtn.addEventListener("click", () => {
  if (listening) stopListening();
  else { committedText = transcriptEl.value ? transcriptEl.value + " " : ""; startListening(); }
});
document.getElementById("scamSample").addEventListener("click", () => { modalShown = false; transcriptEl.value = SCAM_SAMPLE; committedText = ""; analyzeTranscript(); });
document.getElementById("caseStudySample").addEventListener("click", () => {
  modalShown = false; transcriptEl.value = CASE_STUDY_SAMPLE; committedText = ""; analyzeTranscript();
  document.getElementById("payAmount").value = 1700000; document.getElementById("payTypical").value = 20000;
  document.getElementById("payMinutes").value = 120; document.getElementById("payNew").checked = true; document.getElementById("payCall").checked = true;
});
document.getElementById("politeSample").addEventListener("click", () => { modalShown = false; transcriptEl.value = POLITE_SAMPLE; committedText = ""; analyzeTranscript(); });
document.getElementById("safeSample").addEventListener("click", () => { transcriptEl.value = SAFE_SAMPLE; committedText = ""; analyzeTranscript(); });
document.getElementById("clearTranscript").addEventListener("click", () => {
  transcriptEl.value = ""; committedText = ""; modalShown = false; lastShieldRisk = "NONE";
  shieldBanner.style.display = "none";
  shieldResult.innerHTML = `<p class="placeholder">Waiting for call audio / text...</p>`;
});

// Payment guard
document.getElementById("payCheck").addEventListener("click", async () => {
  const box = document.getElementById("payResult");
  const res = await fetch("/api/shield/payment", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      amount: parseFloat(document.getElementById("payAmount").value) || 0,
      typical_max: parseFloat(document.getElementById("payTypical").value) || 10000,
      call_minutes: parseFloat(document.getElementById("payMinutes").value) || 0,
      new_beneficiary: document.getElementById("payNew").checked,
      in_video_call: document.getElementById("payCall").checked,
      shield_risk: lastShieldRisk
    })
  });
  const d = await res.json();
  const cls = d.action === "HOLD" ? "verdict-fake" : d.action === "WARN" ? "verdict-warn" : "verdict-real";
  const icon = d.action === "HOLD" ? "⛔" : d.action === "WARN" ? "🟡" : "✅";
  box.innerHTML = `
    <p class="${cls}">${icon} ${d.action === "HOLD" ? "TRANSACTION PAUSED" : d.action === "WARN" ? "RISKY — CONFIRM FIRST" : "LOOKS NORMAL"} (risk ${d.risk_score}%)</p>
    <p>${escapeHtml(d.message)}</p>
    ${d.reasons.length ? `<ul class="flag-list">${d.reasons.map(r => `<li>${escapeHtml(r)}</li>`).join("")}</ul>` : ""}`;
});

// Family alert
document.getElementById("famAlert").addEventListener("click", async () => {
  const box = document.getElementById("famResult");
  const res = await fetch("/api/shield/family-alert", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      contact_name: document.getElementById("famName").value,
      contact_phone: document.getElementById("famPhone").value
    })
  });
  const d = await res.json();
  box.innerHTML = `
    <p class="verdict-warn">📣 Alert ready for ${escapeHtml(d.contact)}</p>
    <div class="hl-box">${escapeHtml(d.message)}</div>
    ${d.whatsapp_link
      ? `<a class="btn" style="display:inline-block;text-decoration:none;margin-top:10px;" href="${d.whatsapp_link}" target="_blank" rel="noopener">Send on WhatsApp</a>`
      : `<p class="hint">Add a phone number to get a WhatsApp send button.</p>`}`;
});


// ---------- DATA EXPOSURE ----------
let exposureLoaded = false;
async function loadExposure() {
  if (exposureLoaded) return;
  try {
    const d = await (await fetch("/api/exposure/awareness")).json();
    document.getElementById("exposureNote").innerHTML = `<b>${escapeHtml(d.headline)}</b><br>${escapeHtml(d.honest_note)}`;
    document.getElementById("leakRoutes").innerHTML = d.leak_routes.map(r => `<li><b>${escapeHtml(r.route)}:</b> ${escapeHtml(r.detail)}</li>`).join("");
    document.getElementById("protectSteps").innerHTML = d.protect_steps.map(r => `<li><b>${escapeHtml(r.step)}</b> — ${escapeHtml(r.how)}</li>`).join("");
    exposureLoaded = true;
  } catch (e) { document.getElementById("exposureNote").textContent = "Could not load (offline?)."; }
}

async function sha1Hex(str) {
  const buf = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(str));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, "0")).join("").toUpperCase();
}
document.getElementById("pwdCheck").addEventListener("click", async () => {
  const box = document.getElementById("pwdResult");
  const pwd = document.getElementById("pwdInput").value;
  if (!pwd) { box.innerHTML = `<p class="placeholder">Type a password first.</p>`; return; }
  try {
    const h = await sha1Hex(pwd);
    const r = await fetch("https://api.pwnedpasswords.com/range/" + h.slice(0, 5), { headers: { "Add-Padding": "true" } });
    const txt = await r.text();
    const line = txt.split("\n").map(l => l.trim().split(":")).find(p => p[0] === h.slice(5));
    const n = line ? parseInt(line[1], 10) : 0;
    box.innerHTML = n > 0
      ? `<p class="verdict-fake">⛔ Seen ${n.toLocaleString()} times in data breaches — never use this password.</p>`
      : `<p class="verdict-real">✅ Not found in known breaches (this does not prove it is strong).</p>`;
  } catch (e) {
    box.innerHTML = `<p class="verdict-warn">Could not reach the breach service (needs internet).</p>`;
  }
  document.getElementById("pwdInput").value = "";
});
document.getElementById("mailCheck").addEventListener("click", async () => {
  const box = document.getElementById("mailResult");
  const res = await fetch("/api/exposure/email", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: document.getElementById("mailInput").value }) });
  const d = await res.json();
  const cls = d.status === "ok" ? (d.breaches > 0 ? "verdict-fake" : "verdict-real") : "verdict-warn";
  box.innerHTML = `<p class="${cls}">${escapeHtml(d.message)}</p>` +
    (d.breach_names ? `<p class="hint">${d.breach_names.map(escapeHtml).join(", ")}</p>` : "");
});

// ---------- SHARE-TO-APP (Android PWA share target) ----------
// Android "Share -> DeepVerif" opens /?text=... ; drop it into the SMS tab and analyse.
(function handleSharedText() {
  const q = new URLSearchParams(location.search);
  const shared = [q.get("title"), q.get("text"), q.get("url")].filter(Boolean).join(" ").trim();
  if (!shared) return;
  document.querySelector('[data-tab="sms"]').click();
  document.getElementById("smsInput").value = shared;
  document.getElementById("analyzeSms").click();
  history.replaceState({}, "", "/");
})();

// ---------- Mobile quick protection + incident report ----------
const quickStartShield = document.getElementById("quickStartShield");
if (quickStartShield) {
  quickStartShield.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    const shieldTab = document.querySelector('.tab-btn[data-tab="shield"]');
    shieldTab.classList.add("active");
    document.getElementById("shield").classList.add("active");
    document.getElementById("shield").scrollIntoView({behavior:"smooth", block:"start"});
    setTimeout(() => {
      if (!listening) startListening();
    }, 350);
  });
}

function buildIncidentReport() {
  const now = new Date();
  const includeTranscript = document.getElementById("reportTranscript")?.checked;
  const user = document.getElementById("reportUser")?.value.trim() || "Not provided";
  const caller = document.getElementById("reportCaller")?.value.trim() || "Not provided";
  const notes = document.getElementById("reportNotes")?.value.trim() || "Not provided";
  const transcript = transcriptEl.value.trim();
  return [
    "DEEPVERIF.AI — DIGITAL ARREST INCIDENT REPORT",
    "================================================",
    `Generated: ${now.toLocaleString()}`,
    `User: ${user}`,
    `Caller number: ${caller}`,
    `Risk detected: ${lastShieldRisk}`,
    "",
    "DETECTED PATTERN",
    "----------------",
    "The DeepVerif.AI Digital Arrest Shield found patterns commonly associated with impersonation, arrest threats, isolation and/or money demands.",
    "",
    "USER NOTES",
    "----------",
    notes,
    "",
    "RECOMMENDED ACTION",
    "------------------",
    "1. End the suspicious call.",
    "2. Do not transfer money or share OTP/PIN/passwords.",
    "3. Contact a trusted family member through a separate channel.",
    "4. If money has been sent or fraud is suspected, contact India's cyber-fraud helpline 1930 and report at https://cybercrime.gov.in/.",
    "",
    includeTranscript ? "TRANSCRIPT / USER-PROVIDED EVIDENCE\n--------------------------------\n" + (transcript || "No transcript captured.") : "TRANSCRIPT OMITTED BY USER",
    "",
    "DISCLAIMER",
    "This is an automated risk assessment, not proof of identity or guilt. Verify the caller independently through an official contact number."
  ].join("\n");
}

function downloadText(filename, text) {
  const blob = new Blob([text], {type: "text/plain;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}

const saveIncidentReport = document.getElementById("saveIncidentReport");
if (saveIncidentReport) {
  saveIncidentReport.addEventListener("click", () => {
    const report = buildIncidentReport();
    downloadText(`deepverif-digital-arrest-report-${Date.now()}.txt`, report);
    document.getElementById("reportResult").innerHTML = `<p class="verdict-real">✅ Incident report saved on this device.</p><p class="hint">You can attach this report while reporting the incident.</p>`;
  });
}

const shareIncidentReport = document.getElementById("shareIncidentReport");
if (shareIncidentReport) {
  shareIncidentReport.addEventListener("click", async () => {
    const report = buildIncidentReport();
    try {
      if (navigator.share) {
        await navigator.share({title: "DeepVerif.AI Incident Report", text: report});
        document.getElementById("reportResult").innerHTML = `<p class="verdict-real">✅ Report shared.</p>`;
      } else {
        await navigator.clipboard.writeText(report);
        document.getElementById("reportResult").innerHTML = `<p class="verdict-warn">📋 Sharing is not available here.</p><p class="hint">The report was copied to the clipboard.</p>`;
      }
    } catch (e) {
      if (e.name !== "AbortError") document.getElementById("reportResult").innerHTML = `<p class="verdict-warn">Could not share the report. Use Save Incident Report instead.</p>`;
    }
  });
}


// ---------- ALERTS + HELP & REPORT ----------
function goTab(name) {
  const b = document.querySelector(`.tab-btn[data-tab="${name}"]`);
  if (b) b.click();
}

let lastAlertKey = "", lastAlertAt = 0;
function raiseAlert({ level, title, reasons }) {
  reasons = (reasons || []).filter(Boolean);
  const key = title + "|" + reasons.join("|");
  if (key === lastAlertKey && Date.now() - lastAlertAt < 60000) return;   // don't spam while live-listening
  lastAlertKey = key; lastAlertAt = Date.now();

  const bar = document.getElementById("alertBar");
  bar.className = "alert-bar " + (level === "HIGH" ? "high" : "med");
  bar.innerHTML = `<b>${escapeHtml(title)}</b>
    ${reasons.length ? `<ul>${reasons.slice(0, 4).map(r => `<li>${escapeHtml(r)}</li>`).join("")}</ul>` : ""}
    <div class="alert-actions">
      <a class="btn danger-btn" href="tel:1930">📞 Call 1930</a>
      <button class="btn secondary-btn" id="alertHelp">🚨 Report / Help</button>
      <button class="btn secondary-btn" id="alertClose">Close</button>
    </div>`;
  bar.style.display = "block";
  document.getElementById("alertHelp").onclick = () => { bar.style.display = "none"; goTab("help"); };
  document.getElementById("alertClose").onclick = () => { bar.style.display = "none"; };

  // System notification (needs permission + service worker); the in-page bar above always shows.
  if ("Notification" in window && Notification.permission === "granted" && navigator.serviceWorker) {
    navigator.serviceWorker.ready.then(reg => reg.showNotification(title, {
      body: reasons.slice(0, 3).join(" • ") || "Be careful: do not share money or OTP. Help: 1930",
      icon: "/static/icons/icon-192.png", tag: "deepverif-alert", renotify: true,
      requireInteraction: level === "HIGH", vibrate: [200, 100, 200],
      data: { url: "/?tab=help" },
      actions: [{ action: "help", title: "Report / Help (1930)" }],
    })).catch(() => {});
  }
}

function refreshAlertStatus() {
  const el = document.getElementById("alertStatus");
  if (!("Notification" in window)) { el.textContent = "This browser does not support notifications."; return; }
  el.textContent = { granted: "✅ Notifications are on.", denied: "❌ Blocked. Allow them in browser/app settings.",
                     default: "Not allowed yet." }[Notification.permission];
}
document.getElementById("enableAlerts").addEventListener("click", async () => {
  if ("Notification" in window) await Notification.requestPermission();
  refreshAlertStatus();
});
refreshAlertStatus();

document.getElementById("pasteCheck").addEventListener("click", async () => {
  const st = document.getElementById("pasteStatus");
  try {
    const text = (await navigator.clipboard.readText()).trim();
    if (!text) { st.textContent = "Clipboard is empty. Copy the message first."; return; }
    st.textContent = "";
    goTab("sms");
    document.getElementById("smsInput").value = text;
    document.getElementById("analyzeSms").click();
  } catch (e) {
    st.textContent = "Clipboard access was not allowed. Paste the message in the SMS tab.";
    goTab("sms");
  }
});

const numResult = document.getElementById("numResult");
let lastCheckedNumber = "";
document.getElementById("numCheck").addEventListener("click", async () => {
  const number = document.getElementById("numInput").value;
  const res = await fetch("/api/number/check", { method: "POST", headers: { "Content-Type": "application/json" },
                                                 body: JSON.stringify({ number }) });
  const d = await res.json();
  if (d.error) { numResult.innerHTML = `<p class="verdict-warn">${escapeHtml(d.error)}</p>`; return; }
  lastCheckedNumber = number;
  const cls = d.risk_level === "HIGH" ? "verdict-fake" : d.risk_level === "MEDIUM" ? "verdict-warn" : "verdict-real";
  numResult.innerHTML = `<p class="${cls}">${escapeHtml(d.number_masked)}: ${d.risk_level} RISK (${d.risk_score}/100)</p>
    ${d.reasons.length ? `<ul class="flag-list">${d.reasons.map(r => `<li>${escapeHtml(r)}</li>`).join("")}</ul>` : "<p>No red flags found.</p>"}
    <div class="advice-box">${escapeHtml(d.advice)}</div>`;
  document.getElementById("numReportRow").style.display = "flex";
  if (d.risk_level !== "LOW") raiseAlert({ level: d.risk_level, title: "📞 This number looks risky", reasons: d.reasons });
  addFeedback(numResult, "number", d.risk_level, d.risk_score);
});
document.getElementById("numReport").addEventListener("click", async () => {
  const res = await fetch("/api/number/report", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ number: lastCheckedNumber, category: document.getElementById("numCategory").value }) });
  const d = await res.json();
  numResult.innerHTML += d.error ? `<p class="verdict-warn">${escapeHtml(d.error)}</p>`
    : `<p class="verdict-real">✅ Reported. ${d.community_reports} report(s) so far. For an official complaint, also use 1930 / cybercrime.gov.in.</p>`;
});

document.getElementById("goIncident").addEventListener("click", () => {
  goTab("shield");
  setTimeout(() => document.getElementById("reportUser").scrollIntoView({ behavior: "smooth", block: "center" }), 150);
});
document.getElementById("goLogs").addEventListener("click", () => goTab("logs"));

// Open a tab from a link / notification / app shortcut:  /?tab=help
(function openTabFromUrl() {
  const t = new URLSearchParams(location.search).get("tab");
  if (t && document.getElementById(t)) { goTab(t); history.replaceState({}, "", "/"); }
})();


// ---------- AI EXPLAIN + FEEDBACK ----------
function addFeedback(box, tool, level, score) {
  const div = document.createElement("div");
  div.className = "fb";
  div.innerHTML = `Was this result correct? <button class="btn secondary-btn" data-v="correct">👍 Correct</button>
                   <button class="btn secondary-btn" data-v="wrong">👎 Galat</button>`;
  div.querySelectorAll("button").forEach(b => b.addEventListener("click", async () => {
    await fetch("/api/feedback", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tool, verdict: b.dataset.v, level, score }) }).catch(() => {});
    div.textContent = "🙏 Thank you! Your feedback will help improve the model.";
  }));
  box.appendChild(div);
}

let aiConsent = false;
function addAiButton(box, text, score, flags) {
  const wrap = document.createElement("div");
  wrap.className = "ai-box";
  wrap.innerHTML = `<button class="btn secondary-btn">🤖 Explain with AI (the message will be sent to Anthropic AI)</button><div class="ai-out"></div>`;
  const out = wrap.querySelector(".ai-out");
  wrap.querySelector("button").addEventListener("click", async () => {
    if (!aiConsent) {
      if (!confirm("The text of this message will be sent to the AI service so it can explain it. Do not send it if it contains an OTP, password or bank details. Continue?")) return;
      aiConsent = true;
    }
    out.innerHTML = `<p class="placeholder">AI is thinking...</p>`;
    try {
      const res = await fetch("/api/ai/explain", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, score, flags }) });
      const d = await res.json();
      const msg = d.explanation || d.message || d.error || "No answer received.";
      out.innerHTML = `<div class="advice-box">${escapeHtml(msg).replace(/\n/g, "<br>")}</div>
        ${d.explanation ? '<p class="hint">An AI-generated answer can be wrong. Also check the rule-based result and the 1930 advice.</p>' : ""}`;
    } catch (e) { out.innerHTML = `<p class="verdict-warn">Could not connect to the AI.</p>`; }
  });
  box.appendChild(wrap);
}

// ---------- QR / UPI ----------
const upiResult = document.getElementById("upiResult");
function renderUpi(d) {
  if (d.error) { upiResult.innerHTML = `<p class="verdict-warn">${escapeHtml(d.error)}</p>`; return; }
  const cls = d.risk_level === "HIGH" ? "verdict-fake" : d.risk_level === "MEDIUM" ? "verdict-warn" : "verdict-real";
  upiResult.innerHTML = `<p class="${cls}">${escapeHtml(d.headline)}: ${d.risk_level} RISK (${d.risk_score}/100)</p>
    ${d.payee_vpa ? `<p>Payee: <b>${escapeHtml(d.payee_name || "no name")}</b> (${escapeHtml(d.payee_vpa)})${d.amount ? ` | Amount: <b>Rs ${d.amount}</b>` : ""}</p>` : ""}
    <ul class="flag-list">${d.reasons.map(r => `<li>${escapeHtml(r)}</li>`).join("")}</ul>
    <div class="advice-box">${escapeHtml(d.advice)}</div>`;
  if (d.risk_level !== "LOW") raiseAlert({ level: d.risk_level, title: "💳 This QR / link looks risky", reasons: d.reasons });
  addFeedback(upiResult, "upi", d.risk_level, d.risk_score);
}
document.getElementById("upiCheck").addEventListener("click", async () => {
  const res = await fetch("/api/upi/check", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: document.getElementById("upiInput").value, expecting_to_receive: document.getElementById("upiExpect").checked }) });
  renderUpi(await res.json());
});
document.getElementById("qrFile").addEventListener("change", async e => {
  const f = e.target.files[0]; if (!f) return;
  upiResult.innerHTML = `<p class="placeholder">Reading QR...</p>`;
  const fd = new FormData();
  fd.append("image", f);
  fd.append("expecting_to_receive", document.getElementById("upiExpect").checked ? "1" : "0");
  try { renderUpi(await (await fetch("/api/upi/scan-image", { method: "POST", body: fd })).json()); }
  catch (err) { upiResult.innerHTML = `<p class="verdict-warn">Upload failed. Please try again.</p>`; }
  e.target.value = "";
});

// ---------- DASHBOARD ----------
const TOOL_NAMES = { sms_phishing: "SMS check", digital_arrest_shield_script: "Call Shield", number_check: "Number check",
                     upi_check: "QR / UPI", document_forensics: "Fake document", rppg_liveness: "Deepfake check", data_exposure: "Data leak" };
const prettyName = n => TOOL_NAMES[n] || String(n).replace(/_/g, " ");
function barList(items) {
  const max = Math.max(1, ...items.map(i => i.count));
  if (!items.length) return `<p class="placeholder">No data yet.</p>`;
  return items.map(i => `<div class="bar-row"><span class="bar-label">${escapeHtml(prettyName(i.name || i.day))}</span>
    <span class="bar"><span style="width:${Math.round(100 * i.count / max)}%"></span></span><b>${i.count}</b></div>`).join("");
}
async function loadDashboard(demo) {
  const d = await (await fetch("/api/insights" + (demo ? "?demo=1" : ""))).json();
  const acc = d.feedback.accuracy === null ? "-" : d.feedback.accuracy + "%";
  document.getElementById("dashBody").innerHTML = `
    ${d.demo ? '<div class="demo-banner">🎬 SAMPLE DATA: these numbers are for demo only, not real.</div>' : ""}
    <div class="stat-cards">
      <div class="stat"><b>${d.total_checks}</b><span>Total checks</span></div>
      <div class="stat"><b>${d.high_risk_alerts}</b><span>High-risk alerts</span></div>
      <div class="stat"><b>${d.numbers_reported}</b><span>Numbers reported</span></div>
      <div class="stat"><b>${acc}</b><span>Users said "correct" (${d.feedback.correct + d.feedback.wrong} feedback)</span></div>
    </div>
    <h3>Kaun sa tool kitna use hua</h3>${barList(d.by_tool)}
    <h3>Most common findings in scam calls</h3>${barList(d.scam_categories)}
    <h3>Pichhle 7 din</h3>${barList(d.last_7_days)}`;
}
document.getElementById("dashRefresh").addEventListener("click", () => loadDashboard(false));
document.getElementById("dashDemo").addEventListener("click", () => loadDashboard(true));
