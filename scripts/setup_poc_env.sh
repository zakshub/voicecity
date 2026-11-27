#!/usr/bin/env bash
# Isolated Phase 1 PoC environment setup on Linux Mint (delegates to install_linux_mint.sh logic).

set -euo pipefail

ENGINE="${1:-dual_cloning}"
DEVICE="${2:-auto}"

if [[ -d "/data/data/com.termux" ]] || uname -r | grep -qi "proot"; then
  echo "ERROR: Detected Android/Termux PRoot environment. Run this script on Linux Mint." >&2
  exit 1
fi

bash scripts/install_linux_mint.sh --with-engine "$ENGINE" --device "$DEVICE"
echo "Run dry-run evaluation: .venv/bin/python scripts/poc_eval.py --engine f5_tts_urdu --dry-run"
