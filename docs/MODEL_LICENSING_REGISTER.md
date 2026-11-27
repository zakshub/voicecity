# VoiceCity Model & Dependency Licensing Register

**Last Updated:** 2026-11-27  
**Policy:** A permissive inference-code license (MIT / Apache-2.0) NEVER overrides a restrictive or ShareAlike weight license. Code and weight licenses are audited and tracked independently.

---

## 1. Core Application Dependencies (All Commercially Permissive)

| Dependency | Purpose | License | Authoritative Source |
| :--- | :--- | :--- | :--- |
| `fastapi` | Local REST API server | MIT | [github.com/fastapi/fastapi/blob/master/LICENSE](https://github.com/fastapi/fastapi/blob/master/LICENSE) |
| `uvicorn` | ASGI local HTTP server (`127.0.0.1`) | BSD-3-Clause | [github.com/encode/uvicorn/blob/master/LICENSE.md](https://github.com/encode/uvicorn/blob/master/LICENSE.md) |
| `pydantic` / `pydantic-settings` | Schema & config validation | MIT | [github.com/pydantic/pydantic/blob/main/LICENSE](https://github.com/pydantic/pydantic/blob/main/LICENSE) |
| `python-multipart` | Multipart WAV file upload parsing | Apache-2.0 | [github.com/Kludex/python-multipart/blob/master/LICENSE.txt](https://github.com/Kludex/python-multipart/blob/master/LICENSE.txt) |
| `python-dotenv` | Local `.env` loading | BSD-3-Clause | [github.com/theskumar/python-dotenv/blob/main/LICENSE](https://github.com/theskumar/python-dotenv/blob/main/LICENSE) |
| `pytest` / `httpx` | Development & QA test suite | MIT / BSD-3-Clause | [pytest](https://github.com/pytest-dev/pytest/blob/main/LICENSE), [httpx](https://github.com/encode/httpx/blob/master/LICENSE.md) |
| `ffmpeg` (optional OS tool) | Runtime-detected MP3 export (`libmp3lame`) | LGPL/GPL (external binary, invoked via CLI subprocess, never statically linked) | [ffmpeg.org/legal.html](https://ffmpeg.org/legal.html) |

## 2. Bundled Frontend Assets
- `frontend/index.html`, `frontend/assets/styles.css`, `frontend/assets/app.js` are 100% original VoiceCity source files.
- Zero third-party JavaScript frameworks, zero external CDN links, zero bundled commercial fonts (uses OS system fonts + local Urdu Nastaliq/Naskh font stack).

---

## 3. Speech Model Licensing Register (Code vs. Weights Strictly Separated)

| Model / Checkpoint | Capability Class | Code License & Source | Weight License & Source | Category | Commercial Distributability |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Qwen3-TTS 0.6B / 1.7B Base** (`Qwen/Qwen3-TTS-12Hz-0.6B-Base`) | Reference-Audio Voice Cloning (**English** + 9 langs; **NO Urdu**) | Apache-2.0 ([QwenLM/Qwen3-TTS LICENSE](https://github.com/QwenLM/Qwen3-TTS/blob/main/LICENSE)) | **Apache-2.0** ([HF Model Card](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base)) | **Permissive Commercial** | **Permitted** (English cloning; does not solve Urdu). |
| **ResembleAI Chatterbox** (`ResembleAI/chatterbox`) | Reference-Audio Voice Cloning (**English** + 22 langs; **NO Urdu**) | MIT ([resemble-ai/chatterbox](https://github.com/resemble-ai/chatterbox)) | **MIT** ([HF Model Card](https://huggingface.co/ResembleAI/chatterbox)) | **Permissive Commercial** | **Permitted** (includes embedded PerTh perceptual watermark; does not solve Urdu). |
| **AI4Bharat Indic Parler-TTS** (`ai4bharat/indic-parler-tts`) | **Standard TTS ONLY** (Urdu + English; **NOT voice cloning**) | Apache-2.0 ([parler-tts LICENSE](https://github.com/huggingface/parler-tts/blob/main/LICENSE)) | **Apache-2.0** ([HF Model Card](https://huggingface.co/ai4bharat/indic-parler-tts)) | **Permissive Commercial** | **Permitted** (synthetic speaker TTS only — NOT personal voice cloning). |
| **MyShell OpenVoice v2** (`myshell-ai/OpenVoiceV2`) | **Voice Conversion ONLY** (EN/ES/FR/ZH/JA/KO; **Urdu NOT native**) | MIT ([OpenVoice LICENSE](https://github.com/myshell-ai/OpenVoice/blob/main/LICENSE)) | **MIT** ([HF Model Card](https://huggingface.co/myshell-ai/OpenVoiceV2)) | **Permissive Commercial** | **Permitted** (converter only; Urdu cross-lingual transfer is experimental). |
| **F5-TTS OpenBible Urdu** (`multilingual-tts/F5-TTS-OpenBible-Urdu`) | Reference-Audio Voice Cloning (**Urdu ONLY**) | MIT ([SWivid/F5-TTS LICENSE](https://github.com/SWivid/F5-TTS/blob/main/LICENSE)) | **CC-BY-SA-4.0** ([HF Model Card](https://huggingface.co/multilingual-tts/F5-TTS-OpenBible-Urdu)) + Vocos MIT ([vocos](https://huggingface.co/charactr/vocos-mel-24khz)) | **Optional ShareAlike** | **Conditional:** Commercial use allowed ONLY with Attribution + ShareAlike on modified weights. Kept optional, never hidden as permissive Apache/MIT. |
| **Zyphra Zonos v0.1** (`Zyphra/Zonos-v0.1-transformer`) | Reference-Audio Voice Cloning (EN/JA/ZH/FR/DE; **NO Urdu in v0.1**) | Apache-2.0 ([Zyphra/Zonos](https://github.com/Zyphra/Zonos)) | **Apache-2.0** ([HF Model Card](https://huggingface.co/Zyphra/Zonos-v0.1-transformer)) | **Permissive Commercial** | **Permitted** (requires `espeak-ng`, LGPL/GPL system library; v0.1 omits Urdu). |
| **FunAudioLLM CosyVoice 2 / 3** (`FunAudioLLM/CosyVoice`) | Reference-Audio Voice Cloning (EN/ZH/JA/KO/EU; **NO native Urdu**) | Apache-2.0 ([CosyVoice](https://github.com/FunAudioLLM/CosyVoice)) | **Apache-2.0** ([HF Org](https://huggingface.co/FunAudioLLM)) | **Permissive Commercial** | **Permitted** (no official native Urdu support). |
| **Seed-VC** (`Plachtaa/seed-vc`) | Language-Agnostic Voice Conversion | **GPL-3.0** ([seed-vc](https://github.com/Plachtaa/seed-vc)) | **GPL-3.0** ([HF Model Card](https://huggingface.co/Plachta/Seed-VC)) | **Strong Copyleft (Excluded Default)** | **Copyleft obligation:** GPL-3.0 requires derivative software distribution under GPL-3.0. |
| **k2-fsa OmniVoice** (`k2-fsa/OmniVoice`) | Multilingual Reference Voice Cloning (600+ langs incl. 211h Urdu + EN) | Apache-2.0 ([k2-fsa/OmniVoice](https://github.com/k2-fsa/OmniVoice)) | **CC-BY-NC** (Emilia training data restriction) ([HF Model Card](https://huggingface.co/k2-fsa/OmniVoice)) | **Non-Commercial Restricted** | **Prohibited** for commercial distribution. Excluded from distributable defaults. |
| **F5-TTS Base (Emilia)** (`SWivid/F5-TTS`) | Reference-Audio Voice Cloning (EN/ZH) | MIT ([LICENSE](https://github.com/SWivid/F5-TTS/blob/main/LICENSE)) | **CC-BY-NC-4.0** ([README](https://github.com/SWivid/F5-TTS#license)) | **Non-Commercial Restricted** | **Prohibited** for commercial distribution. Excluded. |
| **Meta MMS Urdu TTS** (`facebook/mms-tts-urd-script_arabic`) | Standard VITS TTS (Urdu; NOT voice cloning) | Apache-2.0 (`transformers`) | **CC-BY-NC-4.0** ([HF Model Card](https://huggingface.co/facebook/mms-tts-urd-script_arabic)) | **Non-Commercial Restricted** | **Prohibited** for commercial distribution. Excluded. |
| **Coqui XTTS-v2 & `XTTS-v2-Urdu-FT`** | Reference-Audio Voice Cloning (base omits Urdu; FT inherits CPML) | MPL-2.0 ([coqui-ai/TTS](https://github.com/coqui-ai/TTS/blob/dev/LICENSE.txt)) | **CPML 1.0.0** ([coqui/XTTS-v2](https://huggingface.co/coqui/XTTS-v2)) | **Non-Commercial Restricted (Blocker)** | **Prohibited.** Upstream `mit` tag on community Urdu FT cannot override CPML; Coqui Inc. dissolved Jan 2024. |
| **Fish Speech 1.5** (`fishaudio/fish-speech-1.5`) | Reference-Audio Voice Cloning (13 langs; **NO Urdu**) | BSD-3-Clause ([LICENSE](https://github.com/fishaudio/fish-speech/blob/main/LICENSE)) | **CC-BY-NC-SA-4.0** ([HF Model Card](https://huggingface.co/fishaudio/fish-speech-1.5)) | **Non-Commercial Restricted** | **Prohibited** for commercial distribution + Urdu unsupported. |

---

## 4. Key Licensing Gap Identified Honestly
- **English reference-audio voice cloning** has strong, 100% **permissive commercial (Apache-2.0 / MIT)** checkpoints (`Qwen3-TTS-12Hz-0.6B-Base`, `ResembleAI Chatterbox`).
- **Pakistani Urdu reference-audio voice cloning** currently has **NO verified, permissive Apache-2.0/MIT zero-shot checkpoint**:
  - The strongest open-weight Urdu reference-audio cloning checkpoint without a Non-Commercial ban is **`multilingual-tts/F5-TTS-OpenBible-Urdu`**, which carries **CC-BY-SA-4.0 (ShareAlike)** and is therefore kept **optional and explicitly labelled**.
  - Multilingual zero-shot Urdu models like **`k2-fsa/OmniVoice`** (211h Urdu) carry **CC-BY-NC** non-commercial weight restrictions despite Apache-2.0 inference code.
  - **`Indic Parler-TTS` (Apache-2.0) + `OpenVoice v2` (MIT)** are both permissive, **but** Indic Parler is Standard TTS (not voice cloning) and Urdu is not native to OpenVoice v2, making that pairing **experimental cross-linguistic conversion** until empirically tested.
