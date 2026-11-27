# Product Requirements

## Product summary
VoiceCity is an original, local-first personal voice studio. It allows a user to prepare a voice profile from their own recording and generate speech from written text in Urdu, English, and mixed Urdu-English.

The product may integrate third-party speech models through adapters. It must not copy another product's complete application or assume that an open-source label grants unrestricted use.

## Initial user and workflow
The initial user is one adult operating the application on their own Linux computer.

1. Open VoiceCity in a local browser.
2. Import an existing voice recording.
3. Review audio metadata and quality checks.
4. Create a named local voice profile.
5. Enter Urdu, English, or mixed-language text.
6. Generate a preview using the selected profile.
7. Listen, regenerate if needed, and export.

The existing approximately two-minute WAV sample is the first evaluation asset. Do not require a longer recording before testing a candidate model.

## Goals
- Understandable voice profile creation for a non-ML user.
- Natural Pakistani Urdu pronunciation as a core requirement.
- English and mixed Urdu-English text support.
- Local storage and inference by default.
- Replaceable model integration.
- Clear model readiness, progress, failures, and limitations.
- Manageable setup on the available Linux hardware.

## Non-goals for the first release
- Training a foundation model from scratch.
- Public multi-user hosting or SaaS.
- Real-time voice conversion or live calls.
- Video dubbing, lip sync, transcription, or audiobook production.
- Public voice marketplace.
- Cloud accounts, subscriptions, or paid API dependencies.
- Automatic publication of generated content.

## Functional requirements
- Voice library: list, create, rename, inspect, and delete local profiles.
- Audio import: WAV first; other formats after reliable validation.
- Audio inspection: duration, sample rate, channels, peak level, clipping warnings, and format status.
- Voice preparation: model-specific validation and clear requirements.
- Text input: explicit language selection; mixed mode only after model validation.
- Speech generation: available only when a compatible model is installed.
- Preview: playback and comparison between attempts.
- Export: WAV first; MP3 may follow after encoder review.
- Settings: model status, storage paths, compute device, audio settings, privacy controls.
- Errors: actionable guidance for invalid audio, unsupported language, missing model, memory limits, and generation failures.

## Quality requirements
- Evaluate Urdu with native or fluent Pakistani Urdu listeners.
- Test Urdu script, borrowed English words, names, numerals, punctuation, and code-switching.
- Language-list claims are not proof of natural pronunciation.
- Measure generation time, peak memory, startup time, and output duration.
- Bind local services to loopback by default.
- Do not log raw text, audio, or personal voice data by default.

## First usable release acceptance
- Import the existing WAV without remote upload.
- Display understandable audio validation.
- Create a profile using supported reference audio.
- Pass Urdu, English, and mixed-language listening review before labelling each supported.
- Preview and export generated audio locally.
- Retain local profiles and outputs after restart.
- Keep personal data, weights, and secrets out of Git.
- Provide setup, backup, and recovery instructions.

## Evidence required before voice engine implementation
For each candidate record official source, code and weight licenses separately, commercial rights, Urdu evidence, reference duration and format, inference method, hardware requirements, model size, offline behavior, network calls, known limitations, and maintenance status.
