# VoiceCity — Linux Mint Installation & User Guide

VoiceCity runs completely on your own Linux Mint laptop and opens locally at `http://127.0.0.1:8765`. Your voice recordings, profiles, and generated audio stay strictly on your machine.

---

## 1. System Prerequisites on Linux Mint

Open **Terminal** on Linux Mint and run:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip ffmpeg curl
```

*(Checking hardware first: `python3 scripts/hardware_probe.py` prints your exact CPU, RAM, disk, and GPU/VRAM without downloading any ML packages.)*

---

## 2. Clone & Choose Which Speech Engine(s) to Install

```bash
git clone https://github.com/zakshub/voicecity.git
cd voicecity
```

VoiceCity strictly separates **Reference-Audio Voice Cloning** from **Standard TTS** and **Experimental Voice Conversion**:

### Recommended for Genuine Personal Voice Cloning (Urdu + English): `dual_cloning`
Installs BOTH specialist reference-audio cloning engines:
- **Urdu Voice Cloning:** `f5_tts_urdu` (`F5-TTS-OpenBible-Urdu`, optional **CC-BY-SA-4.0** ShareAlike, requires reference transcript)
- **English Voice Cloning:** `qwen3_tts_en` (`Qwen3-TTS-12Hz-0.6B-Base`, permissive **Apache-2.0**)

```bash
bash scripts/install_linux_mint.sh --with-engine dual_cloning --device auto
```

### Other Focused Installation Options
- **English Voice Cloning Only (100% Apache-2.0 permissive):**
  ```bash
  bash scripts/install_linux_mint.sh --with-engine qwen3_tts_en --device auto
  ```
- **Urdu Voice Cloning Only (CC-BY-SA-4.0 optional):**
  ```bash
  bash scripts/install_linux_mint.sh --with-engine f5_tts_urdu --device auto
  ```
- **Experimental Cross-Linguistic Conversion (`Indic Parler-TTS` + `OpenVoice v2`, Apache-2.0 + MIT — NOTE: Urdu is NOT native to OpenVoice v2):**
  ```bash
  bash scripts/install_linux_mint.sh --with-engine experimental_parler_openvoice --device auto
  ```

*(Replace `--device auto` with `--device cpu` if your laptop has no NVIDIA GPU, or `--device cuda` for NVIDIA CUDA).*

---

## 3. Download & Verify Local Model Weights (One-Time Setup)

Download weights directly into `./models/` (prompts for explicit license acknowledgment and checks free disk space):

```bash
.venv/bin/python scripts/download_models.py --engine dual_cloning
```

To verify cached local model files offline at any time (no network access):
```bash
.venv/bin/python scripts/download_models.py --engine dual_cloning --verify-only
```

---

## 4. Starting & Stopping VoiceCity

- **Start locally (`127.0.0.1:8765`):**
  ```bash
  bash scripts/start_voicecity.sh
  ```
- **Stop cleanly:**
  ```bash
  bash scripts/stop_voicecity.sh
  ```
- **Optional Applications Menu Shortcut:**
  ```bash
  sed "s|/REPLACE/WITH/PATH/TO/voicecity|$(pwd)|g" scripts/voicecity.desktop.template \
    > ~/.local/share/applications/voicecity.desktop
  ```

---

## 5. Importing Your Existing ~2-Minute WAV & Setting the Reference Transcript

1. Open **http://127.0.0.1:8765** → click **Create Voice Profile**.
2. Drag and drop your existing ~2-minute `.wav` file (your original recording is preserved untouched inside `./data/voice_profiles/<id>/source_audio.wav`).
3. Keep **Automatic Reference Segment Length** at `8.0s` — VoiceCity automatically extracts the cleanest active speech window and normalizes it to 24 kHz mono.
4. Check the **Ownership Confirmation** box and click **Import & Inspect Recording**.
5. Open **Voice Library**, listen to the **Prepared Reference Clip**, and enter the exact spoken words of that 8-second clip in **Reference Clip Transcript** → click **Save Transcript**. *(Required for strict offline F5-TTS Urdu cloning so no Whisper ASR download is triggered; also improves Qwen3-TTS English cloning accuracy).*

---

## 6. Generating Speech & Monitoring Progress

1. Click **Text to Speech Studio** and select your voice profile.
2. Check the **Active Speech Engine** panel to confirm which languages (`ur`, `en`, `mixed`) are ready.
3. Enter Urdu, English, or mixed text; click **Inspect Language Segments** to see detected spans and pronunciation hints (e.g., abbreviations like `PKR` or `Rs.`).
4. Click **Queue Speech Generation**. You can monitor live progress (`0–100%`) or click **Cancel** at any time.
5. Preview and compare clips on **Audio Preview**, and export as **WAV** (or **MP3** when `ffmpeg` is installed).

---

## 7. Backup & Troubleshooting

- **Backup:** Stop VoiceCity and copy `./data/` to an encrypted drive. Never commit `./data/` or `./models/` to Git.
- **Note on Phone/Termux vs. Linux Mint:** The Pixel 7 Pro Termux/PRoot environment uses Android `aarch64` Python 3.13 SOABI where Rust-compiled wheels (`ruff`, `pydantic-core`) and PyTorch CUDA wheels are unavailable. On standard `x86_64` Linux Mint with Python 3.11 or 3.12, prebuilt binary wheels install cleanly.
