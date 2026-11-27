# VoiceCity

**A local-first voice studio for personal voice cloning and speech generation in Urdu and English.**

VoiceCity is an original application project focused on helping a user create, manage, test, and use a personal voice profile for text-to-speech generation. The initial target is a private, locally run application on Linux.

## Project status

**Stage:** Foundation and discovery  
**Implementation status:** Initial scaffold only  
**Model selection:** Pending evidence-based evaluation  
**Primary languages:** Urdu and English, including mixed Urdu-English text  
**Initial deployment target:** Local Linux desktop, accessed through a browser  
**Cost principle:** Prefer free, locally runnable components. No paid API is assumed.

This repository contains the product definition, technical plan, application scaffold, and implementation handoff. It does not contain model weights, user voice recordings, generated audio, or credentials.

## Product direction

- Import a user's own voice recording.
- Create and manage a local voice profile.
- Generate speech from Urdu, English, and mixed Urdu-English text.
- Preview generated audio before export.
- Export generated audio in supported formats.
- Keep voice recordings, profiles, and generated audio on the user's device by default.
- Keep the speech engine replaceable through a model adapter interface.

## Important constraints

- Do not train a foundation voice model from scratch as part of the initial project.
- Do not select a model until language quality, reference-audio requirements, hardware needs, license terms, and commercial-use permissions have been checked.
- Do not assume that a model supporting Hindi or multilingual speech necessarily produces natural Pakistani Urdu.
- Do not upload voice recordings to external services without a separate, explicit user decision.
- Do not commit model weights, recordings, generated audio, secrets, or local runtime data to Git.

## Repository map

- `app/`: application source scaffold
- `docs/`: product, architecture, UX, privacy, evaluation, and delivery documentation
- `tests/`: initial automated test scaffold
- `scripts/`: development and maintenance helpers
- `pyproject.toml`: Python project configuration
- `.env.example`: documented environment variable template
- `.gitignore`: local data and secret exclusions

## Getting started

The scaffold is intentionally lightweight. Model runtimes and large dependencies are not installed by the foundation setup.

See:
1. [Development setup](docs/DEVELOPMENT.md)
2. [Product requirements](docs/PRODUCT_REQUIREMENTS.md)
3. [Architecture](docs/ARCHITECTURE.md)
4. [Model evaluation plan](docs/MODEL_EVALUATION.md)
5. [Antigravity handoff](docs/ANTIGRAVITY_HANDOFF.md)

## Current limitations

The current scaffold is not yet a functioning voice cloning product. It does not load a speech model, clone a voice, or generate audio. Those capabilities must be implemented only after the model and hardware evaluation is approved.

## License

Project license has not yet been selected. See [open decisions](docs/OPEN_DECISIONS.md).
