#!/usr/bin/env bash
# VoiceCity Linux Mint Installer
# Supported --with-engine values:
#   dual_cloning                (F5-TTS Urdu [CC-BY-SA-4.0] + Qwen3-TTS English [Apache-2.0])
#   f5_tts_urdu                 (Urdu reference voice cloning ONLY — CC-BY-SA-4.0 optional)
#   qwen3_tts_en                (English reference voice cloning ONLY — Apache-2.0)
#   indic_parler_tts            (Standard Urdu/English TTS ONLY — NOT voice cloning, Apache-2.0)
#   openvoice_v2_converter      (Audio-to-audio voice conversion ONLY — MIT, Urdu not native)
#   experimental_parler_openvoice (EXPERIMENTAL cross-linguistic conversion)

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
      echo "Usage: bash scripts/install_linux_mint.sh [--with-engine dual_cloning|f5_tts_urdu|qwen3_tts_en|indic_parler_tts|openvoice_v2_converter|experimental_parler_openvoice] [--device auto|cpu|cuda]"
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
  echo "ERROR: Python 3.11+ is required. Run: sudo apt update && sudo apt install -y python3 python3-venv python3-pip" >&2
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

install_f5_urdu() {
  python -m pip install "huggingface_hub>=0.25" "omegaconf>=2.3" "hydra-core>=1.3" "soundfile>=0.12"
  python -m pip install "git+https://github.com/SWivid/F5-TTS.git"
}

install_qwen3_en() {
  python -m pip install "huggingface_hub>=0.25" "soundfile>=0.12" "qwen-tts"
}

install_indic_parler() {
  python -m pip install "transformers>=4.46" "accelerate>=0.34" "soundfile>=0.12" "huggingface_hub>=0.25"
  python -m pip install "git+https://github.com/huggingface/parler-tts.git"
}

install_openvoice() {
  python -m pip install "huggingface_hub>=0.25" "soundfile>=0.12"
  python -m pip install --no-deps "git+https://github.com/myshell-ai/OpenVoice.git"
}

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
    dual_cloning)
      install_f5_urdu
      install_qwen3_en
      ;;
    f5_tts_urdu)
      install_f5_urdu
      ;;
    qwen3_tts_en)
      install_qwen3_en
      ;;
    indic_parler_tts)
      install_indic_parler
      ;;
    openvoice_v2_converter)
      install_openvoice
      ;;
    experimental_parler_openvoice)
      install_indic_parler
      install_openvoice
      ;;
    *)
      echo "ERROR: Unsupported engine '$WITH_ENGINE'." >&2
      exit 1
      ;;
  esac
fi

echo ""
echo "VoiceCity installation complete."
if [[ -n "$WITH_ENGINE" ]]; then
  echo "Next steps:"
  if [[ "$WITH_ENGINE" == "experimental_parler_openvoice" ]]; then
    echo "  1. Download weights: .venv/bin/python scripts/download_models.py --engine indic_parler_tts"
    echo "                       .venv/bin/python scripts/download_models.py --engine openvoice_v2_converter"
  else
    echo "  1. Download weights: .venv/bin/python scripts/download_models.py --engine $WITH_ENGINE"
  fi
  echo "  2. Launch VoiceCity: bash scripts/start_voicecity.sh"
else
  echo "Launch UI now: bash scripts/start_voicecity.sh"
fi
