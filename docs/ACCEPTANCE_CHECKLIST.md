# VoiceCity Acceptance Checklist

## Repository & Hygiene
- [x] README explains scope, implemented features, licensing, and pending hardware tests.
- [x] Product, architecture, UX, privacy, model evaluation, Linux Mint guide, discovery report, and roadmap docs exist.
- [x] Open decisions are recorded (`docs/OPEN_DECISIONS.md`).
- [x] Antigravity handoff is complete (`docs/ANTIGRAVITY_HANDOFF.md`).
- [x] No user audio, embeddings, SQLite DBs, or model weights are tracked in Git.
- [x] No credentials or real environment values are committed.

## Application Backend, Audio Pipeline & Web UI
- [x] Python package imports and starts cleanly on `127.0.0.1`.
- [x] `/health` and `/api/v1/capabilities` return truthful live readiness status.
- [x] `/api/v1/capabilities` never claims speech generation is ready when local model weights are missing.
- [x] WAV validation inspects RIFF/WAVE header, duration, sample rate, channels, bit depth, peak/RMS dBFS, clipping, and silence ratio.
- [x] Automatic reference preparation extracts a clean 6–10s 24 kHz mono clip while preserving the original WAV untouched.
- [x] Invalid audio (empty, corrupt, non-WAV, silent, oversized, missing consent, path traversal) is safely rejected.
- [x] Urdu, English, and mixed Urdu-English text normalization and segmentation verified.
- [x] Voice profile CRUD, generation history, preview playback, WAV export, and SQLite persistence across restarts verified.
- [x] Original 7-screen desktop web UI (`Dashboard`, `Voice Library`, `Create Voice Profile`, `Text to Speech Studio`, `Audio Preview`, `Generation History`, `Settings`) served locally with WCAG 2.2 accessibility markers and RTL Urdu input.
- [x] Commercially permissive default engine adapter (`indic_parler_openvoice`: Apache-2.0 + MIT) and secondary Urdu adapter (`f5_tts_urdu`: MIT + CC-BY-SA-4.0) integrated; non-commercial models excluded from distributable defaults.
- [x] Turnkey Linux Mint installation, model download, and start/stop scripts created and syntax-verified.
- [x] Automated `pytest` suite passes with hardware-dependent live neural tests explicitly marked `SKIPPED` (`PENDING_LAPTOP_HARDWARE`).

## Pending Linux Mint Laptop Verification (Cannot Be Performed on Pixel 7 Pro Phone)
- [ ] Record target Linux Mint laptop hardware specs (`python3 scripts/hardware_probe.py`).
- [ ] Install engine dependencies and download local model weights on Linux Mint.
- [ ] Test existing ~2-minute WAV recording end-to-end with live neural inference.
- [ ] Complete 1–5 Pakistani Urdu, English, and mixed-language listening review (`scripts/poc_eval.py`).
- [ ] Measure real TTFA, RTF, peak RAM, and peak VRAM on Linux Mint.
- [ ] Verify air-gapped offline inference with network disabled after model caching.
- [ ] Verify MP3 export on Linux Mint after `sudo apt install ffmpeg`.
