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

## Phase 3: Product quality
- Generation history and comparison.
- Audio inspection and recovery.
- Settings and model management.
- MP3 export if justified.
- Accessibility and usability review.

## Phase 4: Packaging and handover
- Reproducible setup instructions.
- Local launch script or desktop shortcut.
- Backup and restore guidance.
- Dependency and license inventory.
- Release checklist and known limitations.

## Deferred
Video dubbing, transcription, live conversion, cloud sync, multi-user access, mobile app, and automated content production are outside the first release.
