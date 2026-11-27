# Speech Model Evaluation Plan & Commercial License Matrix

## Objective
Select locally runnable speech models for the target Linux Mint laptop that produce acceptable Pakistani Urdu, English, and mixed Urdu-English speech from the user's ~2-minute WAV reference recording while preserving future commercial distribution compatibility.

## Commercial License Policy
- **Distributable defaults MUST use commercially compatible code AND weights** (Apache-2.0, MIT, BSD-3-Clause; conditional ShareAlike CC-BY-SA-4.0 clearly labelled as secondary).
- **Non-commercial weights (CC-BY-NC-4.0, CPML, CC-BY-NC-SA-4.0)** are strictly excluded from the distributable default configuration and documented only as non-distributable references.
- Code license and weight license are always tracked separately.

## Candidate Matrix (Primary-Source Verified)

| Criterion | Default Distributable: `indic_parler_openvoice` | Secondary Direct Urdu: `f5_tts_urdu` | Excluded (Non-Commercial): Meta MMS + OpenVoice | Excluded (Rejected): Coqui XTTS-v2 / Fish 1.5 / Chatterbox |
| :--- | :--- | :--- | :--- | :--- |
| **Components** | [ai4bharat/indic-parler-tts](https://huggingface.co/ai4bharat/indic-parler-tts) + [myshell-ai/OpenVoiceV2](https://huggingface.co/myshell-ai/OpenVoiceV2) (+ optional [hexgrad/Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) / [MeloTTS](https://github.com/myshell-ai/MeloTTS) for fast English) | [SWivid/F5-TTS](https://github.com/SWivid/F5-TTS) + [multilingual-tts/F5-TTS-OpenBible-Urdu](https://huggingface.co/multilingual-tts/F5-TTS-OpenBible-Urdu) | [facebook/mms-tts-urd-script_arabic](https://huggingface.co/facebook/mms-tts-urd-script_arabic) + OpenVoice v2 | [coqui/XTTS-v2](https://huggingface.co/coqui/XTTS-v2) / [fishaudio/fish-speech-1.5](https://huggingface.co/fishaudio/fish-speech-1.5) / [ResembleAI/chatterbox](https://github.com/resemble-ai/chatterbox) |
| **Code License** | Apache-2.0 + MIT | MIT | Apache-2.0 + MIT | MPL-2.0 / BSD-3 / MIT |
| **Weight License** | **Apache-2.0** (`indic-parler-tts`, `Kokoro-82M`) + **MIT** (`OpenVoiceV2`, `MeloTTS`) | **CC-BY-SA-4.0** (OpenBible Urdu); base Emilia is CC-BY-NC-4.0 (excluded) | **CC-BY-NC-4.0** (MMS) + MIT (OpenVoice) | CPML (non-commercial) / CC-BY-NC-SA-4.0 / MIT (no Urdu) |
| **Commercial Use** | **Permitted** | **Conditional** (Attribution + ShareAlike on modified weights) | **Prohibited** (excluded from defaults) | **Prohibited** or **Urdu Unsupported** |
| **Urdu Support** | Native Urdu Perso-Arabic script claimed | Trained on ~30,600 OpenBible Urdu utterances | Native `urd-script_arabic` VITS | XTTS base omits Urdu; Fish 1.5 omits Urdu; Chatterbox omits Urdu |
| **English & Code-Switching** | Urdu + English natively; deterministic script segmentation feeds same OpenVoice v2 speaker embedding | Urdu-only checkpoint (`vocab.txt`); English/mixed NOT claimed on this adapter | Modular split possible, but MMS weights non-commercial | N/A (excluded) |
| **Reference Audio** | 5–15s clean WAV segment extracted automatically from user's ~2-min WAV | 5–10s clean WAV segment + transcript (`--ref_text`) | 5–15s clean WAV segment | N/A |
| **Download Footprint** | ~4.0 GB (`indic-parler-tts`, 940M params) + ~131 MB (`OpenVoiceV2`) | **5.37 GB** (`model_last.pt` training checkpoint) + Vocos | ~145 MB (`36.3M` params) + ~131 MB | N/A |
| **CPU / GPU Notes** | CPU fallback supported (slower on Parler-TTS); ~4–5 GB VRAM estimated on GPU *(unverified on target laptop)* | CPU supported (slow); ~2–4 GB VRAM community estimate *(unverified on target laptop)* | Lightweight CPU candidate *(excluded from default due to NC license)* | N/A |
| **Pakistani Urdu Listening Score** | **UNTESTED** (pending Linux Mint laptop run) | **UNTESTED** (pending Linux Mint laptop run) | **UNTESTED** | Excluded |
| **Offline Behavior** | Designed for `local_files_only=True` after local model download *(verify air-gapped on laptop)* | Requires local Vocos + explicit `--ref_text` to avoid Whisper download *(verify air-gapped on laptop)* | Offline capable | Excluded |
| **Status** | **Selected Distributable Default Adapter** | **Selected Secondary Urdu Adapter** | **Documented Only (Not Default)** | **Rejected / Deferred** |

## Repeatable Proof-of-Concept Harness (Milestone 1)
- Hardware discovery: `python3 scripts/hardware_probe.py`
- Isolated Linux Mint PoC setup: `bash scripts/setup_poc_env.sh indic_parler_openvoice auto`
- Evaluation harness: `python3 scripts/poc_eval.py --engine indic_parler_openvoice --reference-wav /path/to/voice.wav --output-dir data/eval_runs`

## Fixed 5-Prompt Listening Benchmark
All candidates evaluated on Linux Mint use the exact 5 prompts embedded in `scripts/poc_eval.py`:
1. `ur_formal`: Formal Pakistani Urdu welcome and personal voice test.
2. `ur_phonetics`: Pakistani place names (`راولپنڈی`, `گوجرانوالہ`, `ملتان`, `مظفرآباد`) testing retroflexes and aspirates.
3. `en_baseline`: Clean English VoiceCity description.
4. `ur_en_mixed`: Mixed Urdu-English code-switching (`application`, `launch review`).
5. `ur_numerals`: Numerals, dates (`2026`), currency (`45,000 روپے`), and decimal percentages (`92.5 فیصد`).

## Gate Rules
- Never fabricate or extrapolate listening scores, RTF, or VRAM metrics from the Pixel 7 Pro PRoot dev environment.
- Every listening criterion (intelligibility, pronunciation, naturalness, voice similarity, code-switching) remains marked `UNTESTED` until evaluated by a fluent Pakistani Urdu listener on the Linux Mint laptop.
