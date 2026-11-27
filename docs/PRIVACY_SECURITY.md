# Privacy and Security Requirements

## Data classification
Voice recordings and generated speech are personal data. Treat them as sensitive user content.

## Defaults
- Local processing only unless the user explicitly enables a remote provider.
- Remote inference disabled by default.
- Bind the API to 127.0.0.1 by default.
- Store recordings, profiles, and generated audio in a configurable local data directory.
- Keep runtime data outside the source repository.
- Never commit recordings, generated audio, voice embeddings, model weights, API keys, tokens, or credentials.
- Avoid logging user text or audio.
- Provide deletion for profiles and related files.
- Explain data retention before model preparation.

## Consent and misuse boundaries
The application is intended for the user's own voice or a voice they are explicitly authorized to use. Do not build features intended to impersonate another person without consent, bypass identity checks, or facilitate fraud. Consider an ownership and authorization confirmation during profile creation.

## Network behavior
Any future remote provider must be opt-in and clearly labelled. Disclose what audio or text leaves the device, which provider receives it, and whether it retains the data.

## Repository hygiene
The .gitignore excludes common audio formats, model weights, local data directories, environment files, and logs. Review it whenever a new storage location or format is introduced.

## Release security review
- Validate uploaded file type and actual contents.
- Limit file size and duration.
- Sanitize filenames and prevent path traversal.
- Avoid shell execution with user-controlled strings.
- Restrict generated paths to the configured data directory.
- Validate request sizes.
- Add browser origin protections as required.
- Document dependency sources and update procedures.
