# Architecture

## Principles
1. **Local-first:** Recordings, profiles, embeddings, and generated audio stay on device (`data/`, `models/`) outside Git.
2. **Model-neutral & capability-honest:** Application logic separates four distinct speech capabilities — `standard_tts`, `reference_voice_cloning`, `voice_conversion`, and `cross_linguistic_voice_conversion` — and never disguises synthetic TTS as voice cloning.
3. **Explicit maturity & 5-axis verification reporting:** Every adapter exposes `experimental` | `technically_integrated` | `empirically_verified` plus separate booleans for automated tests, real model loading, actual speech generated, human listening, and commercial licensing.
4. **Minimal infrastructure:** Single-process FastAPI + SQLite + single-worker local thread queue (`app/core/jobs.py`) — no cloud account, PostgreSQL, or Redis.
5. **Secure defaults:** Loopback `127.0.0.1` binding, strict path confinement (`ensure_within_dir`), remote inference disabled by default.

## Logical Components
- **Web UI (`frontend/`):** Zero-build semantic HTML5/CSS/ES2022 7-screen desktop workspace served directly by FastAPI.
- **API (`app/api/routes/`):**
  - System: `GET /health`, `GET /api/v1/capabilities`, `GET /api/v1/diagnostics`, `GET /api/v1/models/verify`, `GET|PATCH /api/v1/settings`
  - Voices: `GET /api/v1/voices`, `POST /api/v1/voices/import`, `GET|PATCH|DELETE /api/v1/voices/{id}`, `POST /api/v1/voices/{id}/prepare`, `GET /api/v1/voices/{id}/source-audio`, `GET /api/v1/voices/{id}/reference-audio`
  - Text & Generation: `POST /api/v1/text/analyze`, `POST /api/v1/jobs`, `GET /api/v1/jobs`, `GET /api/v1/jobs/{id}`, `POST /api/v1/jobs/{id}/cancel`, `GET|POST /api/v1/generations`, `GET|DELETE /api/v1/generations/{id}`, `GET /api/v1/generations/{id}/audio?format=wav|mp3&download=0|1`
  - Voice Conversion: `POST /api/v1/conversions` (explicitly separated audio-to-audio conversion via OpenVoice v2)
- **Audio Service (`app/audio/service.py`):** Pure-Python 8/16/24/32-bit PCM WAV validation, acoustic metrics, automatic best-segment extraction preserving original recordings, cross-fade segment stitching, and optional `ffmpeg` MP3 export.
- **Text Normalizer & Segmenter (`app/text/segmenter.py`):** Urdu character/digit/punctuation normalization preserving ZWNJ, mixed Urdu-English span splitting, and pronunciation hints.
- **Engine Registry (`app/engine/registry.py`):** Hosts 6 distinct lazy-loaded adapters (`f5_tts_urdu`, `qwen3_tts_en`, `dual_cloning_router`, `indic_parler_tts`, `openvoice_v2_converter`, `experimental_parler_openvoice`) + `unconfigured` fallback.

## Local Data Layout (Outside Git)
```text
data/
  voicecity.db
  voice_profiles/<profile-id>/
    profile.json
    source_audio.wav        # Untouched original recording
    reference_segment.wav   # Auto-extracted 24 kHz mono normalized clip
  generated/<profile-id>/<generation-id>.wav
  cache/
models/
  f5_tts_urdu/              # F5-TTS-OpenBible-Urdu (CC-BY-SA-4.0 optional)
  vocos/                    # Local Vocos vocoder (MIT)
  qwen3_tts_0.6b_base/      # Qwen3-TTS-12Hz-0.6B-Base (Apache-2.0)
  indic_parler_tts/         # Indic Parler-TTS (Apache-2.0, Standard TTS ONLY)
  openvoice_v2/converter/   # OpenVoice v2 converter (MIT, Voice Conversion ONLY)
```
