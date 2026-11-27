#!/usr/bin/env bash
# VoiceCity Phase 1 Isolated ML Proof-of-Concept Environment Setup (Linux Mint)
# Refuses to install heavyweight ML packages on Android/Termux PRoot environments.

set -euo pipefail

ENGINE="${1:-indic_parler_openvoice}"
DEVICE="${2:-auto}"
VENV_DIR="${VOICECITY_POC_VENV:-.venv-poc}"

if [[ -d "/data/data/com.termux" ]] || uname -r | grep -qi "proot"; then
  echo "ERROR: Detected Android/Termux PRoot environment." >&2
  echo "Do not install PyTorch or multi-GB speech checkpoints on the phone." >&2
  echo "Run this script on your target Linux Mint laptop instead." >&2
  exit 1
fi

echo "=== VoiceCity Hardware Probe ==="
python3 scripts/hardware_probe.py

PYTHON_BIN=""
for candidate in python3.12 python3.11 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PYTHON_BIN="$candidate"
    break
  fi
done

if [[ -z "$PYTHON_BIN" ]]; then
  echo "ERROR: Python 3.11+ is required." >&2
  exit 1
fi

echo "Using Python interpreter: $PYTHON_BIN ($("$PYTHON_BIN" --version))"
"$PYTHON_BIN" -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip wheel setuptools
python -m pip install -e ".[dev,api]"

if [[ "$DEVICE" == "auto" ]]; then
  if command -v nvidia-smi >/dev/null 2>&1; then
    DEVICE="cuda"
  else
    DEVICE="cpu"
  fi
fi

echo "Installing PyTorch for device mode: $DEVICE"
if [[ "$DEVICE" == "cpu" ]]; then
  python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
else
  python -m pip install torch torchaudio
fi

case "$ENGINE" in
  indic_parler_openvoice)
    echo "Installing Indic Parler-TTS (Apache-2.0) + OpenVoice v2 (MIT) dependencies..."
    python -m pip install "transformers>=4.46" "accelerate>=0.34" "soundfile>=0.12" "huggingface_hub>=0.25"
    python -m pip install "git+https://github.com/huggingface/parler-tts.git"
    python -m pip install --no-deps "git+https://github.com/myshell-ai/OpenVoice.git"
    echo "Optional fast English base (Kokoro-82M Apache-2.0): pip install kokoro"
    ;;
  f5_tts_urdu)
    echo "Installing F5-TTS (MIT code; OpenBible Urdu weights are CC-BY-SA-4.0)..."
    python -m pip install "huggingface_hub>=0.25" "omegaconf>=2.3" "hydra-core>=1.3" "soundfile>=0.12"
    python -m pip install "git+https://github.com/SWivid/F5-TTS.git"
    ;;
  *)
    echo "ERROR: Unsupported engine '$ENGINE'. Supported: indic_parler_openvoice, f5_tts_urdu" >&2
    exit 1
    ;;
esac

echo ""
echo "Isolated PoC environment ready at: $VENV_DIR"
echo "Activate with: source $VENV_DIR/bin/activate"
echo "Run evaluation dry-run: python scripts/poc_eval.py --engine $ENGINE --dry-run"
