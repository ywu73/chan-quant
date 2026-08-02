#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PID=""
FRONTEND_PID=""

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing command: $1" >&2
    echo "$2" >&2
    exit 1
  fi
}

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM

  for pid in "$BACKEND_PID" "$FRONTEND_PID"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" >/dev/null 2>&1 || true
    fi
  done

  for pid in "$BACKEND_PID" "$FRONTEND_PID"; do
    if [[ -n "$pid" ]]; then
      wait "$pid" >/dev/null 2>&1 || true
    fi
  done

  exit "$exit_code"
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

require_command "uv" "Install uv, then run 'uv sync --all-groups' in the backend directory."
require_command "npm" "Install Node.js and npm, then run 'npm ci' in the frontend directory."

if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  echo "Frontend dependencies are not installed. Run:" >&2
  echo "  cd \"$ROOT_DIR/frontend\" && npm ci" >&2
  exit 1
fi

export CHAN_QUANT_DATA_SOURCE="${CHAN_QUANT_DATA_SOURCE:-sina}"
export CHAN_QUANT_SINA_DATALEN="${CHAN_QUANT_SINA_DATALEN:-2000}"

echo "Starting Chan Quant..."
echo "Data source: $CHAN_QUANT_DATA_SOURCE"
echo "Market breadth: remote SSE/SZSE universe + Sina quotes"
echo "Page: http://127.0.0.1:5173/"
echo "Press Ctrl+C to stop both backend and frontend."

(
  cd "$ROOT_DIR/backend"
  exec uv run uvicorn chan_quant.api.app:app --host 127.0.0.1 --port 8000
) &
BACKEND_PID=$!

(
  cd "$ROOT_DIR/frontend"
  exec npm run dev -- --host 127.0.0.1 --port 5173
) &
FRONTEND_PID=$!

exit_code=0
while true; do
  if ! kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    set +e
    wait "$BACKEND_PID"
    exit_code=$?
    set -e
    echo "Backend process exited; stopping frontend." >&2
    break
  fi

  if ! kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
    set +e
    wait "$FRONTEND_PID"
    exit_code=$?
    set -e
    echo "Frontend process exited; stopping backend." >&2
    break
  fi

  sleep 1
done

exit "$exit_code"
