# Open Decisions

| Decision | Current Position | Honest Status & Blockers |
| :--- | :--- | :--- |
| Urdu Reference Voice Cloning | `f5_tts_urdu` (`F5-TTS-OpenBible-Urdu`, **CC-BY-SA-4.0 optional ShareAlike**) | Technically integrated; **untested** on Pakistani Urdu speech; no permissive Apache-2.0/MIT Urdu zero-shot voice cloning checkpoint currently verified |
| English Reference Voice Cloning | `qwen3_tts_en` (`Qwen3-TTS-12Hz-0.6B-Base`, **Apache-2.0 permissive**) | Technically integrated; **untested** on target Linux Mint laptop |
| Mixed Urdu-English Cloning | `dual_cloning_router` (`f5_tts_urdu` + `qwen3_tts_en`) | Cross-model timbre consistency between F5-TTS and Qwen3-TTS is **empirically unverified** |
| Experimental Cross-Linguistic Conversion | `experimental_parler_openvoice` (`Indic Parler-TTS` Apache-2.0 → `OpenVoice v2` MIT) | Strictly marked **EXPERIMENTAL** because Indic Parler is Standard TTS and Urdu is NOT a documented native OpenVoice v2 language |
| Non-Commercial Models | `k2-fsa/OmniVoice` (CC-BY-NC), `Meta MMS Urdu` (CC-BY-NC-4.0), `Coqui XTTS-v2` (CPML), `Fish Speech 1.5` (CC-BY-NC-SA-4.0) | Excluded from distributable defaults; documented in `docs/MODEL_LICENSING_REGISTER.md` |
| Frontend Stack | Zero-build HTML5 + CSS + ES2022 served directly by FastAPI | Implemented; eliminates Node.js runtime requirement on Linux Mint |
| Metadata & Job Queue | Local SQLite (`data/voicecity.db`) + single-worker thread queue with cancellation | Implemented & verified in automated tests |
| Audio Formats | Pure-Python PCM WAV + runtime-detected `ffmpeg` MP3 | WAV verified; live `ffmpeg` MP3 encoding pending Linux Mint |
| Project License | Pending owner choice (compatible with MIT / Apache-2.0 core app) | Core app dependencies are 100% permissive; optional CC-BY-SA-4.0 Urdu weights kept external/user-downloaded |
| Target Hardware | Linux Mint laptop (exact CPU/RAM/GPU/VRAM unknown until probed) | Phone dev environment (`aarch64` PRoot Debian 13, Python 3.13 Android SOABI) cannot run or benchmark ML inference |
