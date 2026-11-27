# VoiceCity Acceptance Checklist

## Repository & Licensing Hygiene
- [x] README, Architecture, Model Evaluation Matrix, Model Licensing Register, Linux Mint Guide, Discovery Report, and Roadmap are synchronized and free of misleading engine claims.
- [x] Four capability classes (`standard_tts`, `reference_voice_cloning`, `voice_conversion`, `cross_linguistic_voice_conversion`) are strictly separated in code, API, UI, and docs.
- [x] `Indic Parler-TTS` is truthfully labelled Standard TTS ONLY (not voice cloning); `OpenVoice v2` truthfully discloses Urdu is not native; `experimental_parler_openvoice` is explicitly marked experimental.
- [x] ShareAlike (`F5-TTS-OpenBible-Urdu` CC-BY-SA-4.0) is kept optional and clearly identified; non-commercial checkpoints (`OmniVoice`, `MMS`, `XTTS-v2`, `Fish 1.5`) are excluded from distributable defaults.
- [x] No user recordings, embeddings, SQLite DBs, secrets, or model weights are tracked in Git.

## Verified Application Functionality (Automated QA)
- [x] Application starts cleanly on `127.0.0.1` and serves all 7 desktop web UI screens.
- [x] Pure-Python 8/16/24/32-bit WAV validation, acoustic inspection, and automatic clean reference slicing preserving original WAV untouched.
- [x] Invalid audio (empty, corrupt, non-WAV, silent, oversized, missing consent, path traversal) safely rejected.
- [x] Voice profile CRUD, inline reference transcript editing, re-preparation, and complete disk cleanup on deletion.
- [x] Urdu/English normalization (Kaf/Yeh, digits, ZWNJ, `?`→`؟`), mixed-language segmentation, and pronunciation hints.
- [x] Background generation job queue with live progress reporting, cooperative cancellation, and error recovery.
- [x] Dedicated audio-to-audio Voice Conversion API (`POST /api/v1/conversions`) and offline local model verifier (`GET /api/v1/models/verify`).
- [x] Automated `pytest` suite passes with hardware-dependent live neural tests explicitly marked `SKIPPED` (`PENDING_LAPTOP_HARDWARE`).

## Pending Linux Mint Laptop Verification (Cannot Run on Pixel 7 Pro Phone)
- [ ] Run `python3 scripts/hardware_probe.py` on Linux Mint to capture exact CPU, RAM, GPU, VRAM, and disk.
- [ ] Install Python 3.11/3.12 ML runtimes and download weights (`f5_tts_urdu` + `qwen3_tts_en`, and optionally `indic_parler_tts` + `openvoice_v2_converter`).
- [ ] Verify actual model loading (`model_integration_verified`) on Linux Mint hardware.
- [ ] Generate actual Pakistani Urdu, English, and mixed speech from your existing ~2-minute WAV (`actual_speech_generated`).
- [ ] Complete 1–5 human listening evaluation (`human_listening_completed`) comparing F5-TTS Urdu, Qwen3-TTS English, Dual Cloning Router, and Experimental Parler→OpenVoice.
- [ ] Verify air-gapped offline inference (network disabled) and live `ffmpeg` MP3 export.
