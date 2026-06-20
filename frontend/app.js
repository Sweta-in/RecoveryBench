/**
 * RecoveryBench — Frontend Application Logic (Redesigned)
 *
 * Vanilla JS (no framework). Connects the redesigned landing page
 * to the FastAPI backend at http://localhost:8000.
 *
 * Responsibilities:
 *   1. Tab navigation (Text Analysis, Audio Analysis, Agent Leaderboard)
 *   2. POST /analyze/text with borrower_message + agent_response
 *   3. POST /analyze/audio with multipart file upload
 *   4. Leaderboard: batch scoring, ranking, CSV export
 *   5. Animate the pipeline trace steps sequentially
 *   6. Populate all result elements from the API response
 *   7. Wire example chips and evaluator selector
 *   8. Chart.js benchmark bar chart + radar chart for agent scorecard
 */

// ── Configuration ───────────────────────────────────────────────
const API_BASE = "http://localhost:8000";
const TRACE_STEP_DELAY_MS = 150;

// ── DOM References ──────────────────────────────────────────────
const dom = {
  // Text tab
  borrowerInput:      () => document.getElementById("borrower-input"),
  agentInput:         () => document.getElementById("agent-input"),
  analyzeBtn:         () => document.getElementById("analyze-btn"),
  evaluatorSelect:    () => document.getElementById("evaluator-select"),

  // Text tab states
  emptyState:         () => document.getElementById("empty-state"),
  errorState:         () => document.getElementById("error-state"),
  errorMessage:       () => document.getElementById("error-message"),
  resultsContent:     () => document.getElementById("results-content"),

  // Trace
  traceList:          () => document.getElementById("trace-list"),

  // Risk gauge (text tab)
  riskValue:          () => document.getElementById("risk-value"),
  riskBand:           () => document.getElementById("risk-band"),
  riskGaugeFill:      () => document.getElementById("risk-gauge-fill"),

  // Intent (text tab)
  intentValue:        () => document.getElementById("intent-value"),
  intentConfFill:     () => document.getElementById("intent-confidence-fill"),
  intentConfLabel:    () => document.getElementById("intent-confidence-label"),

  // Promise (text tab)
  promiseValue:       () => document.getElementById("promise-value"),
  promiseWindow:      () => document.getElementById("promise-window"),

  // Compliance (text tab)
  complianceStatus:   () => document.getElementById("compliance-status"),
  complianceList:     () => document.getElementById("compliance-list"),

  // Eval (text tab)
  evalBlock:          () => document.getElementById("eval-block"),
  overallScore:       () => document.getElementById("overall-score"),
  overallScoreTag:    () => document.getElementById("overall-score-tag"),
  suggestionText:     () => document.getElementById("suggestion-text"),

  // JSON (text tab)
  jsonOutput:         () => document.getElementById("json-output"),

  // Audio tab
  audioDropZone:      () => document.getElementById("audio-drop-zone"),
  audioFileInput:     () => document.getElementById("audio-file-input"),
  audioFileInfo:      () => document.getElementById("audio-file-info"),
  audioFileName:      () => document.getElementById("audio-file-name"),
  audioClearBtn:      () => document.getElementById("audio-clear-btn"),
  audioAnalyzeBtn:    () => document.getElementById("audio-analyze-btn"),
  audioTranscript:    () => document.getElementById("audio-transcript-block"),
  audioTranscriptContent: () => document.getElementById("audio-transcript-content"),
  audioEmptyState:    () => document.getElementById("audio-empty-state"),
  audioErrorState:    () => document.getElementById("audio-error-state"),
  audioErrorMessage:  () => document.getElementById("audio-error-message"),
  audioResultsContent:() => document.getElementById("audio-results-content"),
  audioJsonOutput:    () => document.getElementById("audio-json-output"),

  // Leaderboard tab
  leaderboardInput:   () => document.getElementById("leaderboard-input"),
  leaderboardScoreBtn:() => document.getElementById("leaderboard-score-btn"),
  leaderboardExportBtn:()=> document.getElementById("leaderboard-export-btn"),
  leaderboardProgress:() => document.getElementById("leaderboard-progress"),
  leaderboardProgressFill: () => document.getElementById("leaderboard-progress-fill"),
  leaderboardProgressLabel: () => document.getElementById("leaderboard-progress-label"),
  leaderboardEmptyState: () => document.getElementById("leaderboard-empty-state"),
  leaderboardErrorState: () => document.getElementById("leaderboard-error-state"),
  leaderboardErrorMessage: () => document.getElementById("leaderboard-error-message"),
  leaderboardResults: () => document.getElementById("leaderboard-results"),
  leaderboardTbody:   () => document.getElementById("leaderboard-tbody"),
  lbTotalCount:       () => document.getElementById("lb-total-count"),
  lbAvgScore:         () => document.getElementById("lb-avg-score"),
  lbBestScore:        () => document.getElementById("lb-best-score"),
  lbWorstScore:       () => document.getElementById("lb-worst-score"),
};

// ── Helpers ─────────────────────────────────────────────────────

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function getRiskBand(riskScore) {
  if (riskScore < 0.3) return 'low';
  if (riskScore < 0.6) return 'medium';
  if (riskScore < 0.8) return 'high';
  return 'critical';
}

function setBarColor(el, value) {
  if (value >= 7.5) {
    el.style.background = "var(--good)";
  } else if (value >= 5) {
    el.style.background = "var(--warn)";
  } else {
    el.style.background = "var(--risk)";
  }
}

function truncate(text, maxLen = 60) {
  if (!text) return "—";
  return text.length > maxLen ? text.slice(0, maxLen) + "…" : text;
}

function fmtScore(val) {
  if (val == null) return "—";
  return val.toFixed(1);
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// ══════════════════════════════════════════════════════════════════
// TAB NAVIGATION
// ══════════════════════════════════════════════════════════════════

function initTabs() {
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabContents = document.querySelectorAll(".tab-content");

  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetTab = btn.getAttribute("data-tab");

      tabBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      tabContents.forEach((tc) => {
        if (tc.id === "tab-" + targetTab) {
          tc.classList.add("active");
        } else {
          tc.classList.remove("active");
        }
      });
    });
  });
}

// ══════════════════════════════════════════════════════════════════
// TEXT ANALYSIS
// ══════════════════════════════════════════════════════════════════

function showEmpty() {
  dom.emptyState().classList.remove("hidden");
  dom.errorState().classList.add("hidden");
  dom.resultsContent().classList.add("hidden");
}

function showError(message) {
  dom.emptyState().classList.add("hidden");
  dom.errorState().classList.remove("hidden");
  dom.resultsContent().classList.add("hidden");
  dom.errorMessage().textContent = message;
}

function showResults() {
  dom.emptyState().classList.add("hidden");
  dom.errorState().classList.add("hidden");
  dom.resultsContent().classList.remove("hidden");
}

function setLoading(btn, loading) {
  if (loading) {
    btn.classList.add("loading");
    btn.disabled = true;
  } else {
    btn.classList.remove("loading");
    btn.disabled = false;
  }
}

// ── Trace Animation ─────────────────────────────────────────────

function resetTrace() {
  const list = dom.traceList();
  if (!list) return;
  const steps = list.querySelectorAll(".trace-step");
  steps.forEach((s) => s.classList.remove("active"));
}

async function animateTrace() {
  resetTrace();
  const list = dom.traceList();
  if (!list) return;
  const steps = list.querySelectorAll(".trace-step");
  for (const step of steps) {
    await sleep(TRACE_STEP_DELAY_MS);
    step.classList.add("active");
  }
  await sleep(100);
}

function populateTraceValues(data) {
  const list = dom.traceList();
  if (!list) return;
  const steps = list.querySelectorAll(".trace-step");
  steps.forEach((step) => {
    const key = step.getAttribute("data-step");
    const valEl = step.querySelector(".trace-val");
    if (!valEl) return;
    switch (key) {
      case 'lang':
        valEl.textContent = data.language || '—';
        break;
      case 'intent':
        valEl.textContent = (data.repayment_intent || '—') +
          (data.intent_confidence != null ? ' (' + data.intent_confidence.toFixed(2) + ')' : '');
        break;
      case 'promise':
        valEl.textContent = data.promise_to_pay
          ? 'Yes — ' + (data.payment_window_days || '?') + ' days'
          : 'No';
        break;
      case 'risk':
        valEl.textContent = data.risk_score != null
          ? data.risk_score.toFixed(2) + ' ' + getRiskBand(data.risk_score).toUpperCase()
          : '—';
        break;
      case 'compliance':
        valEl.textContent = (data.compliance && data.compliance.compliant != null)
          ? (data.compliance.compliant ? 'COMPLIANT' : 'VIOLATION')
          : '—';
        break;
      case 'eval':
        valEl.textContent = data.agent_eval
          ? data.agent_eval.overall_score.toFixed(2) + ' / 10'
          : 'N/A';
        break;
    }
  });
}

// ── Shared Result Population ────────────────────────────────────

function populateResults(data, hasAgentResponse, prefix = "") {
  // ── Risk Gauge ────────────────────────────────────────────────
  const riskScore = data.risk_score ?? 0;
  const riskPct = Math.round(riskScore * 100);

  const riskValueEl = document.getElementById(prefix + "risk-value");
  const riskBandEl = document.getElementById(prefix + "risk-band");
  const riskGaugeFillEl = document.getElementById(prefix + "risk-gauge-fill");

  if (riskValueEl) riskValueEl.textContent = riskPct + "%";

  if (riskGaugeFillEl) {
    const offset = 157 - 157 * riskScore;
    riskGaugeFillEl.style.strokeDashoffset = offset;
    if (riskScore < 0.35) {
      riskGaugeFillEl.style.stroke = "var(--good)";
    } else if (riskScore < 0.65) {
      riskGaugeFillEl.style.stroke = "var(--warn)";
    } else {
      riskGaugeFillEl.style.stroke = "var(--risk)";
    }
  }

  if (riskBandEl) {
    riskBandEl.className = "gauge-band";
    if (riskScore < 0.3) {
      riskBandEl.textContent = "Low";
      riskBandEl.classList.add("low");
    } else if (riskScore < 0.6) {
      riskBandEl.textContent = "Medium";
      riskBandEl.classList.add("medium");
    } else if (riskScore < 0.8) {
      riskBandEl.textContent = "High";
      riskBandEl.classList.add("high");
    } else {
      riskBandEl.textContent = "Critical";
      riskBandEl.classList.add("critical");
    }
  }

  // ── Intent ────────────────────────────────────────────────────
  const intentEl = document.getElementById(prefix + "intent-value");
  const intentConfFillEl = document.getElementById(prefix + "intent-confidence-fill");
  const intentConfLabelEl = document.getElementById(prefix + "intent-confidence-label");

  if (intentEl) intentEl.textContent = data.repayment_intent || "—";
  const conf = data.intent_confidence ?? 0;
  if (intentConfFillEl) intentConfFillEl.style.width = (conf * 100) + "%";
  if (intentConfLabelEl) intentConfLabelEl.textContent = Math.round(conf * 100) + "% confidence";

  // ── Promise ───────────────────────────────────────────────────
  const promValEl = document.getElementById(prefix + "promise-value");
  const promWinEl = document.getElementById(prefix + "promise-window");

  const hasProm = data.promise_to_pay === true;
  if (promValEl) {
    promValEl.textContent = hasProm ? "Yes" : "No";
    promValEl.style.color = hasProm ? "var(--good)" : "var(--text-dim)";
  }
  if (promWinEl) {
    promWinEl.textContent = (hasProm && data.payment_window_days != null)
      ? "within " + data.payment_window_days + " days"
      : "";
  }

  // ── Compliance ────────────────────────────────────────────────
  const comp = data.compliance || {};
  const compStatusEl = document.getElementById(prefix + "compliance-status");
  const compListEl = document.getElementById(prefix + "compliance-list");

  if (compStatusEl) {
    compStatusEl.className = "compliance-tag";
    if (comp.compliant) {
      compStatusEl.textContent = "COMPLIANT";
      compStatusEl.classList.add("compliant");
    } else {
      compStatusEl.textContent = "VIOLATION";
      compStatusEl.classList.add("violation");
    }
  }

  if (compListEl) {
    compListEl.innerHTML = "";
    const violations = comp.violations || [];
    if (violations.length === 0) {
      const li = document.createElement("li");
      li.textContent = "No violations detected";
      compListEl.appendChild(li);
    } else {
      violations.forEach((v) => {
        const li = document.createElement("li");
        li.classList.add("violation-item");
        const sev = v.severity ? `[${v.severity.toUpperCase()}]` : "";
        const matched = v.matched_text ? ` — "${v.matched_text}"` : "";
        li.textContent = `${sev} ${v.rule_id || v.category || "rule"}${matched}`;
        compListEl.appendChild(li);
      });
    }
  }

  // ── Agent Eval ────────────────────────────────────────────────
  const evalBlockEl = document.getElementById(prefix + "eval-block");

  if (evalBlockEl) {
    if (!hasAgentResponse || !data.agent_eval) {
      evalBlockEl.classList.add("hidden");
    } else {
      evalBlockEl.classList.remove("hidden");
      const ev = data.agent_eval;

      const overallEl = document.getElementById(prefix + "overall-score");
      const tagEl = document.getElementById(prefix + "overall-score-tag");
      const sugEl = document.getElementById(prefix + "suggestion-text");

      const overall = ev.overall_score ?? 0;
      if (overallEl) overallEl.textContent = overall.toFixed(2);

      if (tagEl) {
        tagEl.className = "overall-score-tag";
        if (overall >= 7.5) {
          tagEl.textContent = "Good";
          tagEl.classList.add("good");
        } else if (overall >= 5) {
          tagEl.textContent = "Needs work";
          tagEl.classList.add("mixed");
        } else {
          tagEl.textContent = "Poor";
          tagEl.classList.add("poor");
        }
      }

      // Rubric bars (used by audio tab)
      const rubrics = ["intent_accuracy", "tone_score", "compliance_score", "escalation_score"];
      rubrics.forEach((key) => {
        const val = ev[key] ?? 0;
        const barEl = document.getElementById(prefix + "bar-" + key);
        const numEl = document.getElementById(prefix + "num-" + key);

        if (barEl) {
          barEl.style.width = (val / 10) * 100 + "%";
          setBarColor(barEl, val);
        }
        if (numEl) {
          numEl.textContent = val.toFixed(1) + "/10";
        }
      });

      if (sugEl) sugEl.textContent = ev.suggested_improvement || "—";

      // Radar chart (text tab only — prefix === "")
      if (prefix === "") {
        renderRadarChart(ev);
      }
    }
  }

  // ── JSON Output ───────────────────────────────────────────────
  const jsonEl = document.getElementById(prefix + "json-output");
  if (jsonEl) jsonEl.textContent = JSON.stringify(data, null, 2);
}

// ── Radar Chart ─────────────────────────────────────────────────

function renderRadarChart(ev) {
  const canvas = document.getElementById("radar-chart");
  if (!canvas) return;

  // Destroy existing chart if any
  if (window.radarChart) {
    window.radarChart.destroy();
  }

  const scores = {
    intent: ev.intent_accuracy ?? 0,
    tone: ev.tone_score ?? 0,
    compliance: ev.compliance_score ?? 0,
    escalation: ev.escalation_score ?? 0
  };

  // Dynamic color based on overall score
  const overall = ev.overall_score ?? 0;
  let borderColor, bgColor;
  if (overall >= 7.5) {
    borderColor = '#14B8A6'; // teal — good
    bgColor = 'rgba(20, 184, 166, 0.25)';
  } else if (overall >= 5) {
    borderColor = '#F59E0B'; // amber — medium
    bgColor = 'rgba(245, 158, 11, 0.25)';
  } else {
    borderColor = '#EF4444'; // red — poor
    bgColor = 'rgba(239, 68, 68, 0.25)';
  }

  const ctx = canvas.getContext("2d");
  window.radarChart = new Chart(ctx, {
    type: "radar",
    data: {
      labels: ["Intent", "Tone", "Compliance", "Escalation"],
      datasets: [{
        data: [scores.intent, scores.tone, scores.compliance, scores.escalation],
        backgroundColor: bgColor,
        borderColor: borderColor,
        borderWidth: 2.5,
        pointBackgroundColor: borderColor,
        pointBorderColor: '#ffffff',
        pointBorderWidth: 2,
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: borderColor,
        pointRadius: 6,
        pointHoverRadius: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        r: {
          min: 0,
          max: 10,
          ticks: {
            stepSize: 2,
            color: '#71717A',
            backdropColor: 'transparent',
            font: { size: 12 }
          },
          grid: { color: '#3F3F46' },
          angleLines: { color: '#3F3F46' },
          pointLabels: {
            color: '#FFFFFF',
            font: { size: 14, weight: '600' },
            padding: 8
          }
        }
      }
    }
  });

  // Render score pills legend
  const pillsContainer = document.getElementById("radar-score-pills");
  if (pillsContainer) {
    const dims = [
      { label: "Intent", value: scores.intent },
      { label: "Tone", value: scores.tone },
      { label: "Compliance", value: scores.compliance },
      { label: "Escalation", value: scores.escalation }
    ];
    pillsContainer.innerHTML = dims.map(d =>
      `<span class="radar-score-pill">` +
        `<span class="pill-label">${d.label}:</span>` +
        `<span class="pill-value">${d.value.toFixed(1)}</span>` +
      `</span>`
    ).join("");
  }
}

// ── Core Text Analysis Flow ─────────────────────────────────────

async function runAnalysis() {
  const borrower = dom.borrowerInput().value.trim();
  const agent = dom.agentInput().value.trim();

  if (!borrower) {
    showError("Please enter a borrower message.");
    return;
  }

  setLoading(dom.analyzeBtn(), true);
  resetTrace();

  let url = API_BASE + "/analyze/text";
  const evaluator = dom.evaluatorSelect().value;
  if (evaluator) {
    url += "?evaluator=" + encodeURIComponent(evaluator);
  }

  const body = { borrower_message: borrower };
  if (agent) {
    body.agent_response = agent;
  }

  try {
    const [, response] = await Promise.all([
      animateTrace(),
      fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    ]);

    if (!response.ok) {
      let errMsg = `Server returned ${response.status}`;
      try {
        const errBody = await response.json();
        errMsg = errBody.detail?.error || errBody.error || errBody.detail || errMsg;
      } catch { /* ignore parse failure */ }
      showError(errMsg);
      return;
    }

    const data = await response.json();
    showResults();
    populateTraceValues(data);
    populateResults(data, !!agent, "");
  } catch (err) {
    console.error("Analysis fetch failed:", err);
    showError(
      "Could not reach the API at " + API_BASE +
      ". Make sure the backend is running (uvicorn api.main:app --port 8000)."
    );
  } finally {
    setLoading(dom.analyzeBtn(), false);
  }
}

// ══════════════════════════════════════════════════════════════════
// AUDIO ANALYSIS
// ══════════════════════════════════════════════════════════════════

let selectedAudioFile = null;

function showAudioEmpty() {
  dom.audioEmptyState().classList.remove("hidden");
  dom.audioErrorState().classList.add("hidden");
  dom.audioResultsContent().classList.add("hidden");
}

function showAudioError(message) {
  dom.audioEmptyState().classList.add("hidden");
  dom.audioErrorState().classList.remove("hidden");
  dom.audioResultsContent().classList.add("hidden");
  dom.audioErrorMessage().textContent = message;
}

function showAudioResults() {
  dom.audioEmptyState().classList.add("hidden");
  dom.audioErrorState().classList.add("hidden");
  dom.audioResultsContent().classList.remove("hidden");
}

function initAudio() {
  const dropZone = dom.audioDropZone();
  const fileInput = dom.audioFileInput();
  const analyzeBtn = dom.audioAnalyzeBtn();

  dropZone.addEventListener("click", () => fileInput.click());

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
  });
  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("drag-over");
  });
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    if (e.dataTransfer.files.length > 0) {
      handleAudioFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
      handleAudioFile(fileInput.files[0]);
    }
  });

  dom.audioClearBtn().addEventListener("click", () => {
    clearAudioFile();
  });

  analyzeBtn.addEventListener("click", runAudioAnalysis);
}

function handleAudioFile(file) {
  selectedAudioFile = file;
  dom.audioFileName().textContent = file.name + " (" + (file.size / 1024).toFixed(1) + " KB)";
  dom.audioFileInfo().classList.remove("hidden");
  dom.audioDropZone().classList.add("hidden");
  dom.audioAnalyzeBtn().disabled = false;
}

function clearAudioFile() {
  selectedAudioFile = null;
  dom.audioFileInput().value = "";
  dom.audioFileInfo().classList.add("hidden");
  dom.audioDropZone().classList.remove("hidden");
  dom.audioAnalyzeBtn().disabled = true;
  dom.audioTranscript().classList.add("hidden");
  showAudioEmpty();
}

async function runAudioAnalysis() {
  if (!selectedAudioFile) return;

  const btn = dom.audioAnalyzeBtn();
  setLoading(btn, true);

  const formData = new FormData();
  formData.append("file", selectedAudioFile);

  try {
    const response = await fetch(API_BASE + "/analyze/audio", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      let errMsg = `Server returned ${response.status}`;
      try {
        const errBody = await response.json();
        const detail = errBody.detail;
        if (typeof detail === "object") {
          errMsg = detail.error || JSON.stringify(detail);
        } else {
          errMsg = detail || errBody.error || errMsg;
        }
      } catch { /* ignore parse failure */ }

      if (response.status === 503) {
        errMsg = "Voice pipeline unavailable. Ensure Whisper and ffmpeg are installed. " + errMsg;
      }

      showAudioError(errMsg);
      return;
    }

    const data = await response.json();

    // Show transcript
    const transcriptBlock = dom.audioTranscript();
    const transcriptContent = dom.audioTranscriptContent();
    transcriptBlock.classList.remove("hidden");

    if (data.speakers && data.speakers.length > 0) {
      transcriptContent.innerHTML = "";
      data.speakers.forEach((turn) => {
        const div = document.createElement("div");
        div.className = "transcript-turn";
        const label = document.createElement("span");
        label.className = "speaker-label " + turn.speaker.toLowerCase();
        label.textContent = turn.speaker;
        const text = document.createElement("span");
        text.className = "speaker-text";
        text.textContent = turn.text;
        div.appendChild(label);
        div.appendChild(text);
        transcriptContent.appendChild(div);
      });
    } else if (data.transcript) {
      transcriptContent.innerHTML = "";
      const p = document.createElement("p");
      p.textContent = data.transcript;
      transcriptContent.appendChild(p);
    }

    // Populate audio metadata
    const durationEl = document.getElementById("audio-duration");
    const asrModelEl = document.getElementById("audio-asr-model");
    const diarizationEl = document.getElementById("audio-diarization");
    const procTimeEl = document.getElementById("audio-proc-time");

    if (durationEl && data.duration_seconds != null) {
      durationEl.textContent = data.duration_seconds.toFixed(1) + "s";
    }
    if (asrModelEl) asrModelEl.textContent = data.asr_model || "—";
    if (diarizationEl) diarizationEl.textContent = data.diarization_backend || "—";
    if (procTimeEl && data.processing_time_seconds != null) {
      procTimeEl.textContent = data.processing_time_seconds.toFixed(2) + "s";
    }

    showAudioResults();
    const hasAgent = !!(data.agent_text || data.agent_eval);
    populateResults(data, hasAgent, "audio-");

  } catch (err) {
    console.error("Audio analysis failed:", err);
    showAudioError(
      "Could not reach the API at " + API_BASE +
      ". Make sure the backend is running with voice pipeline enabled."
    );
  } finally {
    setLoading(btn, false);
  }
}

// ══════════════════════════════════════════════════════════════════
// AGENT LEADERBOARD
// ══════════════════════════════════════════════════════════════════

let leaderboardData = [];

function showLeaderboardEmpty() {
  dom.leaderboardEmptyState().classList.remove("hidden");
  dom.leaderboardErrorState().classList.add("hidden");
  dom.leaderboardResults().classList.add("hidden");
}

function showLeaderboardError(message) {
  dom.leaderboardEmptyState().classList.add("hidden");
  dom.leaderboardErrorState().classList.remove("hidden");
  dom.leaderboardResults().classList.add("hidden");
  dom.leaderboardErrorMessage().textContent = message;
}

function showLeaderboardResults() {
  dom.leaderboardEmptyState().classList.add("hidden");
  dom.leaderboardErrorState().classList.add("hidden");
  dom.leaderboardResults().classList.remove("hidden");
}

function initLeaderboard() {
  dom.leaderboardScoreBtn().addEventListener("click", runLeaderboardScoring);
  dom.leaderboardExportBtn().addEventListener("click", exportLeaderboardCSV);
}

async function runLeaderboardScoring() {
  const input = dom.leaderboardInput().value.trim();
  if (!input) {
    showLeaderboardError("Please enter at least one conversation (format: borrower|agent).");
    return;
  }

  const lines = input.split("\n").filter((l) => l.trim().length > 0);
  const conversations = lines.map((line) => {
    const parts = line.split("|");
    return {
      borrower_message: (parts[0] || "").trim(),
      agent_response: (parts[1] || "").trim() || null,
    };
  });

  if (conversations.length === 0) {
    showLeaderboardError("No valid conversations found. Use format: borrower|agent");
    return;
  }

  const btn = dom.leaderboardScoreBtn();
  setLoading(btn, true);
  dom.leaderboardExportBtn().disabled = true;

  const progressWrap = dom.leaderboardProgress();
  const progressFill = dom.leaderboardProgressFill();
  const progressLabel = dom.leaderboardProgressLabel();
  progressWrap.classList.remove("hidden");
  progressFill.style.width = "0%";
  progressLabel.textContent = `0 / ${conversations.length}`;

  leaderboardData = [];

  const evaluator = dom.evaluatorSelect().value;

  try {
    for (let i = 0; i < conversations.length; i++) {
      const conv = conversations[i];
      let url = API_BASE + "/analyze/text";
      if (evaluator) {
        url += "?evaluator=" + encodeURIComponent(evaluator);
      }

      const body = { borrower_message: conv.borrower_message };
      if (conv.agent_response) {
        body.agent_response = conv.agent_response;
      }

      try {
        const response = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });

        if (response.ok) {
          const data = await response.json();
          leaderboardData.push({
            rank: 0,
            borrower: conv.borrower_message,
            agent: conv.agent_response || "",
            intent: data.repayment_intent || "—",
            riskScore: data.risk_score ?? null,
            intentAccuracy: data.agent_eval?.intent_accuracy ?? null,
            toneScore: data.agent_eval?.tone_score ?? null,
            complianceScore: data.agent_eval?.compliance_score ?? null,
            escalationScore: data.agent_eval?.escalation_score ?? null,
            overallScore: data.agent_eval?.overall_score ?? null,
          });
        } else {
          leaderboardData.push({
            rank: 0,
            borrower: conv.borrower_message,
            agent: conv.agent_response || "",
            intent: "ERROR",
            riskScore: null,
            intentAccuracy: null,
            toneScore: null,
            complianceScore: null,
            escalationScore: null,
            overallScore: null,
          });
        }
      } catch {
        leaderboardData.push({
          rank: 0,
          borrower: conv.borrower_message,
          agent: conv.agent_response || "",
          intent: "ERROR",
          riskScore: null,
          intentAccuracy: null,
          toneScore: null,
          complianceScore: null,
          escalationScore: null,
          overallScore: null,
        });
      }

      const pct = ((i + 1) / conversations.length) * 100;
      progressFill.style.width = pct + "%";
      progressLabel.textContent = `${i + 1} / ${conversations.length}`;
    }

    // Sort by overall_score descending
    leaderboardData.sort((a, b) => {
      if (a.overallScore == null && b.overallScore == null) return 0;
      if (a.overallScore == null) return 1;
      if (b.overallScore == null) return -1;
      return b.overallScore - a.overallScore;
    });

    leaderboardData.forEach((item, idx) => { item.rank = idx + 1; });

    renderLeaderboard();
    showLeaderboardResults();
    dom.leaderboardExportBtn().disabled = false;

  } catch (err) {
    console.error("Leaderboard scoring failed:", err);
    showLeaderboardError("Failed to score conversations. Check API connection.");
  } finally {
    setLoading(btn, false);
    progressWrap.classList.add("hidden");
  }
}

function renderLeaderboard() {
  const tbody = dom.leaderboardTbody();
  tbody.innerHTML = "";

  leaderboardData.forEach((item) => {
    const tr = document.createElement("tr");

    // Score pill class
    let pillClass = "";
    if (item.overallScore != null) {
      if (item.overallScore >= 7.5) pillClass = "good";
      else if (item.overallScore >= 5) pillClass = "mixed";
      else pillClass = "poor";
    }

    const riskDisplay = item.riskScore != null ? (item.riskScore * 100).toFixed(0) + "%" : "—";
    const scoreDisplay = item.overallScore != null
      ? `<span class="score-pill ${pillClass}">${item.overallScore.toFixed(1)}</span>`
      : "—";

    tr.innerHTML = `
      <td class="rank-cell">${item.rank}</td>
      <td class="text-cell" title="${escapeHtml(item.borrower)}">${escapeHtml(truncate(item.borrower, 40))}</td>
      <td class="text-cell" title="${escapeHtml(item.agent)}">${escapeHtml(truncate(item.agent, 40))}</td>
      <td><span class="intent-badge-sm">${item.intent}</span></td>
      <td class="num-cell">${riskDisplay}</td>
      <td class="num-cell">${scoreDisplay}</td>
    `;

    tbody.appendChild(tr);
  });

  // Summary stats
  const scores = leaderboardData.map(d => d.overallScore).filter(s => s != null);
  dom.lbTotalCount().textContent = leaderboardData.length;
  dom.lbAvgScore().textContent = scores.length > 0
    ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(2) : "—";
  dom.lbBestScore().textContent = scores.length > 0 ? Math.max(...scores).toFixed(2) : "—";
  dom.lbWorstScore().textContent = scores.length > 0 ? Math.min(...scores).toFixed(2) : "—";
}

function exportLeaderboardCSV() {
  if (leaderboardData.length === 0) return;

  const headers = ["Rank", "Borrower", "Agent", "Intent", "Intent Accuracy", "Tone", "Compliance", "Escalation", "Overall Score"];
  const rows = leaderboardData.map((item) => [
    item.rank,
    `"${(item.borrower || "").replace(/"/g, '""')}"`,
    `"${(item.agent || "").replace(/"/g, '""')}"`,
    item.intent,
    item.intentAccuracy != null ? item.intentAccuracy.toFixed(1) : "",
    item.toneScore != null ? item.toneScore.toFixed(1) : "",
    item.complianceScore != null ? item.complianceScore.toFixed(1) : "",
    item.escalationScore != null ? item.escalationScore.toFixed(1) : "",
    item.overallScore != null ? item.overallScore.toFixed(2) : "",
  ]);

  const csv = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "recoverybench_leaderboard.csv";
  a.click();
  URL.revokeObjectURL(url);
}

// ══════════════════════════════════════════════════════════════════
// BENCHMARK CHART (static, created once on page load)
// ══════════════════════════════════════════════════════════════════

function initBenchmarkChart() {
  const canvas = document.getElementById("benchmark-chart");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  window.benchmarkChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["NEEDS_REMINDER", "DISPUTE", "VAGUE", "HIGH_RISK", "LIKELY_PAY"],
      datasets: [{
        data: [65, 75, 85, 85, 100],
        backgroundColor: ["#EF4444", "#F59E0B", "#14B8A6", "#14B8A6", "#14B8A6"],
        borderRadius: 4,
        barThickness: 28,
      }]
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ctx.raw + "% accuracy"
          }
        }
      },
      scales: {
        x: {
          min: 0,
          max: 100,
          ticks: {
            color: "#A1A1AA",
            font: { family: "'Inter', sans-serif", size: 12 },
            callback: (v) => v + "%"
          },
          grid: { color: "#27272A" }
        },
        y: {
          ticks: {
            color: "#A1A1AA",
            font: { family: "'Inter', sans-serif", size: 12 }
          },
          grid: { display: false }
        }
      }
    }
  });
}

// ══════════════════════════════════════════════════════════════════
// EVENT WIRING
// ══════════════════════════════════════════════════════════════════

document.addEventListener("DOMContentLoaded", () => {
  // Tab navigation
  initTabs();

  // Benchmark chart
  initBenchmarkChart();

  // Text Analysis
  dom.analyzeBtn().addEventListener("click", runAnalysis);

  // Enter key in borrower textarea → analyze
  dom.borrowerInput().addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      runAnalysis();
    }
  });

  // Example chips
  document.querySelectorAll(".example-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const borrower = chip.getAttribute("data-borrower") || "";
      const agent = chip.getAttribute("data-agent") || "";

      dom.borrowerInput().value = borrower;
      dom.agentInput().value = agent;

      runAnalysis();
    });
  });

  // Audio Analysis
  initAudio();

  // Leaderboard
  initLeaderboard();
});
