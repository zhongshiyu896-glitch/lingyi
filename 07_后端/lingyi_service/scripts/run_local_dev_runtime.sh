#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

HOST="${LINGYI_LOCAL_DEV_HOST:-127.0.0.1}"
PORT="${LINGYI_LOCAL_DEV_PORT:-8000}"

if [[ "$HOST" != "127.0.0.1" || "$PORT" != "8000" ]]; then
  echo "[run_local_dev_runtime] 仅允许本地 127.0.0.1:8000，当前配置 host=$HOST port=$PORT" >&2
  exit 2
fi

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[run_local_dev_runtime] 检测到 $HOST:$PORT 已有 pre-existing 监听，跳过启动，不执行 kill。"
  exit 0
fi

if [[ -x ".venv/bin/uvicorn" ]]; then
  UVICORN_CMD=(".venv/bin/uvicorn")
elif command -v uvicorn >/dev/null 2>&1; then
  UVICORN_CMD=("uvicorn")
else
  UVICORN_CMD=("python3" "-m" "uvicorn")
fi

export LINGYI_ALLOW_DEV_AUTH=true

echo "[run_local_dev_runtime] 启动本地 dev runtime: $HOST:$PORT (LINGYI_ALLOW_DEV_AUTH=true)"
exec "${UVICORN_CMD[@]}" app.local_dev:app --host "$HOST" --port "$PORT"
