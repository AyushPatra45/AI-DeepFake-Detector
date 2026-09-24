const state = { currentJob: null, pollTimer: null, toastTimer: null };

const MAX_UPLOAD_BYTES = 500 * 1024 * 1024;
const SUPPORTED_MEDIA_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "video/mp4",
  "video/quicktime",
]);
const SUPPORTED_EXTENSIONS = new Set(["jpg", "jpeg", "png", "mp4", "mov"]);

const byId = (id) => document.getElementById(id);
const formatPercent = (value) => `${(Number(value) * 100).toFixed(1)}%`;
const escapeText = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

function showToast(message) {
  const toast = byId("toast");
  window.clearTimeout(state.toastTimer);
  toast.textContent = message;
  toast.hidden = false;
  state.toastTimer = window.setTimeout(() => { toast.hidden = true; }, 4500);
}

function resetFileSelection() {
  const input = byId("mediaFile");
  input.value = "";
  byId("dropTitle").textContent = "Choose image or video";
  byId("dropMeta").textContent = "Maximum 500 MB";
  byId("analyseButton").disabled = true;
}

function validateFile(file) {
  if (!file) return "Choose a file before starting analysis.";
  const extension = file.name.includes(".") ? file.name.split(".").pop().toLowerCase() : "";
  if (!SUPPORTED_MEDIA_TYPES.has(file.type) && !SUPPORTED_EXTENSIONS.has(extension)) {
    return "Unsupported format. Choose a JPEG, PNG, MP4, or MOV file.";
  }
  if (file.size > MAX_UPLOAD_BYTES) return "File is larger than the 500 MB limit.";
  return null;
}

function selectFile(file, assignToInput = false) {
  const input = byId("mediaFile");
  const validationError = validateFile(file);
  if (validationError) {
    resetFileSelection();
    showToast(validationError);
    input.focus();
    return false;
  }
  if (assignToInput) {
    const transfer = new DataTransfer();
    transfer.items.add(file);
    input.files = transfer.files;
  }
  byId("dropTitle").textContent = file.name;
  byId("dropMeta").textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB`;
  byId("analyseButton").disabled = false;
  return true;
}

function setAnalysisBusy(busy) {
  const form = byId("uploadForm");
  const button = byId("analyseButton");
  form.setAttribute("aria-busy", String(busy));
  button.disabled = busy || !byId("mediaFile").files.length;
  button.textContent = busy ? "Analysing media" : "Start forensic analysis";
}

async function submitAnalysis(event) {
  event.preventDefault();
  const file = byId("mediaFile").files[0];
  if (!selectFile(file)) return;

  const form = new FormData();
  form.append("file", file);
  setAnalysisBusy(true);
  resetResult();
  byId("results").hidden = true;
  setProgress("Uploading", "", 12);
  try {
    const job = await api("/api/v1/analyses", { method: "POST", body: form });
    state.currentJob = job.id;
    setProgress("Queued", job.id, 28);
    pollJob(job.id);
  } catch (error) {
    setProgress("Upload failed", "", 100);
    showToast(error.message);
    setAnalysisBusy(false);
  }
}

function setProgress(label, id, percent) {
  const progress = byId("jobProgress");
  progress.hidden = false;
  byId("progressLabel").textContent = label;
  byId("progressId").textContent = id ? id.slice(0, 8) : "";
  byId("progressBar").style.width = `${percent}%`;
  byId("progressTrack").setAttribute("aria-valuenow", String(percent));
  byId("progressTrack").setAttribute("aria-valuetext", label);
}

async function pollJob(jobId) {
  window.clearTimeout(state.pollTimer);
  try {
    const job = await api(`/api/v1/analyses/${jobId}`);
    const progress = { queued: 30, processing: 68, partially_completed: 100, completed: 100, failed: 100 };
    setProgress(job.status.replaceAll("_", " "), job.id, progress[job.status] || 50);
    if (["completed", "partially_completed", "failed"].includes(job.status)) {
      setAnalysisBusy(false);
      renderResult(job);
      loadHistory();
      return;
    }
    state.pollTimer = window.setTimeout(() => pollJob(jobId), 900);
  } catch (error) {
    setProgress("Analysis status unavailable", jobId, 100);
    showToast(error.message);
    setAnalysisBusy(false);
  }
}

function resetResult() {
  byId("caseFile").textContent = "";
  byId("scoreLabel").textContent = "Face-manipulation model score";
  byId("riskScore").textContent = "Unavailable";
  byId("riskScore").className = "";
  byId("riskDecision").textContent = "Not evaluated";
  byId("riskDecision").className = "risk-badge neutral";
  byId("riskHelp").textContent = "Watermark, provenance, model and forensic signals are reported separately.";
  byId("mediaSummary").textContent = "—";
  byId("frameSummary").textContent = "0";
  byId("lsbSummary").textContent = "Not detected";
  byId("statusSummary").textContent = "—";
  for (const id of ["modelSignal", "originSignal", "elaSignal", "lsbSignal"]) {
    byId(id).replaceChildren();
  }
  byId("moduleList").replaceChildren();
  byId("warningList").replaceChildren();
  byId("artifactGrid").replaceChildren();
  byId("frameTable").replaceChildren();
  byId("reportActions").hidden = true;
  activateTab(byId("overviewTab"));
}

function renderResult(job) {
  resetResult();
  const result = job.result;
  byId("results").hidden = false;
  byId("caseFile").textContent = `${job.source_name} · SHA-256 ${job.sha256}`;
  byId("jsonReport").href = `/api/v1/analyses/${job.id}/report.json`;
  byId("pdfReport").href = `/api/v1/analyses/${job.id}/report.pdf`;
  byId("statusSummary").textContent = job.status.replaceAll("_", " ");

  if (!result) {
    byId("warningList").innerHTML = `<div class="warning">${escapeText(job.error || "Analysis failed")}</div>`;
    byId("riskHelp").textContent = "No model result was produced. Review the failure message and try a supported file.";
    byId("resultHeading").focus();
    return;
  }

  byId("reportActions").hidden = false;

  const deepfake = result.modules.find((module) => module.module === "deepfake_detection");
  const authenticity = result.modules.find((module) => module.module === "media_authenticity");
  const forensics = result.modules.find((module) => module.module === "image_forensics");
  const probability = deepfake?.findings?.deepfake_probability;
  const decision = deepfake?.findings?.decision;
  const assessment = authenticity?.findings?.assessment;
  const watermark = authenticity?.findings?.visible_watermark;
  const score = byId("riskScore");
  const riskBadge = byId("riskDecision");
  if (authenticity?.status === "completed" && watermark?.candidate_detected) {
    byId("scoreLabel").textContent = "AI-origin signal";
    score.textContent = "Strong AI-origin evidence";
    score.className = "assessment-text";
    riskBadge.textContent = watermark?.candidate_detected ? "Visible watermark detected" : "Provenance marker detected";
    riskBadge.className = "risk-badge strong_evidence";
    byId("riskHelp").textContent = watermark?.candidate_detected
      ? "A persistent generator-style watermark was found. Verify invisible SynthID separately for provider attribution."
      : "File-level provenance markers were found. Signature validation is still required.";
  } else if (authenticity?.status === "completed" && authenticity?.findings?.provenance?.ai_origin_claim_detected) {
    score.textContent = probability == null ? "Unavailable" : formatPercent(probability);
    riskBadge.textContent = "Unverified AI-origin claim";
    riskBadge.className = "risk-badge evaluation_pending";
    byId("riskHelp").textContent = "File text mentions AI generation, but its signature is unverified. The face-model score is a separate measurement, not proof of origin.";
  } else if (assessment === "inconclusive" && probability != null) {
    score.textContent = formatPercent(probability);
    riskBadge.textContent = "Origin not confirmed";
    riskBadge.className = "risk-badge evaluation_pending";
    byId("riskHelp").textContent = "No known watermark or provenance marker was found. This unvalidated face-model score is not the probability that the whole image or video is AI-generated.";
  } else if (assessment === "inconclusive") {
    score.textContent = "Unavailable";
    riskBadge.textContent = "Origin not confirmed";
    riskBadge.className = "risk-badge evaluation_pending";
    byId("riskHelp").textContent = "No known watermark or provenance marker was found, and no face-model score was produced. This does not prove the media is real.";
  } else {
    score.textContent = probability == null ? "Unavailable" : formatPercent(probability);
    riskBadge.textContent = decision ? decision.replaceAll("_", " ") : "Not evaluated";
    riskBadge.className = `risk-badge ${decision || "neutral"}`;
    byId("riskHelp").textContent = "Authenticity analysis was unavailable; review individual module warnings.";
  }
  byId("frameSummary").textContent = deepfake?.findings?.analysed_faces ?? "Not evaluated";
  const lsb = forensics?.findings?.lsb;
  byId("lsbSummary").textContent = lsb
    ? (lsb.supported_payload_detected ? "Extracted safely" : "Not detected")
    : "Not evaluated";
  const media = result.media;
  byId("mediaSummary").textContent = media.duration_seconds == null
    ? `${media.width} × ${media.height}`
    : `${media.duration_seconds.toFixed(1)} s · ${media.width} × ${media.height}`;

  renderSignals(deepfake, authenticity, forensics, media);
  renderModules(result.modules);
  renderWarnings(result);
  renderArtifacts(result.modules);
  renderFrames(result.frames);
  byId("resultHeading").focus();
}

function setSignal(id, value, note) {
  const valueElement = document.createElement("strong");
  valueElement.textContent = value;
  const noteElement = document.createElement("span");
  noteElement.textContent = note;
  byId(id).replaceChildren(valueElement, noteElement);
}

function renderSignals(deepfake, authenticity, forensics, media) {
  const probability = deepfake?.findings?.deepfake_probability;
  setSignal(
    "modelSignal",
    probability == null ? "No score" : formatPercent(probability),
    "Unvalidated score for facial manipulation patterns, not whole-media AI probability."
  );

  const watermark = authenticity?.findings?.visible_watermark;
  const provenance = authenticity?.findings?.provenance;
  if (!authenticity || authenticity.status !== "completed") {
    setSignal("originSignal", "Not evaluated", "Origin-marker analysis was unavailable.");
  } else if (watermark?.candidate_detected) {
    setSignal("originSignal", "Visible watermark candidate", "Strong AI-origin lead; confirm provider attribution separately.");
  } else if (provenance?.ai_origin_claim_detected) {
    setSignal("originSignal", "AI-origin claim found", "File claim is not signature-verified.");
  } else {
    setSignal("originSignal", "No known marker found", "Absence does not establish authenticity.");
  }

  const ela = forensics?.findings?.ela;
  if (ela) {
    setSignal(
      "elaSignal",
      `${Number(ela.mean_error).toFixed(2)} mean error · ${formatPercent(ela.highlighted_pixel_ratio)} highlighted`,
      "JPEG recompression difference; inspect the heatmap. Neither measure is a fake probability."
    );
  } else {
    setSignal("elaSignal", "Not applied", media.duration_seconds == null
      ? "ELA was not available for this image."
      : "Video compression changes this signal.");
  }

  const lsb = forensics?.findings?.lsb;
  if (lsb?.supported_payload_detected) {
    setSignal("lsbSignal", `${lsb.extracted_size_bytes} bytes extracted`, "Supported LSB layout; payload retained as inert bytes.");
  } else {
    setSignal("lsbSignal", lsb ? "No supported payload" : "Not evaluated",
      lsb ? "Other steganography methods may still exist."
        : media.duration_seconds == null ? "LSB analysis was unavailable for this image."
          : "LSB extraction is for still images.");
  }
}

function renderModules(modules) {
  const container = byId("moduleList");
  container.replaceChildren();
  modules.forEach((module) => {
    const row = document.createElement("article");
    row.className = "module-row";
    let findingText = Object.entries(module.findings || {})
      .filter(([key, value]) => !["assessment", "decision"].includes(key)
        && ["string", "number", "boolean"].includes(typeof value))
      .map(([key, value]) => {
        const label = key === "deepfake_probability"
          ? "face manipulation model score"
          : key.replaceAll("_", " ");
        return `${label}: ${key === "deepfake_probability" && value != null ? formatPercent(value) : value}`;
      })
      .join(" · ");
    if (module.status !== "completed") {
      findingText = (module.warnings || []).join(" ") || "No findings were produced.";
    } else if (module.module === "media_authenticity") {
      findingText = module.findings?.visible_watermark?.candidate_detected
        ? "Visible watermark candidate detected"
        : module.findings?.provenance?.ai_origin_claim_detected
          ? "AI-origin claim found; signature not verified"
          : "No known watermark or provenance marker found";
    } else if (module.module === "image_forensics") {
      findingText = module.findings?.ela
        ? "ELA heatmap and LSB inspection available above"
        : "Video metadata inspected; ELA and LSB not applied";
    }
    findingText ||= `Version ${module.version}`;
    row.innerHTML = `
      <div class="module-name">${escapeText(module.module.replaceAll("_", " "))}</div>
      <span class="module-state ${escapeText(module.status)}">${escapeText(module.status)}</span>
      <p class="module-detail">${escapeText(findingText)}</p>`;
    container.append(row);
  });
}

function renderWarnings(result) {
  const warnings = [
    ...(result.warnings || []),
    ...result.modules.flatMap((module) => module.warnings || []),
  ];
  const container = byId("warningList");
  container.replaceChildren();
  warnings.forEach((message) => {
    const item = document.createElement("div");
    item.className = "warning";
    item.textContent = message;
    container.append(item);
  });
}

function renderArtifacts(modules) {
  const container = byId("artifactGrid");
  container.replaceChildren();
  const artifacts = modules.flatMap((module) => module.artifacts || []);
  if (!artifacts.length) {
    container.innerHTML = '<p class="empty-cell">No visual evidence was generated.</p>';
    return;
  }
  artifacts.forEach((artifact) => {
    const card = document.createElement("article");
    card.className = "artifact";
    if (artifact.kind === "extracted_payload") {
      card.innerHTML = `<div class="artifact-copy"><strong>${escapeText(artifact.kind.replaceAll("_", " "))}</strong><span>${escapeText(artifact.description)}</span><a href="${encodeURI(artifact.path)}" download>Download inert bytes</a></div>`;
    } else {
      card.innerHTML = `<img src="${encodeURI(artifact.path)}" alt="${escapeText(artifact.description || artifact.kind)}" loading="lazy" /><div class="artifact-copy"><strong>${escapeText(artifact.kind.replaceAll("_", " "))}</strong><span>${escapeText(artifact.description)}</span></div>`;
    }
    container.append(card);
  });
}

function renderFrames(frames) {
  const table = byId("frameTable");
  table.replaceChildren();
  if (!frames.length) {
    table.innerHTML = '<tr><td class="empty-cell" colspan="4">No sampled video frames.</td></tr>';
    return;
  }
  frames.forEach((frame) => {
    const row = document.createElement("tr");
    row.innerHTML = `<td>${frame.frame_index}</td><td>${Number(frame.timestamp_seconds).toFixed(2)} s</td><td>${frame.deepfake_probability == null ? "—" : formatPercent(frame.deepfake_probability)}</td><td><a href="${encodeURI(frame.artifact.path)}" target="_blank" rel="noreferrer">Open frame</a></td>`;
    table.append(row);
  });
}

async function loadHistory() {
  const table = byId("historyTable");
  table.setAttribute("aria-busy", "true");
  try {
    const payload = await api("/api/v1/analyses?limit=100");
    table.replaceChildren();
    if (!payload.jobs.length) {
      table.innerHTML = '<tr><td class="empty-cell" colspan="5">No analysis cases.</td></tr>';
      return;
    }
    payload.jobs.forEach((job) => {
      const row = document.createElement("tr");
      const status = job.status.replaceAll("_", " ");
      row.innerHTML = `<td>${escapeText(job.source_name)}</td><td>${new Date(job.created_at).toLocaleString()}</td><td>${escapeText(job.media_type)}</td><td>${escapeText(status)}</td><td><button class="case-button" type="button" data-job="${job.id}" aria-label="Open ${escapeText(job.source_name)} case, status ${escapeText(status)}">${job.id.slice(0, 8)}</button></td>`;
      table.append(row);
    });
  } catch (error) {
    showToast(error.message);
  } finally {
    table.setAttribute("aria-busy", "false");
  }
}

function activateTab(selectedTab, focusTab = false) {
  document.querySelectorAll(".tab").forEach((tab) => {
    const active = tab === selectedTab;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", String(active));
    tab.tabIndex = active ? 0 : -1;
  });

  document.querySelectorAll(".tab-panel").forEach((panel) => {
    const active = panel.id === selectedTab.getAttribute("aria-controls");
    panel.classList.toggle("active", active);
    panel.hidden = !active;
  });

  if (focusTab) selectedTab.focus();
}

function switchView(name, focusHeading = false) {
  document.querySelectorAll(".view").forEach((view) => {
    const active = view.id === `${name}View`;
    view.classList.toggle("active", active);
    view.hidden = !active;
  });

  document.querySelectorAll(".nav-item").forEach((item) => {
    const active = item.dataset.view === name;
    item.classList.toggle("active", active);
    item.setAttribute("aria-pressed", String(active));
  });

  if (name === "history") loadHistory();
  if (focusHeading) byId(`${name}Heading`).focus();
}
function initialiseEvents() {
  byId("uploadForm").addEventListener("submit", submitAnalysis);
  byId("mediaFile").addEventListener("change", (event) => selectFile(event.target.files[0]));
  const dropZone = byId("dropZone");
  ["dragenter", "dragover"].forEach((name) => dropZone.addEventListener(name, (event) => {
    event.preventDefault();
    dropZone.classList.add("dragging");
  }));
  ["dragleave", "drop"].forEach((name) => dropZone.addEventListener(name, (event) => {
    event.preventDefault();
    dropZone.classList.remove("dragging");
  }));
  dropZone.addEventListener("drop", (event) => selectFile(event.dataTransfer.files[0], true));
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => switchView(button.dataset.view, true));
  });

  const tabs = Array.from(document.querySelectorAll(".tab"));
  tabs.forEach((button, index) => {
    button.addEventListener("click", () => activateTab(button));

    button.addEventListener("keydown", (event) => {
      let nextIndex;

      if (event.key === "ArrowRight") {
        nextIndex = (index + 1) % tabs.length;
      } else if (event.key === "ArrowLeft") {
        nextIndex = (index - 1 + tabs.length) % tabs.length;
      } else if (event.key === "Home") {
        nextIndex = 0;
      } else if (event.key === "End") {
        nextIndex = tabs.length - 1;
      } else {
        return;
      }

      event.preventDefault();
      activateTab(tabs[nextIndex], true);
    });
  });
  byId("refreshHistory").addEventListener("click", loadHistory);
  byId("historyTable").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-job]");
    if (!button) return;
    try {
      const job = await api(`/api/v1/analyses/${button.dataset.job}`);
      switchView("analysis");
      renderResult(job);
    } catch (error) { showToast(error.message); }
  });
}

async function initialise() {
  initialiseEvents();
  try {
    const health = await api("/health");
    byId("healthDot").classList.add("online");
    byId("healthText").textContent = `Engine ${health.version}`;
  } catch {
    byId("healthText").textContent = "Engine unavailable";
  }
}

initialise();
