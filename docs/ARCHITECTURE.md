# Architecture

## Principles
1. Local-first: recordings, profiles, and generated audio stay on device by default.
2. Model-neutral: application logic must not depend on one model API.
3. Explicit capability reporting: unsupported languages and unavailable models are visible.
4. Replaceable components: audio processing, storage, and speech engines have clear boundaries.
5. Minimal infrastructure: no cloud account, queue, or database server for the first local prototype.
6. Secure defaults: loopback binding, secrets outside Git, user data isolated from source code.

## Provisional technology direction
The scaffold uses Python and FastAPI for a local backend. The browser frontend framework is not locked until discovery confirms the best maintainable option. Heavy ML dependencies are deliberately excluded.

## Logical components
- Web UI: voice library, import, text editor, generation, preview, export, settings.
- API: validation and capability endpoints.
- Voice profile service: metadata and profile lifecycle.
- Audio service: file validation and metadata extraction.
- Speech engine interface: provider-neutral local inference contract.
- Model adapter: translates application requests to the selected runtime.
- Local storage: metadata, recordings, generated audio, model files.
- Diagnostics: readiness, resources, and structured errors.

## Proposed local data layout
```text
data/
  voice_profiles/<profile-id>/
    profile.json
    source_audio.wav
  generated/<profile-id>/<generation-id>.wav
  cache/
models/<provider-or-model-id>/
```
Runtime data must remain outside tracked source files.

## API direction
Implemented:
- GET /health
- GET /api/v1/capabilities

Future endpoints, subject to review:
- GET /api/v1/voices
- POST /api/v1/voices/import
- GET /api/v1/voices/{voice_id}
- DELETE /api/v1/voices/{voice_id}
- POST /api/v1/generations
- GET /api/v1/generations/{generation_id}
- GET /api/v1/generations/{generation_id}/audio

Do not implement fake endpoints that imply working features.

## Speech engine contract
The eventual adapter should expose health_check, supported_languages, prepare_voice, generate, and capability metadata. It must declare model ID, version, license, language evidence, hardware requirements, and network behavior.

## Storage
Filesystem audio storage is preferred. SQLite is a candidate for profile and generation metadata. Do not introduce PostgreSQL or Redis for a single-user local app without a demonstrated need.

## Deployment
Initial target is a Linux desktop, local Python environment, local browser UI, service bound to 127.0.0.1, and configurable user data and model directories. Do not expose to LAN or public internet by default.

## Hardware gate
Record CPU, RAM, GPU, VRAM, Linux version, free disk, and acceleration support before choosing an inference runtime. Do not silently switch to a remote API if local inference is slow.
