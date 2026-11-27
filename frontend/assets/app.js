/* VoiceCity Local Web Studio Frontend
 * Pure ES2022 client communicating strictly with local loopback FastAPI endpoints.
 * Separates Standard TTS, Reference-Audio Voice Cloning, Voice Conversion, and
 * Experimental Cross-Linguistic Conversion honestly across all views.
 */

const state = {
  view: "dashboard",
  capabilities: null,
  diagnostics: null,
  settings: null,
  voices: [],
  generations: [],
  jobs: [],
  activePreviewId: null,
  activeJobId: null,
  jobPollTimer: null,
};

const VIEW_META = {
  dashboard: {
    title: "Dashboard",
    subtitle: "Private, local-first Urdu and English personal voice studio.",
  },
  voices: {
    title: "Voice Library",
    subtitle: "Inspect original WAV recordings, edit reference transcripts, and re-extract clean segments.",
  },
  "create-voice": {
    title: "Create Voice Profile",
    subtitle: "Import your personal WAV recording once; VoiceCity preserves the original and prepares a clean clip.",
  },
  studio: {
    title: "Text to Speech Studio",
    subtitle: "Queue Urdu, English, or mixed speech synthesis with live progress, cancellation, and capability honesty.",
  },
  preview: {
    title: "Audio Preview",
    subtitle: "Listen to generated clips, compare attempts side by side, and export locally as WAV or MP3.",
  },
  history: {
    title: "Generation History",
    subtitle: "Filter, replay, refine, download, or delete past speech generations.",
  },
  settings: {
    title: "Settings",
    subtitle: "Manage engines, separated capability classes, licenses, 5-axis verification, and host diagnostics.",
  },
};

const SAMPLES = {
  ur: "السلام علیکم، وائس سٹی میں خوش آمدید۔ یہ میری اپنی آواز کا پہلا مقامی تجربہ ہے۔",
  en: "Welcome to VoiceCity. This is a local-first personal voice studio running privately on Linux.",
  mixed: "آج شام کو ہم اپنی نئی application کا launch review کریں گے، براہ کرم وقت پر جوائن کریں۔",
};

const CAP_LABELS = {
  standard_tts: "Standard TTS (Not Cloning)",
  reference_voice_cloning: "Reference-Audio Voice Cloning",
  voice_conversion: "Voice Conversion (Audio-to-Audio)",
  cross_linguistic_voice_conversion: "Cross-Linguistic Conversion",
};

const MATURITY_LABELS = {
  experimental: "Experimental",
  technically_integrated: "Technically Integrated",
  empirically_verified: "Empirically Verified",
};

const LICENSE_LABELS = {
  permissive_commercial: "Permissive Commercial",
  share_alike_optional: "Optional ShareAlike (CC-BY-SA)",
  non_commercial_restricted: "Non-Commercial Restricted",
  none: "No Weights",
};

const STATUS_LABELS = {
  empirically_verified: ["Empirically Verified", "badge-ok"],
  ready_unverified_listening: ["Ready (Listening Unverified)", "badge-ok"],
  ready_experimental: ["Ready (Experimental)", "badge-warn"],
  experimental_not_installed: ["Experimental · Not Installed", "badge-warn"],
  not_installed: ["Not Installed", "badge-neutral"],
  unsupported: ["Unsupported", "badge-error"],
};

function esc(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function fmtSeconds(sec) {
  const n = Number(sec || 0);
  if (n >= 60) {
    const mins = Math.floor(n / 60);
    const rem = (n % 60).toFixed(1).padStart(4, "0");
    return `${mins}m ${rem}s`;
  }
  return `${n.toFixed(1)}s`;
}

function fmtDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function statusBadgeHtml(code) {
  const [label, cls] = STATUS_LABELS[code] || [code, "badge-neutral"];
  return `<span class="badge ${cls}">${esc(label)}</span>`;
}

let toastTimer = null;
function showToast(message) {
  const el = document.getElementById("global-toast");
  if (!el) return;
  el.textContent = message;
  el.hidden = false;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    el.hidden = true;
  }, 3600);
}

async function apiJson(url, options = {}) {
  const resp = await fetch(url, options);
  let data = null;
  try {
    data = await resp.json();
  } catch {
    data = null;
  }
  if (!resp.ok) {
    const detail = data?.detail;
    const msg =
      typeof detail === "string"
        ? detail
        : detail?.message || `Request failed (${resp.status})`;
    const err = new Error(msg);
    err.status = resp.status;
    err.detail = detail;
    throw err;
  }
  return data;
}

function switchView(viewId) {
  if (!VIEW_META[viewId]) return;
  state.view = viewId;

  document.querySelectorAll(".nav-item").forEach((btn) => {
    const active = btn.dataset.view === viewId;
    btn.classList.toggle("active", active);
    btn.setAttribute("aria-selected", active ? "true" : "false");
  });

  document.querySelectorAll(".view").forEach((section) => {
    const active = section.id === `view-${viewId}`;
    section.hidden = !active;
    section.classList.toggle("active", active);
  });

  const meta = VIEW_META[viewId];
  document.getElementById("topbar-title").textContent = meta.title;
  document.getElementById("topbar-subtitle").textContent = meta.subtitle;

  if (viewId === "preview") renderPreview();
  if (viewId === "history") renderHistory();
  if (viewId === "voices") renderVoices();
  if (viewId === "studio") renderStudioMeta();
  if (viewId === "settings") renderSettings();
}

async function loadAllData() {
  try {
    const [caps, diag, settings, voicesRes, gensRes, jobsRes] = await Promise.all([
      apiJson("/api/v1/capabilities"),
      apiJson("/api/v1/diagnostics"),
      apiJson("/api/v1/settings"),
      apiJson("/api/v1/voices"),
      apiJson("/api/v1/generations"),
      apiJson("/api/v1/jobs"),
    ]);
    state.capabilities = caps;
    state.diagnostics = diag;
    state.settings = settings;
    state.voices = voicesRes.voices || [];
    state.generations = gensRes.generations || [];
    state.jobs = jobsRes.jobs || [];

    if (!state.activePreviewId && state.generations.length > 0) {
      const firstCompleted = state.generations.find((g) => g.has_audio);
      if (firstCompleted) state.activePreviewId = firstCompleted.id;
    }

    renderSidebarStatus();
    renderDashboard();
    renderVoices();
    renderStudioMeta();
    renderPreview();
    renderHistory();
    renderSettings();
  } catch (err) {
    showToast(`Failed to reach local VoiceCity API: ${err.message}`);
  }
}

function renderSidebarStatus() {
  const caps = state.capabilities;
  document.getElementById("nav-voice-count").textContent = String(state.voices.length);
  document.getElementById("nav-history-count").textContent = String(state.generations.length);

  if (!caps) return;
  const eng = caps.active_engine;
  const dot = document.getElementById("sidebar-engine-dot");
  const label = document.getElementById("sidebar-engine-label");
  dot.className = `status-dot ${eng.ready ? "status-ok" : "status-warn"}`;
  label.textContent = eng.ready
    ? `${eng.engine_id} (${MATURITY_LABELS[eng.maturity_level] || eng.maturity_level})`
    : `Engine Not Installed`;

  const procBadge = document.getElementById("topbar-processing-badge");
  procBadge.textContent = caps.remote_inference ? "Remote Inference Enabled" : "Processing: On Device";
  procBadge.className = `badge ${caps.remote_inference ? "badge-warn" : "badge-ok"}`;
}

function renderDashboard() {
  const caps = state.capabilities;
  const diag = state.diagnostics;
  document.getElementById("dash-voice-count").textContent = String(state.voices.length);
  document.getElementById("dash-gen-count").textContent = String(state.generations.length);

  if (caps) {
    const eng = caps.active_engine;
    document.getElementById("dash-engine-name").textContent = eng.display_name;
    document.getElementById("dash-engine-state").textContent = eng.ready
      ? `${CAP_LABELS[eng.capability_class] || eng.capability_class} · ${MATURITY_LABELS[eng.maturity_level] || eng.maturity_level}`
      : "Not installed yet (honest status)";

    const banner = document.getElementById("dashboard-engine-banner");
    if (!eng.ready) {
      banner.hidden = false;
      banner.innerHTML = `<strong>Local Speech Engine Not Yet Installed:</strong> ${esc(
        eng.status_message
      )} You can already import your WAV recording, inspect audio quality, add your reference transcript, and prepare your voice profile.`;
    } else if (eng.maturity_level === "experimental") {
      banner.hidden = false;
      banner.innerHTML = `<strong>Experimental Pipeline Active:</strong> ${esc(eng.status_message)}`;
    } else {
      banner.hidden = true;
    }

    const byType = caps.capabilities_by_type || {};
    const matrixEl = document.getElementById("dash-capability-matrix");
    if (matrixEl && byType.reference_voice_cloning) {
      matrixEl.innerHTML = `
        <div class="kv-item">
          <span class="kv-label">Urdu Reference Voice Cloning</span>
          <span class="kv-val">${statusBadgeHtml(byType.reference_voice_cloning.urdu)}</span>
          <span class="meta-text">F5-TTS OpenBible Urdu (CC-BY-SA-4.0 optional)</span>
        </div>
        <div class="kv-item">
          <span class="kv-label">English Reference Voice Cloning</span>
          <span class="kv-val">${statusBadgeHtml(byType.reference_voice_cloning.english)}</span>
          <span class="meta-text">Qwen3-TTS 0.6B-Base (Apache-2.0)</span>
        </div>
        <div class="kv-item">
          <span class="kv-label">Mixed Urdu-English Cloning</span>
          <span class="kv-val">${statusBadgeHtml(byType.reference_voice_cloning.mixed)}</span>
          <span class="meta-text">Dual Router (requires both Urdu + English engines)</span>
        </div>
        <div class="kv-item">
          <span class="kv-label">Standard TTS (NOT Voice Cloning)</span>
          <span class="kv-val">${statusBadgeHtml(byType.standard_tts?.urdu || "not_installed")}</span>
          <span class="meta-text">Indic Parler-TTS (Apache-2.0 · synthetic voice only)</span>
        </div>
        <div class="kv-item">
          <span class="kv-label">Voice Conversion (Audio-to-Audio)</span>
          <span class="kv-val">${statusBadgeHtml(byType.voice_conversion?.english || "not_installed")}</span>
          <span class="meta-text">OpenVoice v2 (MIT · Urdu NOT native)</span>
        </div>
        <div class="kv-item">
          <span class="kv-label">Cross-Linguistic Conversion (Urdu)</span>
          <span class="kv-val">${statusBadgeHtml(byType.cross_linguistic_voice_conversion?.urdu_experimental || "experimental_not_installed")}</span>
          <span class="meta-text">Experimental: Indic Parler -&gt; OpenVoice v2</span>
        </div>
      `;
    }
  }

  if (diag?.hardware) {
    const hw = diag.hardware;
    document.getElementById("dash-compute-mode").textContent = hw.is_mobile_proot_env
      ? "Phone Dev Container"
      : hw.recommended_device.toUpperCase();
    document.getElementById("dash-compute-hint").textContent = `${hw.cpu_logical_cores} cores · ${hw.ram_available_gb} GB RAM free · ${hw.disk_free_gb} GB disk free`;
  }

  const recentVoicesEl = document.getElementById("dash-recent-voices");
  if (state.voices.length === 0) {
    recentVoicesEl.innerHTML = `<div class="empty-state">No voice profiles yet. Import your ~2-minute WAV recording to get started.</div>`;
  } else {
    recentVoicesEl.innerHTML = state.voices
      .slice(0, 4)
      .map(
        (v) => `
      <div class="compact-row">
        <div>
          <strong>${esc(v.display_name)}</strong>
          <div class="meta-text">${esc(v.source_audio_name)} · ${fmtSeconds(v.source_duration_seconds)} (${v.source_sample_rate_hz} Hz)</div>
        </div>
        <span class="badge ${v.status === "ready" ? "badge-ok" : "badge-warn"}">${esc(v.status)}</span>
      </div>`
      )
      .join("");
  }

  const recentGensEl = document.getElementById("dash-recent-generations");
  if (state.generations.length === 0) {
    recentGensEl.innerHTML = `<div class="empty-state">No generated audio clips yet.</div>`;
  } else {
    recentGensEl.innerHTML = state.generations
      .slice(0, 5)
      .map(
        (g) => `
      <div class="compact-row">
        <div>
          <strong>${esc(g.voice_profile_name)}</strong> · <span class="badge badge-neutral">${esc(g.language.toUpperCase())}</span>
          <div class="meta-text">${esc(g.text.slice(0, 90))}${g.text.length > 90 ? "…" : ""}</div>
        </div>
        <button type="button" class="btn btn-secondary btn-sm" data-open-preview="${esc(g.id)}">Preview</button>
      </div>`
      )
      .join("");
  }
}

function renderVoices() {
  const container = document.getElementById("voices-list-container");
  const query = (document.getElementById("voice-search-input")?.value || "").trim().toLowerCase();
  const filtered = state.voices.filter(
    (v) =>
      !query ||
      v.display_name.toLowerCase().includes(query) ||
      v.source_audio_name.toLowerCase().includes(query)
  );

  if (filtered.length === 0) {
    container.innerHTML = `<div class="empty-state">${
      state.voices.length === 0
        ? 'Your Voice Library is empty. Click "+ Create Voice Profile" to import your personal WAV recording.'
        : "No voice profiles match your filter."
    }</div>`;
    return;
  }

  container.innerHTML = filtered
    .map((v) => {
      const warnHtml =
        v.warnings && v.warnings.length
          ? `<ul class="warning-list">${v.warnings.map((w) => `<li>${esc(w)}</li>`).join("")}</ul>`
          : "";
      return `
      <article class="item-card" data-voice-card="${esc(v.id)}">
        <div class="item-card-head">
          <div>
            <h3 class="item-card-title">${esc(v.display_name)}</h3>
            <div class="meta-text">Source: ${esc(v.source_audio_name)} · Created ${esc(fmtDate(v.created_at))}</div>
          </div>
          <div class="action-row-inline">
            <span class="badge ${v.status === "ready" ? "badge-ok" : "badge-warn"}">${esc(v.status)}</span>
            <button type="button" class="btn btn-secondary btn-sm" data-use-voice="${esc(v.id)}">Use in Studio</button>
            <button type="button" class="btn btn-secondary btn-sm" data-rename-voice="${esc(v.id)}">Rename</button>
            <button type="button" class="btn btn-danger btn-sm" data-delete-voice="${esc(v.id)}">Delete</button>
          </div>
        </div>

        <div class="kv-list">
          <div class="kv-item"><span class="kv-label">Original Length</span><span class="kv-val">${fmtSeconds(v.source_duration_seconds)}</span></div>
          <div class="kv-item"><span class="kv-label">Format</span><span class="kv-val">${v.source_sample_rate_hz} Hz · ${v.source_channels}ch · ${v.source_bit_depth}-bit</span></div>
          <div class="kv-item"><span class="kv-label">Levels (Peak / RMS)</span><span class="kv-val">${v.peak_dbfs} / ${v.rms_dbfs} dBFS</span></div>
          <div class="kv-item"><span class="kv-label">Clipping / Silence</span><span class="kv-val">${v.clipping_samples} samples · ${Math.round(v.silence_ratio * 100)}% silent</span></div>
          <div class="kv-item"><span class="kv-label">Prepared Reference</span><span class="kv-val">${fmtSeconds(v.reference_duration_seconds)} (from ${fmtSeconds(v.reference_start_seconds)})</span></div>
        </div>

        ${warnHtml}

        <div class="two-col" style="margin-top: 10px;">
          <div class="audio-block">
            <span class="meta-text"><strong>Prepared Reference Clip</strong> (24 kHz Mono Normalized)</span>
            <audio controls preload="none" src="${esc(v.reference_audio_url)}"></audio>
          </div>
          <div class="audio-block">
            <span class="meta-text"><strong>Original Recording</strong> (Preserved Untouched)</span>
            <audio controls preload="none" src="${esc(v.source_audio_url)}"></audio>
          </div>
        </div>

        <div class="inline-editor">
          <div>
            <label for="transcript-${esc(v.id)}">Reference Clip Transcript (Required for offline F5-TTS Urdu)</label>
            <input id="transcript-${esc(v.id)}" type="text" dir="auto" value="${esc(v.reference_transcript || "")}" placeholder="Enter exact words spoken in the prepared 6-10s reference clip…" />
          </div>
          <div class="action-row-inline">
            <button type="button" class="btn btn-secondary btn-sm" data-save-transcript="${esc(v.id)}">Save Transcript</button>
            <button type="button" class="btn btn-secondary btn-sm" data-reprepare-voice="${esc(v.id)}">Re-Slice 8s Clip</button>
          </div>
        </div>
      </article>`;
    })
    .join("");
}

function renderInspectionResult(voice) {
  const target = document.getElementById("import-inspection-result");
  const warnHtml = voice.warnings?.length
    ? `<ul class="warning-list">${voice.warnings.map((w) => `<li>${esc(w)}</li>`).join("")}</ul>`
    : `<div class="callout callout-ok" style="margin-top:12px;">Clean acoustic profile detected with no quality warnings.</div>`;

  target.className = "";
  target.innerHTML = `
    <div class="callout callout-ok">
      <strong>Profile "${esc(voice.display_name)}" created locally.</strong>
      Your original recording is untouched and a clean ${fmtSeconds(voice.reference_duration_seconds)} reference segment has been prepared.
    </div>
    <div class="kv-list">
      <div class="kv-item"><span class="kv-label">Original Duration</span><span class="kv-val">${fmtSeconds(voice.source_duration_seconds)}</span></div>
      <div class="kv-item"><span class="kv-label">Sample Rate / Ch</span><span class="kv-val">${voice.source_sample_rate_hz} Hz / ${voice.source_channels}ch</span></div>
      <div class="kv-item"><span class="kv-label">Peak / RMS</span><span class="kv-val">${voice.peak_dbfs} / ${voice.rms_dbfs} dBFS</span></div>
      <div class="kv-item"><span class="kv-label">Extracted Window</span><span class="kv-val">${fmtSeconds(voice.reference_start_seconds)} → +${fmtSeconds(voice.reference_duration_seconds)}</span></div>
    </div>
    ${warnHtml}
    <div class="audio-block">
      <span class="meta-text"><strong>Preview Prepared Reference Clip</strong></span>
      <audio controls src="${esc(voice.reference_audio_url)}"></audio>
    </div>
    <div class="action-row">
      <button type="button" class="btn btn-primary" data-use-voice="${esc(voice.id)}">Open in Speech Studio</button>
      <button type="button" class="btn btn-secondary" data-goto="voices">Add Reference Transcript in Library</button>
    </div>`;
}

function renderStudioMeta() {
  const voiceSelect = document.getElementById("studio-voice-select");
  const prevVal = voiceSelect.value;
  if (state.voices.length === 0) {
    voiceSelect.innerHTML = `<option value="">No voice profiles — create one first</option>`;
  } else {
    voiceSelect.innerHTML = state.voices
      .map(
        (v) =>
          `<option value="${esc(v.id)}">${esc(v.display_name)} (${fmtSeconds(v.reference_duration_seconds)} ref${
            v.reference_transcript ? " · transcript set" : ""
          })</option>`
      )
      .join("");
    if (prevVal && state.voices.some((v) => v.id === prevVal)) {
      voiceSelect.value = prevVal;
    }
  }

  const caps = state.capabilities;
  if (!caps) return;
  const eng = caps.active_engine;
  const alertEl = document.getElementById("studio-engine-alert");

  if (!eng.ready) {
    alertEl.hidden = false;
    alertEl.innerHTML = `<strong>Active Engine Not Installed (${esc(CAP_LABELS[eng.capability_class] || eng.capability_class)}):</strong> ${esc(
      eng.status_message
    )}`;
  } else if (eng.capability_class === "standard_tts") {
    alertEl.hidden = false;
    alertEl.innerHTML = `<strong>Notice — Standard TTS Only (NOT Voice Cloning):</strong> ${esc(
      eng.display_name
    )} ignores your uploaded WAV recording and uses a synthetic speaker. Switch to a Reference-Audio Voice Cloning engine in Settings for personal voice cloning.`;
  } else if (eng.maturity_level === "experimental") {
    alertEl.hidden = false;
    alertEl.innerHTML = `<strong>Experimental Mode:</strong> ${esc(eng.status_message)}`;
  } else {
    alertEl.hidden = true;
  }

  document.getElementById("studio-engine-details").innerHTML = `
    <div class="kv-item"><span class="kv-label">Engine</span><span class="kv-val">${esc(eng.display_name)}</span></div>
    <div class="kv-item"><span class="kv-label">Capability Class</span><span class="kv-val">${esc(CAP_LABELS[eng.capability_class] || eng.capability_class)}</span></div>
    <div class="kv-item"><span class="kv-label">Maturity</span><span class="kv-val">${esc(MATURITY_LABELS[eng.maturity_level] || eng.maturity_level)}</span></div>
    <div class="kv-item"><span class="kv-label">Uses Ref Audio</span><span class="kv-val">${eng.uses_reference_audio ? "Yes" : "No (Synthetic TTS)"}</span></div>
    <div class="kv-item"><span class="kv-label">Urdu / English / Mixed</span><span class="kv-val">${esc(caps.urdu)} / ${esc(caps.english)} / ${esc(caps.mixed_language)}</span></div>
    <div class="kv-item"><span class="kv-label">Weight License</span><span class="kv-val">${esc(eng.weight_license)}</span></div>
  `;

  const jobsEl = document.getElementById("studio-jobs-list");
  if (jobsEl) {
    if (!state.jobs.length) {
      jobsEl.innerHTML = `<span class="meta-text">No queued generation jobs yet.</span>`;
    } else {
      jobsEl.innerHTML = state.jobs
        .slice(0, 5)
        .map(
          (j) => `
        <div class="compact-row">
          <div>
            <strong>${esc(j.language.toUpperCase())}</strong> · <span class="meta-text">${esc(j.stage_message)}</span>
            <div class="meta-text">${esc(j.text_preview)}</div>
          </div>
          <span class="badge ${
            j.status === "completed" ? "badge-ok" : j.status === "failed" ? "badge-error" : "badge-warn"
          }">${esc(j.status)} (${j.progress_percent}%)</span>
        </div>`
        )
        .join("");
    }
  }
}

function renderPreview() {
  const content = document.getElementById("preview-content");
  const exportActions = document.getElementById("preview-export-actions");
  const compareList = document.getElementById("preview-compare-list");

  const active = state.generations.find((g) => g.id === state.activePreviewId);
  if (!active) {
    exportActions.innerHTML = "";
    content.className = "empty-state";
    content.innerHTML = `<p>Select any generated clip from Generation History or generate speech in the Studio to preview and export.</p>`;
  } else {
    content.className = "";
    const mp3Disabled = !active.mp3_download_url;
    exportActions.innerHTML = `
      ${
        active.wav_download_url
          ? `<a class="btn btn-primary btn-sm" href="${esc(active.wav_download_url)}">Download WAV</a>`
          : ""
      }
      ${
        mp3Disabled
          ? `<button type="button" class="btn btn-secondary btn-sm" disabled title="Install ffmpeg on Linux Mint to enable MP3 export">MP3 Unavailable (No ffmpeg)</button>`
          : `<a class="btn btn-secondary btn-sm" href="${esc(active.mp3_download_url)}">Download MP3</a>`
      }
      <button type="button" class="btn btn-secondary btn-sm" data-reuse-text="${esc(active.id)}">Refine in Studio</button>
    `;

    content.innerHTML = `
      <div class="kv-list">
        <div class="kv-item"><span class="kv-label">Voice Profile</span><span class="kv-val">${esc(active.voice_profile_name)}</span></div>
        <div class="kv-item"><span class="kv-label">Language</span><span class="kv-val">${esc(active.language.toUpperCase())}</span></div>
        <div class="kv-item"><span class="kv-label">Duration / Rate</span><span class="kv-val">${fmtSeconds(active.duration_seconds)} · ${active.sample_rate_hz} Hz</span></div>
        <div class="kv-item"><span class="kv-label">Generation Time</span><span class="kv-val">${active.generation_time_seconds.toFixed(2)}s</span></div>
        <div class="kv-item"><span class="kv-label">Engine / Model</span><span class="kv-val">${esc(active.model_id)}</span></div>
      </div>
      <div class="audio-block">
        <span class="meta-text"><strong>Generated Output Playback</strong></span>
        ${
          active.audio_url
            ? `<audio controls src="${esc(active.audio_url)}"></audio>`
            : `<p class="meta-text">No audio file available for this record.</p>`
        }
      </div>
      <div class="subpanel">
        <h3>Input Script</h3>
        <p dir="auto" class="${active.language === "ur" ? "urdu-text" : ""}" style="margin:0;">${esc(active.text)}</p>
      </div>
    `;
  }

  const completed = state.generations.filter((g) => g.has_audio);
  if (completed.length === 0) {
    compareList.innerHTML = `<div class="empty-state">No completed audio clips available for side-by-side comparison yet.</div>`;
  } else {
    compareList.innerHTML = completed
      .slice(0, 8)
      .map(
        (g) => `
      <div class="compact-row">
        <div style="flex:1; min-width:0;">
          <strong>${esc(g.voice_profile_name)}</strong> · <span class="badge badge-neutral">${esc(g.language.toUpperCase())}</span> · <span class="meta-text">${fmtSeconds(g.duration_seconds)}</span>
          <div class="meta-text">${esc(g.text.slice(0, 80))}${g.text.length > 80 ? "…" : ""}</div>
        </div>
        <audio controls preload="none" src="${esc(g.audio_url)}" style="max-width:260px;"></audio>
        <button type="button" class="btn btn-secondary btn-sm" data-open-preview="${esc(g.id)}">Inspect</button>
      </div>`
      )
      .join("");
  }
}

function renderHistory() {
  const voiceFilter = document.getElementById("history-voice-filter");
  const prevVoice = voiceFilter.value;
  voiceFilter.innerHTML =
    `<option value="">All voices</option>` +
    state.voices.map((v) => `<option value="${esc(v.id)}">${esc(v.display_name)}</option>`).join("");
  if (prevVoice) voiceFilter.value = prevVoice;

  const langFilter = document.getElementById("history-lang-filter").value;
  const items = state.generations.filter(
    (g) =>
      (!voiceFilter.value || g.voice_profile_id === voiceFilter.value) &&
      (!langFilter || g.language === langFilter)
  );

  const container = document.getElementById("history-list-container");
  if (items.length === 0) {
    container.innerHTML = `<div class="empty-state">No speech generation history records found.</div>`;
    return;
  }

  container.innerHTML = items
    .map(
      (g) => `
    <article class="item-card">
      <div class="item-card-head">
        <div>
          <h3 class="item-card-title">${esc(g.voice_profile_name)} · <span class="badge badge-neutral">${esc(g.language.toUpperCase())}</span></h3>
          <div class="meta-text">${esc(fmtDate(g.created_at))} · ${esc(g.model_id)} · ${fmtSeconds(g.duration_seconds)}</div>
        </div>
        <div class="action-row-inline">
          <span class="badge ${g.status === "completed" ? "badge-ok" : "badge-error"}">${esc(g.status)}</span>
          ${g.has_audio ? `<button type="button" class="btn btn-secondary btn-sm" data-open-preview="${esc(g.id)}">Preview</button>` : ""}
          ${g.wav_download_url ? `<a class="btn btn-secondary btn-sm" href="${esc(g.wav_download_url)}">WAV</a>` : ""}
          <button type="button" class="btn btn-secondary btn-sm" data-reuse-text="${esc(g.id)}">Reuse Text</button>
          <button type="button" class="btn btn-danger btn-sm" data-delete-gen="${esc(g.id)}">Delete</button>
        </div>
      </div>
      <p dir="auto" style="margin:6px 0 8px;">${esc(g.text)}</p>
      ${g.error_message ? `<div class="callout callout-error">${esc(g.error_message)}</div>` : ""}
      ${g.audio_url ? `<audio controls preload="none" src="${esc(g.audio_url)}" style="width:100%;"></audio>` : ""}
    </article>`
    )
    .join("");
}

function renderSettings() {
  const s = state.settings;
  const diag = state.diagnostics;
  if (!s) return;

  const engSelect = document.getElementById("settings-engine-select");
  engSelect.innerHTML = (s.available_engines || [])
    .map(
      (e) =>
        `<option value="${esc(e.engine_id)}">${esc(e.display_name)} (${e.ready ? "Ready" : "Not Installed"})</option>`
    )
    .join("");
  engSelect.value = s.preferences.active_engine;

  document.getElementById("settings-device-select").value = s.preferences.compute_device;
  document.getElementById("settings-lang-select").value = s.preferences.default_language;
  document.getElementById("settings-speed-input").value = String(s.preferences.default_speed);
  document.getElementById("settings-export-select").value = s.preferences.default_export_format;
  document.getElementById("settings-offline-checkbox").checked = Boolean(
    s.preferences.prefer_offline_only
  );

  document.getElementById("settings-storage-kv").innerHTML = `
    <div class="kv-item"><span class="kv-label">Bind Address</span><span class="kv-val code-inline">${esc(s.runtime.host)}:${s.runtime.port}</span></div>
    <div class="kv-item"><span class="kv-label">Local Data Directory</span><span class="kv-val code-inline">${esc(s.runtime.data_dir)}</span></div>
    <div class="kv-item"><span class="kv-label">Model Cache Directory</span><span class="kv-val code-inline">${esc(s.runtime.model_dir)}</span></div>
    <div class="kv-item"><span class="kv-label">Remote Cloud Inference</span><span class="kv-val">${s.runtime.remote_inference_enabled ? "Enabled" : "Disabled (Local Only)"}</span></div>
    <div class="kv-item"><span class="kv-label">MP3 Export (ffmpeg)</span><span class="kv-val">${s.runtime.mp3_export_available ? "Available" : "Unavailable (WAV Only)"}</span></div>
  `;

  document.getElementById("settings-engines-list").innerHTML = (s.available_engines || [])
    .map((e) => {
      const v = e.verification || {};
      const caveatsHtml =
        e.caveats && e.caveats.length
          ? `<ul class="warning-list">${e.caveats.map((c) => `<li>${esc(c)}</li>`).join("")}</ul>`
          : "";
      return `
    <article class="item-card">
      <div class="item-card-head">
        <div>
          <h3 class="item-card-title">${esc(e.display_name)}</h3>
          <div class="meta-text">ID: <span class="code-inline">${esc(e.engine_id)}</span> · Est. Download: ${e.estimated_download_gb} GB · RAM &ge;${e.min_ram_gb} GB${
        e.min_vram_gb ? ` · VRAM &ge;${e.min_vram_gb} GB` : ""
      }</div>
        </div>
        <div class="action-row-inline">
          <span class="badge ${e.capability_class === "reference_voice_cloning" ? "badge-ok" : "badge-neutral"}">${esc(
        CAP_LABELS[e.capability_class] || e.capability_class
      )}</span>
          <span class="badge ${e.maturity_level === "experimental" ? "badge-warn" : "badge-neutral"}">${esc(
        MATURITY_LABELS[e.maturity_level] || e.maturity_level
      )}</span>
          <span class="badge ${e.license_category === "permissive_commercial" ? "badge-ok" : "badge-warn"}">${esc(
        LICENSE_LABELS[e.license_category] || e.license_category
      )}</span>
          <span class="badge ${e.ready ? "badge-ok" : "badge-warn"}">${e.ready ? "Ready" : "Not Installed"}</span>
        </div>
      </div>
      <div class="kv-list">
        <div class="kv-item"><span class="kv-label">Code License</span><span class="kv-val">${esc(e.code_license)}</span></div>
        <div class="kv-item"><span class="kv-label">Weight License</span><span class="kv-val">${esc(e.weight_license)}</span></div>
        <div class="kv-item"><span class="kv-label">Native / Experimental Langs</span><span class="kv-val">Native: ${esc((e.verified_native_languages || []).join(", ") || "None")} | Exp: ${esc((e.experimental_languages || []).join(", ") || "None")}</span></div>
        <div class="kv-item"><span class="kv-label">CPU Feasibility</span><span class="kv-val">${esc(e.cpu_feasible)}</span></div>
      </div>
      <div class="verify-grid" aria-label="Five-axis verification status">
        <span class="badge ${v.automated_tests_passed ? "badge-ok" : "badge-neutral"}">Automated Tests: ${v.automated_tests_passed ? "Passed" : "Pending"}</span>
        <span class="badge ${v.model_integration_verified ? "badge-ok" : "badge-neutral"}">Model Load Verified: ${v.model_integration_verified ? "Yes" : "Pending"}</span>
        <span class="badge ${v.actual_speech_generated ? "badge-ok" : "badge-neutral"}">Actual Speech Generated: ${v.actual_speech_generated ? "Yes" : "No"}</span>
        <span class="badge ${v.human_listening_completed ? "badge-ok" : "badge-neutral"}">Human Listening: ${v.human_listening_completed ? "Done" : "Pending"}</span>
        <span class="badge ${v.commercial_licensing_verified ? "badge-ok" : "badge-warn"}">License Checked: ${v.commercial_licensing_verified ? "Yes" : "Pending"}</span>
      </div>
      ${caveatsHtml}
      <p class="field-help" style="margin-top:10px;">${esc(e.status_message)}</p>
    </article>`;
    })
    .join("");

  if (diag?.hardware) {
    const hw = diag.hardware;
    document.getElementById("diag-host-badge").textContent = `${hw.os_pretty_name} (${hw.architecture})`;
    const gpuText =
      hw.gpus && hw.gpus.length
        ? hw.gpus.map((g) => `${g.vendor} ${g.name}${g.vram_mb ? ` (${g.vram_mb} MiB)` : ""}`).join("; ")
        : "None detected (CPU mode)";
    document.getElementById("settings-hardware-kv").innerHTML = `
      <div class="kv-item"><span class="kv-label">CPU</span><span class="kv-val">${esc(hw.cpu_model)} (${hw.cpu_logical_cores} cores)</span></div>
      <div class="kv-item"><span class="kv-label">RAM</span><span class="kv-val">${hw.ram_available_gb} GB free / ${hw.ram_total_gb} GB total</span></div>
      <div class="kv-item"><span class="kv-label">Disk Free</span><span class="kv-val">${hw.disk_free_gb} GB</span></div>
      <div class="kv-item"><span class="kv-label">GPU</span><span class="kv-val">${esc(gpuText)}</span></div>
      <div class="kv-item"><span class="kv-label">Python</span><span class="kv-val">${esc(hw.python_version)}</span></div>
      <div class="kv-item"><span class="kv-label">Recommended Device</span><span class="kv-val">${esc(hw.recommended_device.toUpperCase())}</span></div>
    `;
    document.getElementById("settings-hardware-warnings").innerHTML = (hw.warnings || [])
      .map((w) => `<div class="callout callout-warn" style="margin-top:10px;margin-bottom:0;">${esc(w)}</div>`)
      .join("");
  }
}

async function pollJob(jobId) {
  const box = document.getElementById("studio-job-progress");
  const stageEl = document.getElementById("studio-job-stage");
  const fillEl = document.getElementById("studio-progress-fill");
  const barEl = document.getElementById("studio-progress-bar");
  const errEl = document.getElementById("studio-error");

  try {
    const res = await apiJson(`/api/v1/jobs/${encodeURIComponent(jobId)}`);
    const job = res.job;
    box.hidden = false;
    stageEl.textContent = `${job.stage_message} (${job.progress_percent}%)`;
    fillEl.style.width = `${job.progress_percent}%`;
    barEl.setAttribute("aria-valuenow", String(job.progress_percent));

    if (job.status === "completed") {
      stopJobPolling();
      box.hidden = true;
      state.activePreviewId = job.generation_id;
      showToast("Speech generated locally.");
      await loadAllData();
      switchView("preview");
      return;
    }
    if (job.status === "cancelled") {
      stopJobPolling();
      box.hidden = true;
      showToast("Generation cancelled.");
      await loadAllData();
      return;
    }
    if (job.status === "failed") {
      stopJobPolling();
      box.hidden = true;
      errEl.textContent = job.error_message || "Generation failed.";
      errEl.hidden = false;
      await loadAllData();
    }
  } catch (err) {
    stopJobPolling();
    box.hidden = true;
    errEl.textContent = err.message;
    errEl.hidden = false;
  }
}

function stopJobPolling() {
  if (state.jobPollTimer) {
    clearInterval(state.jobPollTimer);
    state.jobPollTimer = null;
  }
  state.activeJobId = null;
  const btn = document.getElementById("btn-generate-speech");
  if (btn) {
    btn.disabled = false;
    btn.textContent = "Queue Speech Generation";
  }
}

function bindEvents() {
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => switchView(btn.dataset.view));
  });

  document.body.addEventListener("click", async (ev) => {
    const gotoBtn = ev.target.closest("[data-goto]");
    if (gotoBtn) {
      switchView(gotoBtn.dataset.goto);
      return;
    }

    const useVoiceBtn = ev.target.closest("[data-use-voice]");
    if (useVoiceBtn) {
      const vid = useVoiceBtn.dataset.useVoice;
      switchView("studio");
      document.getElementById("studio-voice-select").value = vid;
      return;
    }

    const previewBtn = ev.target.closest("[data-open-preview]");
    if (previewBtn) {
      state.activePreviewId = previewBtn.dataset.openPreview;
      switchView("preview");
      return;
    }

    const reuseBtn = ev.target.closest("[data-reuse-text]");
    if (reuseBtn) {
      const rec = state.generations.find((g) => g.id === reuseBtn.dataset.reuseText);
      if (rec) {
        switchView("studio");
        document.getElementById("studio-voice-select").value = rec.voice_profile_id;
        document.getElementById("studio-language-select").value = rec.language;
        document.getElementById("studio-text-input").value = rec.text;
        updateStudioTextStyles();
      }
      return;
    }

    const saveTranscriptBtn = ev.target.closest("[data-save-transcript]");
    if (saveTranscriptBtn) {
      const vid = saveTranscriptBtn.dataset.saveTranscript;
      const input = document.getElementById(`transcript-${vid}`);
      try {
        await apiJson(`/api/v1/voices/${encodeURIComponent(vid)}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reference_transcript: (input?.value || "").trim() }),
        });
        showToast("Reference transcript saved locally.");
        await loadAllData();
      } catch (err) {
        showToast(err.message);
      }
      return;
    }

    const reprepareBtn = ev.target.closest("[data-reprepare-voice]");
    if (reprepareBtn) {
      const vid = reprepareBtn.dataset.reprepareVoice;
      const input = document.getElementById(`transcript-${vid}`);
      try {
        await apiJson(`/api/v1/voices/${encodeURIComponent(vid)}/prepare`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            target_duration_seconds: 8.0,
            reference_transcript: (input?.value || "").trim(),
          }),
        });
        showToast("Reference clip re-extracted from untouched source WAV.");
        await loadAllData();
      } catch (err) {
        showToast(err.message);
      }
      return;
    }

    const renameBtn = ev.target.closest("[data-rename-voice]");
    if (renameBtn) {
      const vid = renameBtn.dataset.renameVoice;
      const v = state.voices.find((item) => item.id === vid);
      const nextName = window.prompt("New voice profile name:", v?.display_name || "");
      if (nextName && nextName.trim()) {
        try {
          await apiJson(`/api/v1/voices/${encodeURIComponent(vid)}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ display_name: nextName.trim() }),
          });
          showToast("Voice profile renamed.");
          await loadAllData();
        } catch (err) {
          showToast(err.message);
        }
      }
      return;
    }

    const deleteVoiceBtn = ev.target.closest("[data-delete-voice]");
    if (deleteVoiceBtn) {
      const vid = deleteVoiceBtn.dataset.deleteVoice;
      if (!window.confirm("Delete this local voice profile, its recordings, and generated outputs?")) {
        return;
      }
      try {
        await apiJson(`/api/v1/voices/${encodeURIComponent(vid)}`, { method: "DELETE" });
        showToast("Voice profile deleted from local storage.");
        await loadAllData();
      } catch (err) {
        showToast(err.message);
      }
      return;
    }

    const deleteGenBtn = ev.target.closest("[data-delete-gen]");
    if (deleteGenBtn) {
      const gid = deleteGenBtn.dataset.deleteGen;
      if (!window.confirm("Delete this generated audio clip from local disk?")) return;
      try {
        await apiJson(`/api/v1/generations/${encodeURIComponent(gid)}`, { method: "DELETE" });
        if (state.activePreviewId === gid) state.activePreviewId = null;
        showToast("Generation deleted.");
        await loadAllData();
      } catch (err) {
        showToast(err.message);
      }
      return;
    }

    const sampleBtn = ev.target.closest("[data-sample]");
    if (sampleBtn) {
      const lang = sampleBtn.dataset.sample;
      document.getElementById("studio-language-select").value = lang;
      document.getElementById("studio-text-input").value = SAMPLES[lang] || "";
      updateStudioTextStyles();
      analyzeStudioText();
    }
  });

  document.getElementById("btn-refresh-all").addEventListener("click", async () => {
    await loadAllData();
    showToast("Local status refreshed.");
  });

  document.getElementById("btn-verify-models").addEventListener("click", async () => {
    const out = document.getElementById("settings-model-verify-result");
    try {
      const res = await apiJson("/api/v1/models/verify");
      out.hidden = false;
      const rows = Object.entries(res.models || {})
        .map(
          ([k, v]) => `
        <div class="compact-row">
          <div>
            <strong class="code-inline">${esc(k)}</strong>
            <div class="meta-text">${
              v.complete
                ? `Cached files verified (${v.present_files.length})`
                : `Missing: ${esc((v.missing_files || []).join(", "))}`
            }</div>
          </div>
          <span class="badge ${v.complete ? "badge-ok" : "badge-warn"}">${v.complete ? "Cached" : "Incomplete"}</span>
        </div>`
        )
        .join("");
      out.innerHTML = `<div class="compact-list">${rows}</div>`;
    } catch (err) {
      out.hidden = false;
      out.innerHTML = `<div class="callout callout-error">${esc(err.message)}</div>`;
    }
  });

  document.getElementById("btn-cancel-job").addEventListener("click", async () => {
    if (!state.activeJobId) return;
    try {
      await apiJson(`/api/v1/jobs/${encodeURIComponent(state.activeJobId)}/cancel`, {
        method: "POST",
      });
      showToast("Cancellation requested.");
    } catch (err) {
      showToast(err.message);
    }
  });

  document.getElementById("voice-search-input").addEventListener("input", renderVoices);
  document.getElementById("history-voice-filter").addEventListener("change", renderHistory);
  document.getElementById("history-lang-filter").addEventListener("change", renderHistory);

  // Create Voice Profile form
  const refSlider = document.getElementById("ref-duration-slider");
  refSlider.addEventListener("input", () => {
    document.getElementById("ref-duration-output").textContent = `${Number(refSlider.value).toFixed(1)}s`;
  });

  const fileInput = document.getElementById("voice-file-input");
  const dropzone = document.getElementById("voice-dropzone");
  fileInput.addEventListener("change", () => {
    const f = fileInput.files?.[0];
    document.getElementById("dropzone-filename").textContent = f
      ? `Selected: ${f.name} (${(f.size / (1024 * 1024)).toFixed(2)} MB)`
      : "Choose your ~2-minute WAV file or drop it here";
  });
  ["dragenter", "dragover"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      if (evt === "drop" && e.dataTransfer?.files?.length) {
        fileInput.files = e.dataTransfer.files;
        fileInput.dispatchEvent(new Event("change"));
      }
    })
  );

  document.getElementById("create-voice-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const errEl = document.getElementById("create-voice-error");
    errEl.hidden = true;

    const form = e.currentTarget;
    const f = fileInput.files?.[0];
    if (!f) {
      errEl.textContent = "Please select a .wav recording first.";
      errEl.hidden = false;
      return;
    }

    const fd = new FormData();
    fd.append("file", f);
    fd.append("display_name", form.display_name.value.trim());
    fd.append("ownership_confirmed", form.ownership_confirmed.checked ? "true" : "false");
    fd.append("notes", form.notes.value.trim());
    fd.append("reference_transcript", form.reference_transcript.value.trim());
    fd.append("target_reference_seconds", form.target_reference_seconds.value);

    const submitBtn = document.getElementById("btn-submit-voice");
    submitBtn.disabled = true;
    submitBtn.textContent = "Inspecting & Preparing…";
    try {
      const res = await apiJson("/api/v1/voices/import", { method: "POST", body: fd });
      renderInspectionResult(res.voice);
      showToast(`Voice profile "${res.voice.display_name}" created.`);
      await loadAllData();
    } catch (err) {
      errEl.textContent = err.message;
      errEl.hidden = false;
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Import & Inspect Recording";
    }
  });

  // Studio controls
  const speedSlider = document.getElementById("studio-speed-slider");
  speedSlider.addEventListener("input", () => {
    document.getElementById("studio-speed-output").textContent = `${Number(speedSlider.value).toFixed(2)}x`;
  });

  const studioText = document.getElementById("studio-text-input");
  const studioLang = document.getElementById("studio-language-select");
  studioText.addEventListener("input", updateStudioTextStyles);
  studioLang.addEventListener("change", updateStudioTextStyles);
  document.getElementById("btn-analyze-text").addEventListener("click", analyzeStudioText);

  document.getElementById("studio-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const errEl = document.getElementById("studio-error");
    errEl.hidden = true;

    const voiceId = document.getElementById("studio-voice-select").value;
    const text = studioText.value.trim();
    if (!voiceId) {
      errEl.textContent = "Select or create a voice profile first.";
      errEl.hidden = false;
      return;
    }
    if (!text) {
      errEl.textContent = "Enter Urdu, English, or mixed text to synthesize.";
      errEl.hidden = false;
      return;
    }

    const genBtn = document.getElementById("btn-generate-speech");
    genBtn.disabled = true;
    genBtn.textContent = "Queued…";
    try {
      const res = await apiJson("/api/v1/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          voice_profile_id: voiceId,
          text,
          language: studioLang.value,
          speed: Number(speedSlider.value),
          expression: document.getElementById("studio-expression-select").value,
        }),
      });
      state.activeJobId = res.job.job_id;
      await pollJob(state.activeJobId);
      if (state.activeJobId) {
        state.jobPollTimer = setInterval(() => pollJob(state.activeJobId), 500);
      }
    } catch (err) {
      errEl.textContent = err.message;
      errEl.hidden = false;
      stopJobPolling();
    }
  });

  // Settings form
  document.getElementById("settings-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const errEl = document.getElementById("settings-error");
    errEl.hidden = true;
    try {
      await apiJson("/api/v1/settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          active_engine: document.getElementById("settings-engine-select").value,
          compute_device: document.getElementById("settings-device-select").value,
          default_language: document.getElementById("settings-lang-select").value,
          default_speed: Number(document.getElementById("settings-speed-input").value),
          default_export_format: document.getElementById("settings-export-select").value,
          prefer_offline_only: document.getElementById("settings-offline-checkbox").checked,
        }),
      });
      showToast("Settings saved locally.");
      await loadAllData();
    } catch (err) {
      errEl.textContent = err.message;
      errEl.hidden = false;
    }
  });
}

function updateStudioTextStyles() {
  const studioText = document.getElementById("studio-text-input");
  const lang = document.getElementById("studio-language-select").value;
  document.getElementById("studio-char-count").textContent = `${studioText.value.length} / 4000 chars`;
  studioText.classList.toggle("urdu-text", lang === "ur" || lang === "mixed");
  studioText.dir = lang === "ur" ? "rtl" : "auto";
}

async function analyzeStudioText() {
  const text = document.getElementById("studio-text-input").value.trim();
  const lang = document.getElementById("studio-language-select").value;
  const out = document.getElementById("studio-segments-preview");
  const hintsEl = document.getElementById("studio-pronunciation-hints");
  if (!text) {
    out.innerHTML = `<span class="meta-text">Enter text to inspect Urdu/English segmentation.</span>`;
    if (hintsEl) hintsEl.innerHTML = "";
    return;
  }
  try {
    const res = await apiJson("/api/v1/text/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, language: lang }),
    });
    out.innerHTML = (res.segments || [])
      .map(
        (seg) => `
      <div class="segment-pill">
        <span class="badge ${seg.language === "ur" ? "badge-ok" : "badge-neutral"}">${seg.language.toUpperCase()}</span>
        <span dir="${seg.language === "ur" ? "rtl" : "ltr"}">${esc(seg.text)}</span>
      </div>`
      )
      .join("");
    if (hintsEl) {
      hintsEl.innerHTML = (res.pronunciation_hints || [])
        .map((h) => `<div class="callout callout-warn" style="margin-bottom:0;">${esc(h)}</div>`)
        .join("");
    }
  } catch (err) {
    out.innerHTML = `<div class="callout callout-error">${esc(err.message)}</div>`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  updateStudioTextStyles();
  loadAllData();
});
