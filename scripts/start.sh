#!/usr/bin/env bash
# One-click local start: Docker postgres/redis + API + launcher + open UI.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# GUI / double-click shells often lack Homebrew / uv on PATH.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

log() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

if ! command -v docker >/dev/null 2>&1; then
  die "Docker CLI not found. Install/start Docker Desktop first."
fi

if ! docker info >/dev/null 2>&1; then
  die "Docker Desktop is not running (or not ready). Open it, wait until green, retry."
fi

if ! command -v uv >/dev/null 2>&1; then
  die "uv not found on PATH. Install: https://docs.astral.sh/uv/  then reopen Terminal."
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  log "Created .env from .env.example — set XAI_API_KEY before real LLM runs."
fi

log "→ uv sync"
uv sync

log "→ docker compose up (postgres, redis)"
docker compose up -d postgres redis

log "→ waiting for postgres"
for _ in $(seq 1 60); do
  if docker compose exec -T postgres pg_isready -U crypto -d crypto_intel >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

log "→ alembic upgrade"
uv run alembic upgrade head

start_api_if_needed() {
  if curl -sf "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    log "API already healthy on :8000"
    return 0
  fi
  if [[ -f .api.pid ]]; then
    old_pid="$(cat .api.pid 2>/dev/null || true)"
    if [[ -n "${old_pid}" ]] && kill -0 "${old_pid}" 2>/dev/null; then
      kill "${old_pid}" 2>/dev/null || true
      sleep 1
    fi
    rm -f .api.pid
  fi
  log "→ starting API on :8000"
  nohup uv run uvicorn crypto_intel.api.app:app --host 127.0.0.1 --port 8000 \
    >.api.log 2>&1 &
  echo $! >.api.pid
}

start_launcher_if_needed() {
  if curl -sf "http://127.0.0.1:7911/status" >/dev/null 2>&1; then
    log "Launcher already healthy on :7911"
    return 0
  fi
  if [[ -f .launcher.pid ]]; then
    old_pid="$(cat .launcher.pid 2>/dev/null || true)"
    if [[ -n "${old_pid}" ]] && kill -0 "${old_pid}" 2>/dev/null; then
      kill "${old_pid}" 2>/dev/null || true
      sleep 1
    fi
    rm -f .launcher.pid
  fi
  log "→ starting launcher on :7911"
  nohup uv run python scripts/local_launcher.py >.launcher.log 2>&1 &
  echo $! >.launcher.pid
}

wait_http() {
  local url="$1"
  local name="$2"
  local seconds="${3:-90}"
  log "→ waiting for ${name} (${url})"
  for _ in $(seq 1 "${seconds}"); do
    if curl -sf "${url}" >/dev/null 2>&1; then
      log "✓ ${name} is up"
      return 0
    fi
    sleep 1
  done
  die "${name} did not become ready. See logs in project root (.api.log / .launcher.log)."
}

start_api_if_needed
start_launcher_if_needed
wait_http "http://127.0.0.1:8000/health" "API" 90
wait_http "http://127.0.0.1:7911/status" "Launcher" 90

UI="http://127.0.0.1:8000/"
if command -v open >/dev/null 2>&1; then
  open "$UI"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$UI"
else
  log "Open ${UI} in your browser"
fi

log ""
log "Ready: ${UI}"
log "Launcher status: http://127.0.0.1:7911/status"
log "UI button 'Start local stack' works while launcher is running."
