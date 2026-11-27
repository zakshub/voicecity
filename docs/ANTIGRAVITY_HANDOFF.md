# Antigravity Handoff Brief

## Mission
Continue VoiceCity from this repository. Read the root README and every document in docs before making changes.

Repository: https://github.com/zakshub/voicecity

## Product
VoiceCity is an original, local-first personal voice studio for Urdu, English, and mixed Urdu-English speech generation using the user's own recording.

The initial user has an existing approximately two-minute WAV recording. Do not request a longer recording or another upload unless documented model requirements make it necessary.

## Mandatory rules
1. Treat this repository as the source of truth.
2. Do not replace the product direction with a clone of an existing application.
3. Do not assume multilingual claims prove natural Pakistani Urdu.
4. Verify official source, code license, weight license, commercial permissions, reference-audio requirements, hardware requirements, offline behavior, and Urdu evidence before model selection.
5. Do not use paid APIs by default.
6. Do not upload the user's recording to a remote service.
7. Never commit recordings, generated audio, voice embeddings, model weights, credentials, environment files, or personal data.
8. Do not train a foundation model from scratch.
9. Do not install large ML dependencies or download model weights during discovery.
10. Never claim unimplemented functionality works.
11. Keep local services bound to 127.0.0.1 unless explicitly approved otherwise.
12. Work in small milestones. After each milestone report changed files, tests, risks, and the next acceptance check.

## First assignment: discovery and audit
Do not start feature implementation yet.

### A. Repository audit
Inspect the structure and scaffold. Identify missing items, inconsistencies, Python configuration, and data exclusions.

### B. Hardware discovery
The intended inference machine is the Linux laptop, not the Pixel phone. Obtain actual CPU, RAM, GPU, VRAM, OS, and free disk details. Do not guess.

### C. Model research
Find at least three plausible candidates if credible options exist. Use official repositories, model cards, and license files as primary evidence. For each, report code and weight licenses separately, commercial restrictions, Urdu evidence and samples, English and code-switching, reference duration and formats, CPU/RAM/GPU/VRAM/disk, offline behavior, external network calls, maintenance, and limitations.

If fewer than three credible candidates exist, explain why rather than padding the list.

### D. Recommendation
Recommend one: proceed with a local proof of concept, run a limited experiment first, or no-go under current hardware/licensing constraints. State why and identify the cheapest next experiment.

### E. Report format
1. Repository audit
2. Hardware information needed
3. Candidate comparison table with source links
4. Urdu quality evidence and unknowns
5. License assessment
6. Recommended architecture adjustments
7. Phase 1 proof-of-concept plan
8. Risks and open decisions
9. Essential user input only

Stop after the discovery report and wait for explicit approval. Do not create model adapters, install ML frameworks, download model weights, or build the voice generation workflow until approval.
