# Honest Speech Engine Evaluation Matrix

**Last Updated:** 2026-11-27  
**Core Rule:** Never confuse Standard Text-to-Speech, Voice Conversion, Cross-Linguistic Conversion, and Genuine Reference-Audio Voice Cloning. Never extrapolate Pakistani Urdu quality from language lists or non-Urdu benchmarks.

---

## 1. Strict Capability Taxonomy Used in VoiceCity

| Capability Class | Definition | Uses User WAV to Clone Voice? |
| :--- | :--- | :--- |
| **`standard_tts`** | Synthesizes speech in a fixed or text-described synthetic voice | **No** |
| **`reference_voice_cloning`** | Conditions generation directly on the user's reference WAV recording | **Yes** |
| **`voice_conversion`** | Transfers target speaker timbre onto an existing source speech WAV | **Yes (audio-to-audio only)** |
| **`cross_linguistic_voice_conversion`** | Experimental pipeline piping Standard TTS audio into a Voice Converter on a non-native target language | **Yes (experimental / unverified)** |

---

## 2. Comprehensive Candidate Matrix (Primary-Source Grounded)

*Note: Hardware figures marked `(est.)` come from community/third-party reports where official repos omit hard minimums; actual Linux Mint RAM, VRAM, and RTF remain **unmeasured** until Phase 1 laptop runs complete.*

| Candidate | Capability Class | Reference Audio Support | Verified Native Languages | Code / Weight Licenses | Download Size | Practical RAM / VRAM | CPU Feasibility | Install Complexity | Known Limitations & Authoritative Links |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. F5-TTS OpenBible Urdu** (`f5_tts_urdu`) | `reference_voice_cloning` | **Yes** (5–10s WAV + required transcript) | **Urdu (`ur`) ONLY** | MIT / **CC-BY-SA-4.0** (ShareAlike optional); Vocos MIT | **~5.5 GB** (`model_last.pt` 5.37 GB + Vocos) | ≥8 GB RAM / ≥4 GB VRAM (est.) | Slow (unmeasured RTF; GPU strongly preferred) | Moderate (PyTorch + `F5-TTS` git install + local Vocos) | Urdu ONLY (no English/Latin). Open Bible domain bias; Pakistani colloquial accent **untested**. Requires explicit transcript to block Whisper downloads. [HF](https://huggingface.co/multilingual-tts/F5-TTS-OpenBible-Urdu), [Code](https://github.com/SWivid/F5-TTS) |
| **2. Qwen3-TTS 0.6B-Base** (`qwen3_tts_en`) | `reference_voice_cloning` | **Yes** (3–10s WAV; transcript optional) | **English (`en`)** + ZH/JA/KO/DE/FR/RU/PT/ES/IT (**NO Urdu**) | **Apache-2.0 / Apache-2.0** | **~2.52 GB** (0.6B) / ~4.54 GB (1.7B) | ≥8 GB RAM / ≥4–6 GB VRAM (est.) | Possible, slow (est.) | Low–Moderate (`pip install qwen-tts`) | **Urdu NOT supported.** Permissive commercial English voice cloning. [HF](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base), [Code](https://github.com/QwenLM/Qwen3-TTS) |
| **3. ResembleAI Chatterbox** *(Evaluated alternative)* | `reference_voice_cloning` | **Yes** (~10s WAV) | **English (`en`)** + 22 langs (**NO Urdu**) | **MIT / MIT** | ~1.5–2.5 GB (350M Turbo / 500M Base) | ≥8 GB RAM / ≥6–10 GB VRAM (est.) | Slow (GPU recommended) | Moderate | **Urdu NOT supported** (supports Hindi/Arabic, not Urdu). Embeds PerTh perceptual watermark. [GitHub](https://github.com/resemble-ai/chatterbox), [HF](https://huggingface.co/ResembleAI/chatterbox) |
| **4. Dual Cloning Router** (`dual_cloning_router`) | `reference_voice_cloning` (compositional) | **Yes** (same prepared WAV fed to both) | **Urdu (`f5_tts_urdu`) + English (`qwen3_tts_en`)**; Mixed = experimental stitching | MIT + Apache-2.0 / **CC-BY-SA-4.0 (ur)** + **Apache-2.0 (en)** | **~8.02 GB** combined | ≥12 GB RAM / ≥6–8 GB VRAM (est.) | Very slow for both on CPU | Moderate–High (2 runtimes) | Timbre match between F5-TTS Urdu and Qwen3-TTS English segments is **empirically untested**. Honestly exposes single-language cloning if only one is installed. |
| **5. AI4Bharat Indic Parler-TTS** (`indic_parler_tts`) | **`standard_tts` ONLY** | **NO** (ignores user WAV; text-described synthetic voice) | **Urdu (`ur`)**, **English (`en`)**, + 19 Indic langs | **Apache-2.0 / Apache-2.0** | **~4.0 GB** (940M params) | ≥8 GB RAM / ≥4–5 GB VRAM (est.) | Slow (autoregressive 940M) | Moderate (`parler-tts` git install) | **NOT a voice cloning model.** Cannot learn user's voice. Pakistani Urdu prosody untested. [HF](https://huggingface.co/ai4bharat/indic-parler-tts) |
| **6. MyShell OpenVoice v2** (`openvoice_v2_converter`) | **`voice_conversion` ONLY** | **Yes** (5–15s target WAV + source speech WAV) | **EN, ES, FR, ZH, JA, KO** (**Urdu NOT native**) | **MIT / MIT** | **~131 MB** (`checkpoint.pth`) | ≥4 GB RAM / ≥2–3 GB VRAM (est.) | Usable (slower; CPU device mapping needed) | Moderate (`OpenVoice` git install) | Audio-to-audio converter ONLY (not standalone TTS). Urdu is NOT a documented native V2 language. [GitHub](https://github.com/myshell-ai/OpenVoice), [HF](https://huggingface.co/myshell-ai/OpenVoiceV2) |
| **7. Experimental Indic Parler -> OpenVoice v2** (`experimental_parler_openvoice`) | **`cross_linguistic_voice_conversion`** (`experimental`) | **Yes** (via OpenVoice v2 stage) | Native: EN; **Experimental: Urdu & Mixed** | **Apache-2.0 + MIT / Apache-2.0 + MIT** | **~4.14 GB** combined | ≥8 GB RAM / ≥5–6 GB VRAM (est.) | Very slow (2 neural stages) | Moderate–High | **EXPERIMENTAL ONLY — NOT verified Urdu voice cloning.** Urdu is not native to OpenVoice v2; accent & timbre degradation unverified. |
| **8. k2-fsa OmniVoice** *(Excluded: Non-Commercial)* | `reference_voice_cloning` | **Yes** (3–10s WAV) | 600+ langs incl. **Urdu (~211h data)** & **English** | Apache-2.0 / **CC-BY-NC (Non-Commercial)** | ~2–3 GB (0.6B DLM) | ≥12 GB RAM / ≥6.5–8 GB VRAM (est.) | Impractical for interactive CPU | Moderate–High | **Excluded from distributable defaults** due to CC-BY-NC training data (Emilia) weight restrictions despite Apache-2.0 code. [GitHub](https://github.com/k2-fsa/OmniVoice), [HF](https://huggingface.co/k2-fsa/OmniVoice) |
| **9. Zyphra Zonos v0.1 / ZONOS3-Mini** *(Deferred)* | `reference_voice_cloning` | **Yes** (5–30s WAV) | v0.1: EN/JA/ZH/FR/DE (**NO Urdu**). ZONOS3-Mini claims 43 langs incl. Urdu | **Apache-2.0 / Apache-2.0** (v0.1) | ~3.2 GB+ (1.6B) | ≥12 GB RAM / ≥6 GB+ VRAM | Impractical on CPU | High (requires system `espeak-ng` + CUDA Triton) | v0.1 omits Urdu; ZONOS3-Mini Urdu quality & primary HF weight verification pending. [GitHub](https://github.com/Zyphra/Zonos), [HF](https://huggingface.co/Zyphra/Zonos-v0.1-transformer) |
| **10. Seed-VC** *(Excluded: GPL-3.0)* | `voice_conversion` | **Yes** (language-agnostic audio-to-audio) | Language-agnostic (incl. Urdu speech input) | **GPL-3.0 / GPL-3.0** | ~1–2 GB | ≥8 GB RAM / ≥4 GB VRAM (est.) | Slow | Moderate | Strong copyleft GPL-3.0 license; audio-to-audio only. [GitHub](https://github.com/Plachtaa/seed-vc) |
| **11. CosyVoice 2 / 3** *(Excluded: No Native Urdu)* | `reference_voice_cloning` | **Yes** (3–30s WAV) | ZH, EN, JA, KO, DE, ES, FR, IT, RU (**NO native Urdu**) | **Apache-2.0 / Apache-2.0** | ~1.5–2 GB | ≥8 GB RAM / ≥4–6 GB VRAM (est.) | Slow | High | No native Urdu out-of-the-box; cross-lingual Urdu phonetics biased toward Chinese/English. [GitHub](https://github.com/FunAudioLLM/CosyVoice) |
| **12. Meta MMS Urdu / Coqui XTTS-v2 / Fish 1.5** *(Excluded: Non-Commercial)* | MMS: `standard_tts`; XTTS/Fish: `reference_voice_cloning` | MMS: **No**; XTTS/Fish: Yes | MMS: Urdu; XTTS/Fish base: **NO Urdu** | Apache/MPL/BSD / **CC-BY-NC-4.0 / CPML / CC-BY-NC-SA-4.0** | 145 MB / 1.87 GB / 1.28 GB | 2–6 GB VRAM | MMS fast on CPU; XTTS/Fish slow | Low–Moderate | Strictly **non-commercial weights** (Coqui dissolved Jan 2024; XTTS Urdu FT `mit` tag invalid). Excluded from distributable defaults. |

---

## 3. Five-Axis Verification Ledger (Honest Current Status)

| Engine Adapter | Automated Tests Passed | Model Integration Verified (Real Load) | Actual Speech Generated | Human Listening Completed | Commercial Licensing Verified |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `f5_tts_urdu` | **Yes** | Pending (Linux Mint) | **No** | **Pending** | Yes (CC-BY-SA-4.0 optional) |
| `qwen3_tts_en` | **Yes** | Pending (Linux Mint) | **No** | **Pending** | Yes (Apache-2.0 permissive) |
| `dual_cloning_router` | **Yes** | Pending (Linux Mint) | **No** | **Pending** | Yes (Mixed Apache-2.0 + CC-BY-SA-4.0) |
| `indic_parler_tts` | **Yes** | Pending (Linux Mint) | **No** | **Pending** | Yes (Apache-2.0 · NOT cloning) |
| `openvoice_v2_converter` | **Yes** | Pending (Linux Mint) | **No** | **Pending** | Yes (MIT · Urdu NOT native) |
| `experimental_parler_openvoice` | **Yes** | Pending (Linux Mint) | **No** | **Pending** | Yes (Apache-2.0 + MIT · Experimental Urdu) |
