#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PID=""
FRONTEND_PID=""

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "缺少命令：$1" >&2
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

require_command "uv" "请先安装 uv，然后在 backend 目录执行 uv sync --all-groups。"
require_command "npm" "请先安装 Node.js 和 npm，然后在 frontend 目录执行 npm ci。"

if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  echo "前端依赖尚未安装。请先执行：" >&2
  echo "  cd \"$ROOT_DIR/frontend\" && npm ci" >&2
  exit 1
fi

export CHAN_QUANT_DATA_SOURCE="${CHAN_QUANT_DATA_SOURCE:-sina}"
export CHAN_QUANT_SINA_DATALEN="${CHAN_QUANT_SINA_DATALEN:-2000}"
export CHAN_QUANT_SYMBOL="${CHAN_QUANT_SYMBOL:-000001.SZ}"
export CHAN_QUANT_INSTRUMENT_NAME="${CHAN_QUANT_INSTRUMENT_NAME:-平安银行}"

echo "正在启动 Chan Quant…"
echo "数据源：$CHAN_QUANT_DATA_SOURCE"
echo "页面：http://127.0.0.1:5173/?symbol=$CHAN_QUANT_SYMBOL"
echo "按 Ctrl+C 可同时关闭前后端。"

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
    echo "后端进程已退出，正在关闭前端。" >&2
    break
  fi

  if ! kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
    set +e
    wait "$FRONTEND_PID"
    exit_code=$?
    set -e
    echo "前端进程已退出，正在关闭后端。" >&2
    break
  fi

  sleep 1
done

exit "$exit_code"
