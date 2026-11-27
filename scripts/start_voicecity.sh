#!/usr/bin/env bash
# Start VoiceCity locally bound strictly to 127.0.0.1 and open the local browser UI.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

HOST="${VOICECITY_HOST:-127.0.0.1}"
PORT="${VOICECITY_PORT:-8765}"
PID_FILE="${REPO_DIR}/data/voicecity.pid"
LOG_FILE="${REPO_DIR}/logs/voicecity.log"

mkdir -p "${REPO_DIR}/data" "${REPO_DIR}/logs"

if [[ -f "$PID_FILE" ]]; then
  OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$OLD_PID" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "VoiceCity is already running (PID $OLD_PID) at http://${HOST}:${PORT}"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

if [[ ! -x "${REPO_DIR}/.venv/bin/uvicorn" ]]; then
  echo "ERROR: .venv not found. Run 'bash scripts/install_linux_mint.sh' first." >&2
  exit 1
fi

echo "Starting VoiceCity on http://${HOST}:${PORT} (local loopback only)..."
nohup "${REPO_DIR}/.venv/bin/uvicorn" app.main:app --host "$HOST" --port "$PORT" >"$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" >"$PID_FILE"

for _ in $(seq 1 20); do
  if curl -fsS "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
    echo "VoiceCity is running (PID $SERVER_PID) at http://${HOST}:${PORT}"
    if [[ "${1:-}" != "--no-browser" ]] && [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]] && command -v xdg-open >/dev/null 2>&1; then
      xdg-open "http://${HOST}:${PORT}" >/dev/null 2>&1 || true
    fi
    exit 0
  fi
  sleep 0.5
done

echo "WARNING: Server started (PID $SERVER_PID) but did not respond to /health within 10s."
echo "Check logs at: $LOG_FILE"
exit 1
