# VoiceCity

**An original, local-first personal voice studio for Urdu, English, and mixed Urdu-English voice cloning and speech generation.**

VoiceCity lets you import your own WAV recording once, inspect its acoustic quality, prepare a clean reference clip automatically, manage reference transcripts, and generate speech completely locally through your browser (`http://127.0.0.1:8765`).

## Honest Project Status (5-Axis Verification)

| Verification Axis | Status |
| :--- | :--- |
| **Automated Tests Passed** | **Yes** (`22 passed, 3 skipped` in `pytest` + live `127.0.0.1` HTTP smoke test) |
| **Model Integration Verified (Real Load)** | **Pending Linux Mint laptop** (heavyweight ML checkpoints are intentionally not downloaded on the Pixel 7 Pro dev container) |
| **Actual Neural Speech Generated** | **No** (pending Linux Mint) |
| **Human Listening Evaluation Completed** | **No** (pending Pakistani Urdu + English listening review on Linux Mint) |
| **Commercial Licensing Verified** | **Yes** — see [docs/MODEL_LICENSING_REGISTER.md](docs/MODEL_LICENSING_REGISTER.md) |

## Strictly Separated Speech Engine Capabilities

VoiceCity never disguises Standard TTS or experimental conversion as verified native voice cloning:

| Engine ID | Capability Class | Maturity | Supported Languages | Code / Weight Licenses | Commercial Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `f5_tts_urdu` | **Reference-Audio Voice Cloning** | Technically Integrated | **Urdu (`ur`) ONLY** | MIT / **CC-BY-SA-4.0** (Vocos MIT) | Optional ShareAlike (Attribution + ShareAlike on modified weights) |
| `qwen3_tts_en` | **Reference-Audio Voice Cloning** | Technically Integrated | **English (`en`) ONLY** | **Apache-2.0 / Apache-2.0** | **Permissive Commercial** |
| `dual_cloning_router` | **Reference-Audio Voice Cloning** (Compositional) | Technically Integrated | **Urdu (`f5_tts_urdu`) + English (`qwen3_tts_en`)**; Mixed = experimental stitching | MIT + Apache-2.0 / CC-BY-SA-4.0 + Apache-2.0 | Mixed (honestly exposes single-language cloning if only one is installed) |
| `indic_parler_tts` | **Standard TTS ONLY (NOT Cloning)** | Technically Integrated | Urdu (`ur`), English (`en`) | **Apache-2.0 / Apache-2.0** | Permissive Commercial (ignores user WAV; synthetic voice only) |
| `openvoice_v2_converter` | **Voice Conversion ONLY** (Audio-to-Audio) | Technically Integrated | Native: EN/ES/FR/ZH/JA/KO (**Urdu NOT native**) | **MIT / MIT** | Permissive Commercial (audio-to-audio converter only) |
| `experimental_parler_openvoice` | **Cross-Linguistic Conversion** | **Experimental** | Native: EN; **Experimental: Urdu & Mixed** | **Apache-2.0 + MIT / Apache-2.0 + MIT** | Permissive licenses, **NOT verified native Urdu voice cloning** |

*Non-commercial checkpoints (`k2-fsa/OmniVoice` CC-BY-NC, `Meta MMS Urdu` CC-BY-NC-4.0, `Coqui XTTS-v2` CPML, `Fish Speech 1.5` CC-BY-NC-SA-4.0) and strong copyleft (`Seed-VC` GPL-3.0) are documented in [docs/MODEL_EVALUATION.md](docs/MODEL_EVALUATION.md) and excluded from distributable defaults.*

## Quick Start on Linux Mint

See the step-by-step guide in [docs/LINUX_MINT_GUIDE.md](docs/LINUX_MINT_GUIDE.md).

```bash
git clone https://github.com/zakshub/voicecity.git
cd voicecity
python3 scripts/hardware_probe.py
bash scripts/install_linux_mint.sh --with-engine dual_cloning --device auto
.venv/bin/python scripts/download_models.py --engine dual_cloning
bash scripts/start_voicecity.sh
```

Then open **http://127.0.0.1:8765** in your browser.

## Repository Map

- `app/`: FastAPI local backend, pure-Python WAV inspection & slicing, SQLite store, async generation queue with cancellation, Urdu/English text normalizer & segmenter, separated engine adapters, hardware diagnostics
- `frontend/`: Zero-build 7-screen desktop web UI (`Dashboard`, `Voice Library`, `Create Voice Profile`, `Text to Speech Studio`, `Audio Preview`, `Generation History`, `Settings`)
- `scripts/`: `hardware_probe.py`, `poc_eval.py`, `install_linux_mint.sh`, `download_models.py`, `start_voicecity.sh`, `stop_voicecity.sh`, `voicecity.desktop.template`
- `docs/`: [MODEL_EVALUATION.md](docs/MODEL_EVALUATION.md), [MODEL_LICENSING_REGISTER.md](docs/MODEL_LICENSING_REGISTER.md), [LINUX_MINT_GUIDE.md](docs/LINUX_MINT_GUIDE.md), [ARCHITECTURE.md](docs/ARCHITECTURE.md), [ROADMAP.md](docs/ROADMAP.md), [ACCEPTANCE_CHECKLIST.md](docs/ACCEPTANCE_CHECKLIST.md), [discovery_report.md](docs/discovery_report.md)
- `tests/`: Automated pytest suite keeping hardware-dependent live speech & listening tests explicitly `SKIPPED` (`PENDING_LAPTOP_HARDWARE`)

---

## Project Operating System

This repository is governed by [zakshub/project-os](https://github.com/zakshub/project-os) (Private) and tracked on the [Zakshub Portfolio](https://github.com/users/zakshub/projects/2) board.  
For AI assistant rules, local verification commands, and delivery workflow, see [AGENTS.md](./AGENTS.md).
