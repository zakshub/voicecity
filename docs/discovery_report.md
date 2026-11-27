# VoiceCity: Discovery and Technical Evaluation Report

**Date:** 2026-11-27  
**Stage:** Phase 0 — Foundation & Discovery Audit (No Implementation Started)  
**Governing Handoff:** [`docs/ANTIGRAVITY_HANDOFF.md`](ANTIGRAVITY_HANDOFF.md)  
**Evaluation Criteria:** [`docs/MODEL_EVALUATION.md`](MODEL_EVALUATION.md)  
**Decision Gate:** Awaiting explicit user approval before starting Phase 1 Proof of Concept.

---

## Epistemic Classification Standard

To prevent conflating primary-source evidence with estimates or community anecdotes, every finding in this report is explicitly classified into one of three categories:

- **Verified Fact:** Directly observed in this repository, executed locally in the workspace environment, or confirmed from an official repository, model card, or license file.
- **Assumption:** A working engineering premise required for planning that has not yet been confirmed by the user or measured on target hardware.
- **Unverified Claim (Pending Verification):** A performance figure, hardware estimate, language-quality claim, or runtime behavior reported by third-party sources or inferred from model architecture that **must be empirically verified** on the target Linux Mint laptop during Phase 1.

---

## 1. Repository Audit

### 1.1 Workspace & Git Verification (Verified Facts)
- **Project Directory (`pwd`):** `/root/2026-portfolio/voicecity`
- **Git Remote (`git remote -v`):** `origin` → `https://github.com/zakshub/voicecity.git` (fetch and push)
- **Active Branch (`git branch --show-current`):** `main`
- **Baseline Working Tree (`git status`):** Clean prior to adding this report (`Your branch is up to date with 'origin/main'`).
- **Latest Pre-Report Commit (`git log -1`):** `9ac148b031e2dea935bbcda1c206dd547256eb66` — *"Add HTTPX test client dependency to development extras"*

### 1.2 Structure & Scaffold Findings (Verified Facts)
- **Documentation Suite:** All 10 foundation documents exist under `docs/` (`ACCEPTANCE_CHECKLIST.md`, `ANTIGRAVITY_HANDOFF.md`, `ARCHITECTURE.md`, `DEVELOPMENT.md`, `MODEL_EVALUATION.md`, `OPEN_DECISIONS.md`, `PRIVACY_SECURITY.md`, `PRODUCT_REQUIREMENTS.md`, `ROADMAP.md`, `UX_DIRECTION.md`).
- **Truthful API Scaffold (`app/main.py`):**
  - `GET /health` returns `{"status": "ok", "service": "voicecity"}`.
  - `GET /api/v1/capabilities` returns `"voice_profiles": False`, `"speech_generation": False`, `"remote_inference": False`, and marks `"urdu"`, `"english"`, and `"mixed_language"` as `"pending_model_evaluation"`. No fake or unimplemented features are claimed.
- **Data & Secret Exclusions (`.gitignore`):** Excludes audio files (`*.wav`, `*.mp3`, `*.m4a`, `*.flac`, `*.ogg`, `*.aac`), model weights (`*.safetensors`, `*.ckpt`, `*.pth`, `*.pt`, `*.onnx`, `*.bin`), runtime directories (`data/`, `models/`, `voice_profiles/`, `recordings/`, `generated_audio/`, `exports/`), secrets (`.env`, `.env.*`, `*.pem`, `*.key`, `secrets/`, `credentials/`), and logs. No user audio or model weights are tracked in Git.
- **Automated Test Execution Status:** Running `python3 -m pytest` in the current container failed with `No module named pytest` because only `pip`, `proot-distro`, `pydantic` (1.10.27), and `typing_extensions` are installed in the container's Python environment, and no dependencies were installed during discovery per policy.

### 1.3 Inconsistencies & Gaps Identified (Verified Facts)
1. **Unused Declared Dependency (`app/core/config.py` vs. `pyproject.toml`):** `pyproject.toml` declares `pydantic-settings>=2.5` under `[project.optional-dependencies] api`, but `app/core/config.py` implements a plain Python `Settings` class using `os.getenv()` directly (and does not parse `.env` files automatically).
2. **Missing `VOICECITY_TTS_PROVIDER` in Config:** `.env.example` defines `VOICECITY_TTS_PROVIDER=`, but `app/core/config.py` does not read or expose this variable.
3. **Incomplete Engine Protocol (`app/engine/base.py` vs. `docs/ARCHITECTURE.md`):** `docs/ARCHITECTURE.md` specifies that the speech engine adapter should expose `health_check`, `supported_languages`, `prepare_voice`, `generate`, and capability metadata. Currently, `SpeechEngine(Protocol)` in `app/engine/base.py` only defines `health_check`, `supported_languages`, and `generate`.
4. **Missing `scripts/` Directory (`README.md`):** `README.md` lists `scripts/: development and maintenance helpers` in the repository map, but no `scripts/` directory exists yet in the repository.
5. **Python Version / ML Wheel Compatibility Risk:** `pyproject.toml` sets `requires-python = ">=3.11"`. The current PRoot workflow container runs Python `3.13.13`. *(Assumption / Risk:)* Many ML/audio packages (PyTorch, torchaudio, vocoders, phonemizers) have lagging wheel availability on Python 3.13; the target Linux Mint inference environment should standardize on Python 3.11 or 3.12 once verified.

---

## 2. Hardware Discovery & Linux Mint Diagnostic Command

### 2.1 Current Workflow Environment (Verified Facts — NOT the Inference Target)
Running system inspection commands inside the active workspace confirmed:
- **OS / Kernel:** `Linux localhost 6.17.0-PRoot-Distro #1 SMP PREEMPT_DYNAMIC aarch64 GNU/Linux` (Debian GNU/Linux 13 `trixie` via PRoot)
- **CPU:** 8-core ARM (`4× Cortex-A55`, `2× Cortex-A78`, `2× Cortex-X1` — phone SoC)
- **RAM:** `11 GiB` total, `7.3 GiB` used, `2.6 GiB` available (`5.6 GiB` swap, `545 MiB` free)
- **Disk (`/`):** `110 G` size, `92 G` used, `19 G` available (`84%` used)
- **Python:** `Python 3.13.13` (`/data/data/com.termux/files/usr/bin/python3`)
- **GPU Tooling:** `lspci` not found; `nvidia-smi` not found.

This confirms the workspace is the Termux/PRoot phone environment noted in [`docs/DEVELOPMENT.md`](DEVELOPMENT.md) and [`docs/ANTIGRAVITY_HANDOFF.md`](ANTIGRAVITY_HANDOFF.md), and **is not the target inference machine**.

### 2.2 Why the Hardware Discovery Command Failed (Verified Fact)
1. **Container command failure (exit code `1`):** The command executed in the PRoot container (`lscpu; free -h; df -h; lspci 2>&1; which nvidia-smi 2>&1`) exited with status `1` for two exact reasons:
   - `lspci` failed (`bash: line 1: lspci: command not found`) because the `pciutils` package is not installed in the PRoot container (and Android PRoot does not expose a host PCI bus).
   - `which nvidia-smi` exited with status `1` because `nvidia-smi` is absent from `PATH`; because it was the last command in the semicolon-separated list, the shell returned exit code `1`.
2. **Weaknesses in the previously suggested laptop one-liner:**
   - It chained commands with `&&`, meaning a single non-zero exit (e.g., `lscpu | grep ...` failing on a non-English locale) would abort all remaining checks.
   - It omitted `cat /etc/os-release` and `python3 --version` required by [`docs/DEVELOPMENT.md`](DEVELOPMENT.md).
   - It only queried `nvidia-smi` for VRAM, missing AMD Radeon (`sysfs` VRAM counters) and Linux Mint's built-in `inxi` hardware reporter.

### 2.3 Corrected Diagnostic Command for Linux Mint
Run the following non-aborting block on the target **Linux Mint** laptop and paste the output back:

```bash
{
  echo "=== OS & KERNEL ==="
  uname -a
  [ -r /etc/os-release ] && cat /etc/os-release
  [ -r /etc/linuxmint/info ] && cat /etc/linuxmint/info
  echo "=== PYTHON ==="
  command -v python3 >/dev/null && python3 --version || echo "python3 not found"
  echo "=== CPU ==="
  LC_ALL=C lscpu | grep -E "Architecture|Model name|CPU\(s\)|Socket|Core\(s\) per socket|Thread" || lscpu
  echo "=== RAM ==="
  free -h
  echo "=== DISK ==="
  df -h .
  echo "=== GPU & VRAM ==="
  if command -v lspci >/dev/null; then
    lspci -nn | grep -Ei 'vga|3d|display' || echo "No GPU matched in lspci"
  elif [ -x /usr/sbin/lspci ]; then
    /usr/sbin/lspci -nn | grep -Ei 'vga|3d|display' || echo "No GPU matched in lspci"
  else
    echo "lspci not installed (sudo apt install pciutils)"
  fi
  if command -v nvidia-smi >/dev/null; then
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
  else
    echo "nvidia-smi not found (no NVIDIA driver or no NVIDIA GPU)"
  fi
  for f in /sys/class/drm/card*/device/mem_info_vram_total; do
    [ -r "$f" ] && echo "AMD/DRM VRAM ($f): $(awk '{printf "%.2f GiB\n", $1/1024/1024/1024}' "$f")"
  done
  if command -v inxi >/dev/null; then
    echo "=== INXI SUMMARY ==="
    inxi -GSCm --no-host
  fi
}
```

### 2.4 Target Hardware Metrics Still Unknown (Unverified)
- Target Linux Mint CPU model, architecture (`x86_64` assumed, not yet verified), and core count
- Total and available RAM
- Discrete or integrated GPU model, driver stack (CUDA / ROCm / CPU-only), and exact VRAM
- Free disk space available for model checkpoints and Python ML environments

---

## 3. Candidate Comparison Table (With Direct Source Links)

Four plausible local zero-shot voice-cloning candidates were evaluated from primary repositories and model cards. Claims not stated in official repositories are explicitly tagged as **Unverified / Third-party estimate**.

| Criterion | Candidate 1: F5-TTS + Urdu Checkpoint (`F5-TTS-OpenBible-Urdu`) | Candidate 2: Coqui XTTS-v2 + Community Urdu FT (`XTTS-v2-Urdu-FT`) | Candidate 3: Fish Speech v1.5 (`fishaudio/fish-speech-1.5`) | Candidate 4: Two-Stage Hybrid (Meta MMS Urdu + OpenVoice v2) |
| :--- | :--- | :--- | :--- | :--- |
| **Official Sources** | Code: [SWivid/F5-TTS](https://github.com/SWivid/F5-TTS)<br>Urdu Weights: [multilingual-tts/F5-TTS-OpenBible-Urdu](https://huggingface.co/multilingual-tts/F5-TTS-OpenBible-Urdu)<br>Base Weights: [SWivid/F5-TTS (HF)](https://huggingface.co/SWivid/F5-TTS) | Code: [coqui-ai/TTS](https://github.com/coqui-ai/TTS)<br>Base Weights: [coqui/XTTS-v2](https://huggingface.co/coqui/XTTS-v2)<br>Urdu FT: [suhaibrashid17/XTTS-v2-Urdu-FT](https://huggingface.co/suhaibrashid17/XTTS-v2-Urdu-FT) | Code: [fishaudio/fish-speech](https://github.com/fishaudio/fish-speech)<br>v1.5 Weights: [fishaudio/fish-speech-1.5](https://huggingface.co/fishaudio/fish-speech-1.5) | Urdu Base: [facebook/mms-tts-urd-script_arabic](https://huggingface.co/facebook/mms-tts-urd-script_arabic)<br>Code/Converter: [myshell-ai/OpenVoice](https://github.com/myshell-ai/OpenVoice)<br>Converter Weights: [myshell-ai/OpenVoiceV2](https://huggingface.co/myshell-ai/OpenVoiceV2) |
| **Code License (Verified)** | **MIT** ([SWivid/F5-TTS LICENSE](https://github.com/SWivid/F5-TTS/blob/main/LICENSE)) | **MPL-2.0** ([coqui-ai/TTS LICENSE.txt](https://github.com/coqui-ai/TTS/blob/dev/LICENSE.txt)) | **BSD-3-Clause** for core codebase ([fishaudio/fish-speech LICENSE](https://github.com/fishaudio/fish-speech/blob/main/LICENSE)) | **MIT** for OpenVoice ([myshell-ai/OpenVoice LICENSE](https://github.com/myshell-ai/OpenVoice/blob/main/LICENSE)); **Apache-2.0** for Hugging Face `transformers` ([LICENSE](https://github.com/huggingface/transformers/blob/main/LICENSE)) |
| **Weight License (Verified)** | Urdu checkpoint: **CC-BY-SA-4.0** ([HF model card](https://huggingface.co/multilingual-tts/F5-TTS-OpenBible-Urdu)).<br>Base Emilia checkpoint: **CC-BY-NC-4.0** ([SWivid/F5-TTS README](https://github.com/SWivid/F5-TTS#license)). | Base XTTS-v2: **CPML 1.0.0** ([coqui/XTTS-v2](https://huggingface.co/coqui/XTTS-v2), [CPML terms](https://coqui.ai/cpml)).<br>Community FT claims `mit` on [HF card](https://huggingface.co/suhaibrashid17/XTTS-v2-Urdu-FT), which cannot legally override upstream CPML. | v1.5 Weights: **CC-BY-NC-SA-4.0** ([HF model card](https://huggingface.co/fishaudio/fish-speech-1.5)). *(Newer Fish S2/Pro models use custom Fish Audio Research/Community licenses at [fish.audio](https://github.com/fishaudio/fish-speech)).* | MMS Urdu Weights: **CC-BY-NC-4.0** ([HF model card](https://huggingface.co/facebook/mms-tts-urd-script_arabic)).<br>OpenVoice v2 Weights: **MIT** ([myshell-ai/OpenVoiceV2](https://huggingface.co/myshell-ai/OpenVoiceV2)). |
| **Commercial Use** | **Conditional:** CC-BY-SA-4.0 permits commercial use with attribution & ShareAlike on derivatives. Base Emilia weights (CC-BY-NC-4.0) prohibit commercial use. | **Prohibited:** CPML is strictly non-commercial; Coqui Inc. shut down in Jan 2024, leaving no entity to grant commercial licenses. | **Prohibited for v1.5** (CC-BY-NC-SA-4.0). | **Prohibited with MMS** (CC-BY-NC-4.0). **Permitted** if Urdu base is replaced with an Apache-2.0 base such as [ai4bharat/indic-parler-tts](https://huggingface.co/ai4bharat/indic-parler-tts) *(quality unverified)*. |
| **Urdu Evidence** | **Verified:** Trained on ~30,600 Urdu utterances from Open Bible corpus with Perso-Arabic `vocab.txt` ([HF card](https://huggingface.co/multilingual-tts/F5-TTS-OpenBible-Urdu)).<br>**Unverified:** Pakistani conversational accent & colloquial quality. | **Verified:** Base XTTS-v2 omits Urdu (17 languages incl. Hindi/Arabic). Community FT trained on Common Voice Urdu & PRUS CSaLT ([HF card](https://huggingface.co/suhaibrashid17/XTTS-v2-Urdu-FT)).<br>**Unverified:** Naturalness & stability. | **Verified:** v1.5 model card lists 13 core languages (EN, ZH, JA, DE, FR, ES, KO, AR, RU, NL, IT, PL, PT) — **Urdu is NOT officially listed in v1.5** ([HF card](https://huggingface.co/fishaudio/fish-speech-1.5)).<br>**Unverified:** Urdu synthesis quality in v1.5/newer checkpoints. | **Verified:** Meta MMS includes a dedicated `urd-script_arabic` VITS model ([HF card](https://huggingface.co/facebook/mms-tts-urd-script_arabic)).<br>**Unverified:** Pakistani accent fidelity and OpenVoice timbre preservation when applied to Urdu MMS audio. |
| **English & Code-Switching** | **Verified:** OpenBible Urdu `vocab.txt` is built from Urdu Bible transcripts; base F5-TTS is EN/ZH.<br>**Unverified:** Mixed Urdu-English code-switching requires vocabulary verification or dual-model routing. | **Verified:** Base model supports English natively ([HF card](https://huggingface.co/coqui/XTTS-v2)).<br>**Unverified:** Whether Urdu FT degrades English or handles intra-sentence code-switching. | **Verified:** Strong native English in v1.5 ([HF card](https://huggingface.co/fishaudio/fish-speech-1.5)).<br>**Unverified:** Urdu-English code-switching. | **Verified architecture capability:** OpenVoice v2 separates base TTS from tone-color conversion ([OpenVoice README](https://github.com/myshell-ai/OpenVoice)), enabling separate English and Urdu base engines into one cloned voice.<br>**Unverified:** Seam naturalness at language switches. |
| **Reference Audio Requirements** | **Verified:** ~5–10s clean reference clip; 24 kHz Vocos output ([HF card](https://huggingface.co/multilingual-tts/F5-TTS-OpenBible-Urdu)). Empty `--ref_text ""` triggers Whisper ASR auto-transcription ([SWivid/F5-TTS README](https://github.com/SWivid/F5-TTS)). | **Verified:** ~6s reference WAV clip ([coqui/XTTS-v2](https://huggingface.co/coqui/XTTS-v2)). | **Verified:** 10–30s reference audio ([fishaudio/fish-speech docs](https://github.com/fishaudio/fish-speech)). | **Verified:** Short reference audio clip (typically 5–15s) to extract speaker tone-color embedding (`se_extractor`) ([myshell-ai/OpenVoice](https://github.com/myshell-ai/OpenVoice)). |
| **Checkpoint File Size (Verified)** | `model_last.pt`: **5.37 GB** (full training checkpoint) ([HF file tree](https://huggingface.co/multilingual-tts/F5-TTS-OpenBible-Urdu/tree/main)) + Vocos vocoder downloaded separately. | `model.pth`: **~1.87 GB** ([HF file tree](https://huggingface.co/coqui/XTTS-v2/tree/main)) + auxiliary files (`dvae.pth`, `vocab.json`). | `model.pth`: **1.28 GB** ([HF file tree](https://huggingface.co/fishaudio/fish-speech-1.5/tree/main)) + VQ-GAN vocoder checkpoint. | MMS Urdu (`36.3M` params): **~145 MB** ([HF file tree](https://huggingface.co/facebook/mms-tts-urd-script_arabic/tree/main)); OpenVoice v2 `converter/checkpoint.pth`: **~131 MB** ([HF file tree](https://huggingface.co/myshell-ai/OpenVoiceV2/tree/main/checkpoints_v2/converter)). |
| **VRAM / RAM / CPU Requirements** | **Official docs:** No hard minimum VRAM stated; explicitly warns empty `--ref_text ""` adds ASR GPU memory overhead ([SWivid/F5-TTS](https://github.com/SWivid/F5-TTS)).<br>**Unverified third-party estimates:** ~2–4 GB VRAM for basic inference ([HF/community reports](https://github.com/SWivid/F5-TTS/issues)); CPU inference significantly slower than real time. | **Official docs:** No hard minimum VRAM stated on HF card.<br>**Unverified third-party estimates:** ~2.0 GB VRAM (FP16) / ~3.4 GB (FP32) + ~0.3 GB spike for speaker embedding ([GigaGPU breakdown](https://gigagpu.com/)). CPU inference slow. | **Unverified third-party estimates:** ~4–6 GB VRAM at FP16 for v1.5 ([GigaGPU / community reports](https://github.com/fishaudio/fish-speech)). CPU-only speed unverified (expected slow). | **Unverified third-party estimates:** ~2–3 GB VRAM for OpenVoice v2 + base TTS ([OpenVoice issues / community](https://github.com/myshell-ai/OpenVoice/issues)). MMS VITS is lightweight (36.3M params). CPU fallback supported but slower, and `se_extractor.py` may require explicit CPU device mapping ([OpenVoice issues](https://github.com/myshell-ai/OpenVoice/issues)). |
| **Offline Behavior & Network Calls** | **Verified risk:** `load_vocoder(is_local=False)` and empty `--ref_text ""` fetch Vocos/Whisper from Hugging Face on first run ([HF card](https://huggingface.co/multilingual-tts/F5-TTS-OpenBible-Urdu)).<br>**Unverified:** Zero-network offline execution after caching must be tested with network disabled. | **Verified:** Downloads weights via Coqui/HF on first run.<br>**Unverified:** Full offline run with network disabled must be verified in Phase 1. | **Unverified:** Local inference supported, but API/WebUI components and weight downloads must be audited offline in Phase 1. | **Verified:** All weights downloadable locally via Hugging Face (`transformers` + local checkpoints).<br>**Unverified:** Strict air-gapped execution must be verified in Phase 1. |
| **Maintenance Status (Verified)** | Active ([SWivid/F5-TTS](https://github.com/SWivid/F5-TTS)). | **Unmaintained upstream** (Coqui Inc. shut down Jan 2024; community forks exist). | Active ([fishaudio/fish-speech](https://github.com/fishaudio/fish-speech)). | OpenVoice repo public/stable ([myshell-ai/OpenVoice](https://github.com/myshell-ai/OpenVoice)); Hugging Face `transformers` VITS actively maintained. |
| **Phase 1 Verdict** | **Primary End-to-End PoC Candidate** (if GPU is available or CPU latency acceptable). | **Rejected** (CPML licensing blocker + dead upstream). | **Deferred / Not Recommended for Phase 1** (Urdu not officially supported in v1.5 + CC-BY-NC-SA-4.0). | **Primary Low-Hardware / Modular PoC Candidate** (especially if laptop is CPU-only or low-VRAM). |

> **Note on AI4Bharat Models (Evaluated & Excluded from Direct Zero-Shot Table):**
> - [`ai4bharat/indic-parler-tts`](https://huggingface.co/ai4bharat/indic-parler-tts) (**Verified:** Apache-2.0 license, supports Urdu and English) uses *text-prompt voice descriptions* rather than reference-audio voice cloning, so it cannot clone the user's 2-minute WAV directly (though it could potentially serve as an Apache-2.0 Urdu base speaker feeding OpenVoice v2 in a future commercial pipeline — **Unverified**).
> - [`AI4Bharat/IndicF5`](https://github.com/AI4Bharat/IndicF5) (**Verified:** MIT license, zero-shot F5-TTS architecture) officially lists 11 Indian languages and **does not include Urdu** in its core release.

---

## 4. Urdu Quality Evidence and Unknowns

### Verified Linguistic & Dataset Facts
1. **No Listening Tests Completed Yet:** Zero audio samples have been synthesized or audited with the user's 2-minute WAV recording during Phase 0. All naturalness scores remain **Pending Phase 1 Listening Review**.
2. **Script & Phonology Requirements:** Natural Pakistani Urdu requires accurate rendering of retroflex consonants (`ٹ`, `ڈ`, `ڑ`), aspirated stops (`بھ`, `پھ`, `تھ`, `ٹھ`, `دھ`, `ڈھ`), uvular/velar distinctions (`ق` vs `ک`, `غ` vs `گ`, `خ`), and nasalization (`ں`).
3. **Training Domain Narrowing (Verified Fact):** Both `multilingual-tts/F5-TTS-OpenBible-Urdu` (Open Bible Urdu corpus) and `facebook/mms-tts-urd-script_arabic` (Meta MMS, trained primarily on New Testament / religious readings) derive from formal, narrative religious text corpora.

### Unverified Risks & Unknowns (Must Be Tested in Phase 1)
1. **Unvowelized Urdu (Missing Aerab/Diacritics):** Written Urdu normally omits short vowel marks (Zabar, Zer, Pesh). How well `F5-TTS-OpenBible-Urdu` or `MMS Urdu` disambiguate homographs (e.g., `کل` *kal* vs *kul*, `ملک` *mulk* vs *malik*) on modern non-religious prose is **unverified**.
2. **Pakistani vs. Generic/Arabic/Indian Cadence:** Whether the checkpoints sound like natural Pakistani Urdu rather than Arabic-accented or formal robotic narration is **unverified**.
3. **Code-Switching ("Urdish"):** Everyday Pakistani speech mixes English nouns/verbs into Urdu sentences. Neither `F5-TTS-OpenBible-Urdu` nor `mms-tts-urd-script_arabic` has verified mixed-script (`Urdu + Latin`) tokenization; Phase 1 must test how each fails or handles mixed input.
4. **Reference Recording Suitability:** The user's existing ~2-minute WAV has not yet been inspected for sample rate, noise floor, room reverb, or clipping.

---

## 5. License Assessment (Verified Primary-Source Audit)

| Component | Code License & Direct Source | Weight License & Direct Source | Personal Local Use | Commercial Distribution Risk |
| :--- | :--- | :--- | :--- | :--- |
| **F5-TTS (`SWivid/F5-TTS`)** | MIT ([LICENSE](https://github.com/SWivid/F5-TTS/blob/main/LICENSE)) | Base Emilia weights: CC-BY-NC-4.0 ([README](https://github.com/SWivid/F5-TTS#license)) | Allowed | **Blocked** if using Emilia base weights. |
| **F5-TTS Urdu (`multilingual-tts/F5-TTS-OpenBible-Urdu`)** | Uses `SWivid/F5-TTS` (MIT) | CC-BY-SA-4.0 ([Model Card](https://huggingface.co/multilingual-tts/F5-TTS-OpenBible-Urdu)) | Allowed | **Conditional:** Commercial use allowed under CC-BY-SA-4.0 with attribution and ShareAlike on modified weights; dataset provenance (`open-bible-resources`) must still be verified before any commercial release. |
| **Coqui XTTS-v2 & Urdu FT** | MPL-2.0 ([LICENSE.txt](https://github.com/coqui-ai/TTS/blob/dev/LICENSE.txt)) | CPML 1.0.0 ([coqui/XTTS-v2](https://huggingface.co/coqui/XTTS-v2)) | Allowed | **Hard Blocker:** Strictly non-commercial. The `mit` tag on [suhaibrashid17/XTTS-v2-Urdu-FT](https://huggingface.co/suhaibrashid17/XTTS-v2-Urdu-FT) is a **licensing trap** — derivative fine-tunes inherit CPML restrictions, and Coqui Inc. is defunct. |
| **Fish Speech v1.5** | BSD-3-Clause ([LICENSE](https://github.com/fishaudio/fish-speech/blob/main/LICENSE)) | CC-BY-NC-SA-4.0 ([Model Card](https://huggingface.co/fishaudio/fish-speech-1.5)) | Allowed | **Blocked** for v1.5 weights (non-commercial + ShareAlike). |
| **Meta MMS Urdu (`facebook/mms-tts-urd-script_arabic`)** | Apache-2.0 via `transformers` ([LICENSE](https://github.com/huggingface/transformers/blob/main/LICENSE)) | CC-BY-NC-4.0 ([Model Card](https://huggingface.co/facebook/mms-tts-urd-script_arabic)) | Allowed | **Blocked** (non-commercial). Must be swapped for a permissive Urdu base TTS if VoiceCity ever ships commercially. |
| **OpenVoice v2 (`myshell-ai/OpenVoice`)** | MIT ([LICENSE](https://github.com/myshell-ai/OpenVoice/blob/main/LICENSE)) | MIT ([OpenVoiceV2](https://huggingface.co/myshell-ai/OpenVoiceV2)) | Allowed | **Clear:** Permissive MIT for both code and tone-color converter weights. |
| **Indic Parler-TTS (`ai4bharat/indic-parler-tts`)** | Apache-2.0 ([parler-tts LICENSE](https://github.com/huggingface/parler-tts/blob/main/LICENSE)) | Apache-2.0 ([Model Card](https://huggingface.co/ai4bharat/indic-parler-tts)) | Allowed | **Clear** (if later evaluated as a commercial base speaker feeding OpenVoice v2). |

---

## 6. Consolidated Separation: Verified Facts vs. Assumptions vs. Unverified Claims

### Verified Facts
- Repository resides at `/root/2026-portfolio/voicecity`, remote `https://github.com/zakshub/voicecity.git`, branch `main`, baseline commit `9ac148b031e2dea935bbcda1c206dd547256eb66`.
- Current container is `aarch64` PRoot Debian 13 (11 GiB RAM / 2.6 GiB free, 19 GB disk free, no PCI/NVIDIA GPU, Python 3.13.13) — unsuitable for local ML inference.
- `app/main.py` truthfully reports `speech_generation: False`; `.gitignore` excludes audio, weights, and secrets.
- Code/doc discrepancies exist in `app/core/config.py` (unused `pydantic-settings`, missing `VOICECITY_TTS_PROVIDER`), `app/engine/base.py` (missing `prepare_voice`), and `README.md` (missing `scripts/`).
- Official license terms and Hugging Face checkpoint sizes for `F5-TTS-OpenBible-Urdu` (`5.37 GB`, `CC-BY-SA-4.0`), `XTTS-v2` (`~1.87 GB`, `CPML`), `Fish Speech 1.5` (`1.28 GB`, `CC-BY-NC-SA-4.0`, no Urdu listed), `MMS Urdu` (`~145 MB`, `CC-BY-NC-4.0`), and `OpenVoice v2` (`~131 MB`, `MIT`).

### Assumptions
- The target Linux Mint laptop uses `x86_64` architecture and will run an isolated Python 3.11 or 3.12 virtual environment for ML inference.
- The user's existing ~2-minute WAV recording contains at least one clean 5–10 second speech segment suitable for zero-shot conditioning (without requiring a new recording).
- Initial Phase 1 prototyping can prioritize personal local-use viability first while preserving adapter modularity in case commercial distribution is later chosen.

### Unverified Claims (Pending Phase 1 Empirical Testing)
- Actual target laptop CPU, RAM, GPU, VRAM, and free disk space.
- Exact VRAM, system RAM, Time-to-First-Audio (TTFA), and Real-Time Factor (RTF) of Candidate 1 (F5-TTS Urdu) and Candidate 4 (MMS Urdu + OpenVoice v2) on the user's laptop.
- Subjective Pakistani Urdu intelligibility, accent naturalness, voice similarity, and mixed Urdu-English code-switching quality for all candidates.
- Strictly offline (network-disconnected) execution of all candidates after initial weight caching (verifying no hidden Hugging Face, Vocos, or Whisper downloads occur at inference time).

---

## 7. Recommended Architecture Adjustments (Deferred Until Approval)

Do not implement these changes until Phase 0 is approved and Phase 1 confirms model viability:
1. **Complete `SpeechEngine` Protocol (`app/engine/base.py`):** Add `prepare_voice(...)`, `validate_reference_audio(...)`, and explicit capability/license/network metadata fields to match [`docs/ARCHITECTURE.md`](ARCHITECTURE.md).
2. **Align Settings (`app/core/config.py`):** Adopt `pydantic-settings` (already listed in `pyproject.toml`) and wire `VOICECITY_TTS_PROVIDER`.
3. **Reference Audio Preprocessor:** Because zero-shot models take 5–12s prompts (not 2 full minutes), add a local deterministic slicer/inspector (duration, sample rate, clipping, SNR check, and clean 5–10s clip extraction) so the existing 2-minute WAV works out of the box.
4. **Script/Language Router Layer:** Keep text normalization and language segmentation decoupled from the model adapter so mixed Urdu-English text can either pass natively (if supported) or route cleanly across language-specific base engines (Candidate 4).

---

## 8. Recommendation & Phase 1 Proof-of-Concept Plan (Not Started)

### Recommendation
**Run a limited local Phase 1 Proof-of-Concept experiment on the Linux Mint laptop** comparing two candidates — **Candidate 1 (`F5-TTS-OpenBible-Urdu`)** and **Candidate 4 (`Meta MMS Urdu + OpenVoice v2`)** — only **after** recording the laptop's hardware specs and receiving explicit approval.

- If the laptop has a **dedicated NVIDIA GPU (≥4–6 GB VRAM)**: test Candidate 1 first, then Candidate 4 for code-switching comparison.
- If the laptop is **CPU-only or integrated graphics**: test Candidate 4 first (lightweight `~276 MB` combined weights), and benchmark whether Candidate 1 (`5.37 GB` checkpoint) is even practical on CPU.

### Cheapest Next Experiment (Phase 1 Scope — Pending Approval)
1. Confirm Linux Mint hardware specs and free disk space.
2. Create an isolated Python 3.11/3.12 virtual environment on the laptop (never in this phone container).
3. Inspect the user's ~2-minute WAV locally (duration, sample rate, channels, clipping) and extract clean 6s and 10s reference clips + exact transcript (passing explicit `--ref_text` to avoid Whisper ASR downloads/VRAM spikes).
4. Run a minimal standalone evaluation script (no UI, no FastAPI changes) on a fixed 5-prompt test set:
   - Pure Pakistani Urdu (formal)
   - Pakistani proper nouns & place names (retroflexes/aspirates)
   - Pure English
   - Mixed Urdu-English code-switching
   - Numbers, dates, currency, and punctuation
5. Disconnect network and verify strictly offline inference; log TTFA, RTF, peak RAM/VRAM, disk footprint, and conduct a 1–5 blind listening review per [`docs/MODEL_EVALUATION.md`](MODEL_EVALUATION.md).

---

## 9. Risks, Open Decisions & Essential User Input Only

### Key Risks & Open Decisions
- **Hardware Gate:** Without a dedicated GPU on the Linux Mint laptop, diffusion/flow-matching models like F5-TTS may be too slow for interactive desktop use.
- **Commercial vs. Personal Licensing:** Non-commercial checkpoints (Meta MMS, Emilia base, Fish Speech 1.5) are acceptable for private personal use, but block commercial redistribution.
- **Urdu Code-Switching Gap:** Neither top candidate is verified for seamless single-pass Urdu+English script mixing; a language-routing preprocessor may be required.
- **F5-TTS Checkpoint Footprint:** `multilingual-tts/F5-TTS-OpenBible-Urdu` ships a `5.37 GB` training checkpoint (`model_last.pt`), requiring adequate disk space and RAM during loading.

### Essential User Input Needed Before Phase 1 Approval
1. **Linux Mint Hardware Output:** Paste the output of the diagnostic command from **Section 2.3** executed on the target Linux Mint laptop.
2. **Licensing Scope:** Is VoiceCity strictly for private personal use on your laptop right now, or must Phase 1 candidates already be cleared for commercial distribution?
3. **Approval Gate:** Confirm whether you approve proceeding to Phase 1 (and which candidate(s) you want included once hardware specs are known).
