# VoiceCity

**An original, local-first personal voice studio for Urdu, English, and mixed Urdu-English voice cloning and speech generation.**

VoiceCity helps you import your own WAV recording once, inspect its acoustic health, automatically prepare a clean reference clip, and generate Urdu, English, and mixed Urdu-English speech completely on your own Linux computer via a local browser workspace (`http://127.0.0.1:8765`).

## Project status

- **Application Core (Backend + Desktop Web UI + Audio Pipeline):** Implemented and tested
- **Speech Engine Adapters:** Implemented (`indic_parler_openvoice` commercial default; `f5_tts_urdu` secondary Urdu-only adapter)
- **Live Model Listening & Laptop Hardware Benchmarks:** **Pending execution on the target Linux Mint laptop** (heavyweight model checkpoints were intentionally NOT downloaded onto the Pixel 7 Pro PRoot dev environment)
- **Primary languages:** Urdu (`ur`), English (`en`), and mixed Urdu-English (`mixed`)
- **Initial deployment target:** Linux Mint desktop, accessed locally at `http://127.0.0.1:8765`
- **Cost & Privacy principle:** Free, local-first, zero paid APIs, zero cloud voice upload by default

## Selected Speech Engines & Licensing

| Engine ID | Components | Code License | Weight License | Languages | Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `indic_parler_openvoice` | `ai4bharat/indic-parler-tts` + `myshell-ai/OpenVoiceV2` | Apache-2.0 + MIT | **Apache-2.0 + MIT** | Urdu, English, Mixed | **Distributable Commercial Default** |
| `f5_tts_urdu` | `SWivid/F5-TTS` + `multilingual-tts/F5-TTS-OpenBible-Urdu` | MIT | **CC-BY-SA-4.0** | Urdu only | Secondary direct zero-shot Urdu option |

*Non-commercial models (`Meta MMS Urdu` CC-BY-NC-4.0, `Coqui XTTS-v2` CPML, `Fish Speech 1.5` CC-BY-NC-SA-4.0) are explicitly excluded from the distributable default configuration. See [docs/MODEL_EVALUATION.md](docs/MODEL_EVALUATION.md) and [docs/discovery_report.md](docs/discovery_report.md).*

## What Is Implemented

- **7-Screen Desktop Web UI (`frontend/`):** Dashboard, Voice Library, Create Voice Profile, Text to Speech Studio (with RTL Urdu support & live mixed-script segment inspector), Audio Preview (with side-by-side comparison), Generation History, and Settings & Diagnostics.
- **Pure-Python WAV Validation & Reference Preparation (`app/audio/service.py`):** Validates RIFF/WAVE PCM headers, inspects duration, sample rate, channels, bit depth, peak/RMS dBFS, clipping, and silence ratio, preserves the original ~2-minute WAV untouched, and automatically extracts a normalized 24 kHz mono 6–10s reference clip.
- **Local-First Storage (`app/core/storage.py`, `app/core/database.py`):** SQLite persistence + confined filesystem directories (`data/`, `models/`) kept strictly outside Git.
- **WAV & Optional MP3 Export:** Lossless WAV download built in; MP3 export activates automatically when `ffmpeg` is installed.
- **Hardware Discovery & Linux Mint Tooling (`scripts/`):** `hardware_probe.py`, `poc_eval.py`, `install_linux_mint.sh`, `download_models.py`, `start_voicecity.sh`, `stop_voicecity.sh`.

## Quick Start on Linux Mint

See the complete non-technical guide in [docs/LINUX_MINT_GUIDE.md](docs/LINUX_MINT_GUIDE.md).

```bash
git clone https://github.com/zakshub/voicecity.git
cd voicecity
bash scripts/install_linux_mint.sh --with-engine indic_parler_openvoice --device auto
.venv/bin/python scripts/download_models.py --engine indic_parler_openvoice
bash scripts/start_voicecity.sh
```

Then open **http://127.0.0.1:8765** in your browser.

## Repository map

- `app/`: FastAPI backend, audio pipeline, SQLite repository, Urdu/English text segmenter, speech engine adapters, diagnostics
- `frontend/`: Zero-build desktop web studio UI served locally by FastAPI
- `scripts/`: Hardware probe, PoC evaluation harness, Linux Mint installer, consent-driven model downloader, start/stop launchers
- `docs/`: Product requirements, architecture, discovery report, model evaluation, Linux Mint guide, roadmap, privacy & security
- `tests/`: Automated pytest suite (explicitly marking laptop-hardware neural listening tests as skipped/pending)
- `pyproject.toml`: Python package configuration
- `.env.example`: Environment variable template
- `.gitignore`: Strict exclusions for audio recordings, embeddings, weights, SQLite DBs, and secrets

## License

Project license decision remains recorded in [docs/OPEN_DECISIONS.md](docs/OPEN_DECISIONS.md); all default dependencies and default speech model weights have been chosen for commercial compatibility (Apache-2.0 / MIT).
