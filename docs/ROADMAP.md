# Delivery Roadmap

Dates are intentionally not assigned until hardware and model feasibility are known.

## Phase 0: Foundation and discovery
**Status: Completed (`docs/discovery_report.md`).**

Deliverables: product requirements, architecture, UX direction, privacy rules, model evaluation framework, lightweight API scaffold, container hardware probe, primary-source candidate report.

## Phase 1: Technical proof of concept
**Status: Tooling & evaluation harness completed; live audio listening & laptop RTF/VRAM measurements pending target Linux Mint laptop.**

- [x] Commercial-license verification separating permissive defaults (`Indic Parler-TTS` Apache-2.0 + `OpenVoice v2` MIT; optional `Kokoro-82M`/`MeloTTS`; secondary `F5-TTS-OpenBible-Urdu` CC-BY-SA-4.0) from excluded non-commercial checkpoints (Meta MMS, Coqui XTTS-v2, Fish 1.5).
- [x] Cross-platform hardware discovery script (`scripts/hardware_probe.py`) with Android/PRoot safety guard.
- [x] Repeatable 5-prompt PoC evaluation harness (`scripts/poc_eval.py`) and isolated Linux Mint setup script (`scripts/setup_poc_env.sh`).
- [ ] Run isolated PoC on target Linux Mint laptop with user's ~2-minute WAV and record listening scores, RAM/VRAM, and RTF.

## Phase 2: Core application (Backend)
**Status: Completed (`app/core`, `app/audio`, `app/text`, `app/engine`, `app/diagnostics`, `app/api/routes`).**

- [x] Application configuration (`.env` support, loopback defaults, isolated local storage outside Git).
- [x] Local SQLite voice library, generation history, and settings persistence.
- [x] Pure-Python WAV audio inspection (duration, sample rate, channels, bit depth, peak/RMS dBFS, clipping, silence ratio) and automatic clean 6–10s reference segment extraction preserving original audio.
- [x] Deterministic Urdu, English, and mixed Urdu-English script segmentation and WAV cross-fade stitching.
- [x] Provider-neutral `SpeechEngine` protocol, `EngineRegistry`, and truthful capability/diagnostic endpoints.
- [x] WAV preview/download and runtime-detected `ffmpeg` MP3 export.

## Phase 3: Frontend, UX, and product quality
**Status: Completed (`frontend/index.html`, `frontend/assets/styles.css`, `frontend/assets/app.js`).**

- [x] Original light-theme desktop audio workspace (zero external CDN/font dependencies, served directly by FastAPI on `127.0.0.1:8765`).
- [x] All 7 screens implemented: Dashboard, Voice Library, Create Voice Profile, Text to Speech Studio, Audio Preview (with side-by-side comparison), Generation History, Settings & Diagnostics.
- [x] WCAG 2.2 visible label/name alignment, keyboard navigation, `:focus-visible`, RTL Urdu script input, and truthful missing-engine states.
- [x] Conditional MP3 export UI alongside lossless WAV download.

## Phase 4: Speech engine integration
**Status: Adapters implemented and contract-tested; live audio listening & hardware benchmarks pending Linux Mint laptop.**

- [x] Default commercially permissive engine adapter: `indic_parler_openvoice` (`ai4bharat/indic-parler-tts` Apache-2.0 + `myshell-ai/OpenVoiceV2` MIT) supporting Urdu, English, and deterministic mixed Urdu-English synthesis with CPU fallback and CUDA auto-detection.
- [x] Secondary direct zero-shot Urdu adapter: `f5_tts_urdu` (`SWivid/F5-TTS` MIT + `multilingual-tts/F5-TTS-OpenBible-Urdu` CC-BY-SA-4.0), truthfully constrained to Urdu-only with explicit offline transcript guard.
- [x] Non-commercial weights (`Meta MMS Urdu`, `Coqui XTTS-v2`, `Fish Speech 1.5`) excluded from distributable defaults.
- [ ] Execute live audio generation and 1–5 human listening review on the Linux Mint laptop.

## Phase 5: Local Linux Mint packaging and handover
**Status: Completed (`scripts/install_linux_mint.sh`, `scripts/download_models.py`, `scripts/start_voicecity.sh`, `scripts/stop_voicecity.sh`, `scripts/voicecity.desktop.template`, `docs/LINUX_MINT_GUIDE.md`).**

- [x] Turnkey Linux Mint installation script with CPU/CUDA selection and PRoot phone guard.
- [x] Consent-driven local model weight downloader displaying code + weight licenses and checking free disk space.
- [x] Loopback-only (`127.0.0.1:8765`) start/stop scripts and `.desktop` launcher template.
- [x] Non-technical user guide covering installation, model setup, WAV import, profile creation, speech generation, backup/restore, and troubleshooting.
- [x] Updated README, open decisions, and architecture docs.

## Phase 6: Quality assurance
**Status: Pending final QA pass.**

## Deferred
Video dubbing, transcription, live conversion, cloud sync, multi-user access, mobile app, and automated content production are outside the first release.
