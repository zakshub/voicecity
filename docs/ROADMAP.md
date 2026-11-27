# Delivery Roadmap

Dates are intentionally not assigned for hardware-dependent listening validation until run on the target Linux Mint laptop.

## Phase 0: Foundation and discovery — Completed (`7c53b49`)
- Product requirements, architecture, UX direction, privacy rules, primary-source discovery report (`docs/discovery_report.md`).

## Phase 1: Technical proof-of-concept tooling — Completed (`b308ce7`, refined in `848bc84`)
- Cross-platform hardware probe (`scripts/hardware_probe.py`) with Android/PRoot safety guard.
- Repeatable 5-prompt PoC harness (`scripts/poc_eval.py`) and isolated Linux Mint setup (`scripts/setup_poc_env.sh`).
- **Pending on Linux Mint:** Real laptop hardware readout, actual model loading, RTF/VRAM measurement, and 1–5 listening scores.

## Phase 2: Local-first backend & async queue — Completed (`a7d67a6`, upgraded in `848bc84`)
- Loopback FastAPI server, SQLite persistence, confined local file storage, pure-Python WAV validation & automatic reference slicing, Urdu/English text normalization & pronunciation hints, background generation queue with progress & cancellation, audio-to-audio voice conversion API, offline model cache verifier.

## Phase 3: Desktop-first web UI — Completed (`4230d20`, upgraded in `9b822ab`)
- Original 7-screen light-theme desktop audio workspace grounded in `docs/UX_DIRECTION.md` and WCAG 2.2 label/accessibility standards, featuring separated 4-class capability matrix, 5-axis verification display, inline reference transcript editor, and live queue progress + cancellation.

## Phase 4: Corrected separated speech engine architecture — Completed (`11c40ba`)
- Distinct, honestly classified adapters:
  - `f5_tts_urdu` (`reference_voice_cloning`, Urdu ONLY, CC-BY-SA-4.0 optional)
  - `qwen3_tts_en` (`reference_voice_cloning`, English ONLY, Apache-2.0 permissive)
  - `dual_cloning_router` (`reference_voice_cloning`, compositional Urdu + English + Mixed)
  - `indic_parler_tts` (`standard_tts` ONLY — NOT voice cloning, Apache-2.0)
  - `openvoice_v2_converter` (`voice_conversion` ONLY — Urdu NOT native, MIT)
  - `experimental_parler_openvoice` (`cross_linguistic_voice_conversion`, `experimental`)
- Complete 12-candidate honest evaluation matrix (`docs/MODEL_EVALUATION.md`) and authoritative licensing register (`docs/MODEL_LICENSING_REGISTER.md`).

## Phase 5: Local Linux Mint experience — Completed (`c1b53be`, updated in `848bc84`)
- Turnkey Linux Mint installer, consent-driven downloader with offline `--verify-only`, loopback start/stop launchers, `.desktop` menu template, and user guide (`docs/LINUX_MINT_GUIDE.md`).

## Phase 6: Automated QA & pending laptop validation — Automated QA Completed (`df0c403`, expanded through current HEAD)
- Automated backend, audio, queue, cancellation, capability-separation, and UI test suites passing (`22 passed, 3 skipped`).
- **Pending on Linux Mint:** Live neural speech generation, Pakistani Urdu + English listening review, air-gapped offline confirmation, and live `ffmpeg` MP3 export.
