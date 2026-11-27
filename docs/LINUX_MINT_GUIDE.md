# VoiceCity — Linux Mint Installation & User Guide

VoiceCity runs completely on your own Linux Mint computer and opens in your web browser at `http://127.0.0.1:8765`. Your voice recordings, profiles, and generated speech never leave your computer.

---

## 1. Prerequisites on Linux Mint

Open the Linux Mint **Terminal** and install the standard system tools (including `ffmpeg` for optional MP3 downloads):

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip ffmpeg curl
```

---

## 2. Clone & Install VoiceCity

```bash
git clone https://github.com/zakshub/voicecity.git
cd voicecity
```

### Option A — Install VoiceCity with the Default Commercial Speech Engine (`indic_parler_openvoice`)
Supports **Urdu, English, and Mixed Urdu-English** using 100% commercially permissive weights (`Apache-2.0` + `MIT`):

```bash
bash scripts/install_linux_mint.sh --with-engine indic_parler_openvoice --device auto
```

*(Pass `--device cpu` if you want CPU-only PyTorch without CUDA libraries, or `--device cuda` if you have an NVIDIA GPU with proprietary drivers installed).*

### Option B — Install the Secondary Direct Urdu Engine (`f5_tts_urdu`)
Supports **Urdu only** (`MIT` code + `CC-BY-SA-4.0` weights):

```bash
bash scripts/install_linux_mint.sh --with-engine f5_tts_urdu --device auto
```

---

## 3. Download Local Model Weights (One-Time Setup)

Run the consent-driven downloader to cache the speech models locally into `./models/` so future speech generation works offline:

```bash
.venv/bin/python scripts/download_models.py --engine indic_parler_openvoice
```

*(Estimated download: ~4.2 GB; requires at least 10 GB free disk space. For `f5_tts_urdu`, download is ~5.5 GB).*

---

## 4. Starting & Stopping VoiceCity

- **Start VoiceCity** (starts local server on `127.0.0.1:8765` and opens your browser):
  ```bash
  bash scripts/start_voicecity.sh
  ```
- **Stop VoiceCity:**
  ```bash
  bash scripts/stop_voicecity.sh
  ```
- **Optional Applications Menu Shortcut:**
  ```bash
  sed "s|/REPLACE/WITH/PATH/TO/voicecity|$(pwd)|g" scripts/voicecity.desktop.template \
    > ~/.local/share/applications/voicecity.desktop
  ```

---

## 5. Adding Your Existing ~2-Minute WAV Recording & Creating a Profile

You do **not** need to record a new sample or manually trim your ~2-minute WAV file.

1. Open `http://127.0.0.1:8765` in Firefox or Chromium.
2. Click **Create Voice Profile** in the left navigation bar.
3. Enter a profile name (for example, `My Personal Voice`).
4. Click or drag-and-drop your existing ~2-minute `.wav` recording.
5. Keep the **Automatic Reference Segment Length** at `8.0s` (VoiceCity automatically finds the cleanest active speech window inside your recording, normalizes it to 24 kHz mono, and keeps your original WAV untouched).
6. Check the **Ownership Confirmation** box and click **Import & Inspect Recording**.
7. Listen to the **Prepared Reference Clip** on the right panel to confirm it sounds clear and unclipped.

---

## 6. Generating Urdu, English, and Mixed Speech

1. Click **Text to Speech Studio**.
2. Select your voice profile in **Voice Profile**.
3. Choose **Language Mode**:
   - **Urdu (اردو)** for Urdu script (automatically switches to right-to-left input).
   - **English** for English sentences.
   - **Mixed Urdu + English** for code-switched Pakistani speech (click **Inspect Language Segments** to preview how VoiceCity splits Urdu and English spans).
4. Adjust **Speaking Speed** (`0.6x–1.5x`) and **Delivery Style** (`Neutral`, `Clear`, `Warm`, `Calm`).
5. Click **Generate Speech**.
6. On the **Audio Preview** screen, play the result, compare previous attempts, and click **Download WAV** (or **Download MP3** when `ffmpeg` is installed).

---

## 7. Evaluating Pakistani Urdu Quality on Your Laptop

Before trusting any model for daily production use, run the repeatable 5-prompt listening benchmark with your own WAV recording:

```bash
.venv/bin/python scripts/poc_eval.py \
  --engine indic_parler_openvoice \
  --reference-wav /path/to/your_2min_voice.wav \
  --output-dir data/eval_runs
```

---

## 8. Backup, Restore & Privacy

- All personal data lives exclusively inside `./data/` (excluded from Git via `.gitignore`):
  - `data/voicecity.db` — profile metadata, generation history, and preferences
  - `data/voice_profiles/<id>/source_audio.wav` — your untouched original recording
  - `data/voice_profiles/<id>/reference_segment.wav` — auto-prepared 24 kHz reference clip
  - `data/generated/<profile-id>/<gen-id>.wav` — generated audio clips
- **Backup:** Copy the `data/` folder to an encrypted local drive while VoiceCity is stopped.
- **Restore:** Copy `data/` back into the VoiceCity directory and start the server.

---

## 9. Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| Studio says **Engine Not Installed** | PyTorch/engine packages or local model weights are missing | Run `bash scripts/install_linux_mint.sh --with-engine indic_parler_openvoice` and `.venv/bin/python scripts/download_models.py --engine indic_parler_openvoice` |
| **MP3 Unavailable** button is disabled | `ffmpeg` is not installed | Run `sudo apt install -y ffmpeg` and refresh VoiceCity |
| Generation is slow on CPU | No NVIDIA CUDA GPU available | Expected on CPU-only laptops; keep text clips concise (1–3 sentences per pass) |
| Upload rejected as invalid WAV | File is MP3/M4A renamed to `.wav`, compressed WAV, or silent | Convert to uncompressed PCM WAV: `ffmpeg -i input.m4a -ar 24000 -ac 1 output.wav` |
| Port 8765 already in use | Another process or previous instance is running | Run `bash scripts/stop_voicecity.sh` or set `VOICECITY_PORT=8766` in `.env` |
