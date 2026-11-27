#!/usr/bin/env bash
# Stop the local VoiceCity background server cleanly.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${REPO_DIR}/data/voicecity.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "VoiceCity is not running (no PID file found)."
  exit 0
fi

PID="$(cat "$PID_FILE" 2>/dev/null || true)"
if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  for _ in $(seq 1 10); do
    if ! kill -0 "$PID" 2>/dev/null; then
      break
    fi
    sleep 0.3
  done
  echo "VoiceCity stopped (PID $PID)."
else
  echo "Removed stale VoiceCity PID file."
fi

rm -f "$PID_FILE"
