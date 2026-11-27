#!/usr/bin/env bash
# VoiceCity Linux Mint Installer
# Usage:
#   bash scripts/install_linux_mint.sh
#   bash scripts/install_linux_mint.sh --with-engine indic_parler_openvoice --device auto
#   bash scripts/install_linux_mint.sh --with-engine f5_tts_urdu --device cpu

set -euo pipefail

WITH_ENGINE=""
DEVICE="auto"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-engine)
      WITH_ENGINE="${2:-}"
      shift 2
      ;;
    --device)
      DEVICE="${2:-auto}"
      shift 2
      ;;
    -h|--help)
      echo "Usage: bash scripts/install_linux_mint.sh [--with-engine indic_parler_openvoice|f5_tts_urdu] [--device auto|cpu|cuda]"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

echo "=== VoiceCity Linux Mint Setup ==="
python3 scripts/hardware_probe.py

if [[ -n "$WITH_ENGINE" ]] && ( [[ -d "/data/data/com.termux" ]] || uname -r | grep -qi "proot" ); then
  echo "ERROR: Refusing to install heavyweight ML engine packages on Android/Termux PRoot." >&2
  exit 1
fi

PYTHON_BIN=""
for candidate in python3.12 python3.11 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PYTHON_BIN="$candidate"
    break
  fi
done

if [[ -z "$PYTHON_BIN" ]]; then
  echo "ERROR: Python 3.11+ is required. On Linux Mint run: sudo apt update && sudo apt install -y python3 python3-venv python3-pip" >&2
  exit 1
fi

echo "Creating virtual environment in $REPO_DIR/.venv using $PYTHON_BIN..."
"$PYTHON_BIN" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip wheel setuptools
python -m pip install -e ".[api]"

if [[ ! -f ".env" && -f ".env.example" ]]; then
  cp .env.example .env
  echo "Created default .env from .env.example (bound to 127.0.0.1, local-only)."
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "Note: ffmpeg is not installed. WAV works natively; install ffmpeg for MP3 export:"
  echo "  sudo apt update && sudo apt install -y ffmpeg"
fi

if [[ -n "$WITH_ENGINE" ]]; then
  if [[ "$DEVICE" == "auto" ]]; then
    if command -v nvidia-smi >/dev/null 2>&1; then
      DEVICE="cuda"
    else
      DEVICE="cpu"
    fi
  fi

  echo "Installing PyTorch ($DEVICE) and engine '$WITH_ENGINE'..."
  if [[ "$DEVICE" == "cpu" ]]; then
    python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
  else
    python -m pip install torch torchaudio
  fi

  case "$WITH_ENGINE" in
    indic_parler_openvoice)
      python -m pip install "transformers>=4.46" "accelerate>=0.34" "soundfile>=0.12" "huggingface_hub>=0.25"
      python -m pip install "git+https://github.com/huggingface/parler-tts.git"
      python -m pip install --no-deps "git+https://github.com/myshell-ai/OpenVoice.git"
      ;;
    f5_tts_urdu)
      python -m pip install "huggingface_hub>=0.25" "omegaconf>=2.3" "hydra-core>=1.3" "soundfile>=0.12"
      python -m pip install "git+https://github.com/SWivid/F5-TTS.git"
      ;;
    *)
      echo "ERROR: Unsupported engine '$WITH_ENGINE'. Choose indic_parler_openvoice or f5_tts_urdu." >&2
      exit 1
      ;;
  esac
fi

echo ""
echo "VoiceCity installation complete."
echo "Next steps:"
if [[ -n "$WITH_ENGINE" ]]; then
  echo "  1. Download local weights: .venv/bin/python scripts/download_models.py --engine $WITH_ENGINE"
  echo "  2. Launch VoiceCity:       bash scripts/start_voicecity.sh"
else
  echo "  1. Launch VoiceCity UI:    bash scripts/start_voicecity.sh"
  echo "  2. To enable local neural speech synthesis, re-run with:"
  echo "     bash scripts/install_linux_mint.sh --with-engine indic_parler_openvoice --device auto"
fi
