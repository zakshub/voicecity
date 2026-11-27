# Open Decisions

| Decision | Current position | Evidence / Status |
| :--- | :--- | :--- |
| Default speech engine | `indic_parler_openvoice` (`ai4bharat/indic-parler-tts` Apache-2.0 + `myshell-ai/OpenVoiceV2` MIT) | Commercially permissive; **live Pakistani Urdu listening & laptop RTF/VRAM still pending on Linux Mint** |
| Secondary Urdu engine | `f5_tts_urdu` (`SWivid/F5-TTS` MIT + `F5-TTS-OpenBible-Urdu` CC-BY-SA-4.0) | Urdu-only direct zero-shot adapter; **live listening & CPU speed still pending on Linux Mint** |
| Non-commercial models | Meta MMS Urdu (CC-BY-NC-4.0), Coqui XTTS-v2 (CPML), Fish Speech 1.5 (CC-BY-NC-SA-4.0) | Explicitly excluded from distributable defaults |
| Frontend stack | Zero-build semantic HTML5 + CSS + ES2022 served by FastAPI (`frontend/`) | Chosen to eliminate Node.js runtime dependency on Linux Mint and keep 100% offline operation |
| Metadata storage | Local SQLite (`data/voicecity.db`) + per-profile JSON manifest (`profile.json`) | Implemented and verified across restarts |
| Audio formats | Uncompressed PCM WAV first (pure Python, zero external decoder required) | Implemented and verified |
| MP3 export | Runtime-detected `ffmpeg` (`libmp3lame`) optional export | Implemented; gracefully disabled when `ffmpeg` is absent |
| Commercial release | Preserved via Apache-2.0 / MIT default stack | Final repo license still pending user selection |
| Project license | Pending owner choice (MIT / Apache-2.0 compatible with default stack) | Awaiting Zak's selection |
| Packaging | Turnkey Linux Mint shell scripts + `.desktop` launcher (`scripts/`) | Implemented; AppImage/Flatpak deferred |
| GPU runtime | Auto-detects NVIDIA CUDA (`>=4 GB VRAM`) with CPU fallback | Pending actual Linux Mint laptop hardware probe |
| Remote inference | Disabled by default (`VOICECITY_ALLOW_REMOTE_INFERENCE=false`) | Enforced in config and API diagnostics |

## Known constraints
- Initial voice sample is approximately two minutes and available as WAV; VoiceCity automatically extracts a clean 6–10s reference clip without requiring another recording.
- Pixel 7 Pro Termux/PRoot environment is strictly for development and automated testing — never for heavyweight ML model downloads or inference.
- Live Pakistani Urdu, English, and mixed-language listening quality remain **untested** until executed on the Linux Mint laptop.
