#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
DB="$ROOT/db"

# ── colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

log()  { echo -e "${CYAN}${BOLD}[dev]${RESET} $*"; }
ok()   { echo -e "${GREEN}✓${RESET} $*"; }
warn() { echo -e "${YELLOW}⚠${RESET}  $*"; }
die()  { echo -e "${RED}✗${RESET} $*" >&2; exit 1; }

# ── cleanup on exit ───────────────────────────────────────────────────────────
PIDS=()
cleanup() {
  echo ""
  log "Shutting down…"
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  ok "All processes stopped."
}
trap cleanup EXIT INT TERM

# ── checks ────────────────────────────────────────────────────────────────────
command -v docker   >/dev/null 2>&1 || die "docker not found"
command -v python3  >/dev/null 2>&1 || die "python3 not found"
command -v pnpm     >/dev/null 2>&1 || die "pnpm not found (run: npm i -g pnpm)"

# ── env file ──────────────────────────────────────────────────────────────────
if [ ! -f "$BACKEND/.env" ]; then
  warn "backend/.env not found — copying from .env.example"
  cp "$ROOT/.env.example" "$BACKEND/.env"
  echo ""
  echo -e "${YELLOW}${BOLD}ACTION REQUIRED:${RESET} Edit ${BOLD}backend/.env${RESET} and set:"
  echo "  ANTHROPIC_API_KEY=sk-ant-..."
  echo "  JWT_SECRET=<any long random string>"
  echo ""
  read -r -p "Press Enter once you've saved backend/.env, or Ctrl+C to abort… "
fi

export $(grep -v '^#' "$BACKEND/.env" | xargs) 2>/dev/null || true

# ── 1. docker infrastructure ──────────────────────────────────────────────────
log "Starting Postgres + Redis…"
docker-compose -f "$ROOT/docker-compose.yml" up -d
ok "Infrastructure up"

# ── 2. wait for postgres ──────────────────────────────────────────────────────
log "Waiting for Postgres to be ready…"
for i in $(seq 1 20); do
  docker-compose -f "$ROOT/docker-compose.yml" exec -T postgres \
    pg_isready -U cookit -q 2>/dev/null && break
  sleep 1
done
ok "Postgres ready"

# ── 3. python venv ────────────────────────────────────────────────────────────
if [ ! -d "$BACKEND/.venv" ]; then
  log "Creating Python virtual environment…"
  python3 -m venv "$BACKEND/.venv"
fi
source "$BACKEND/.venv/bin/activate"

log "Installing Python dependencies…"
pip install -q -r "$BACKEND/requirements.txt"
ok "Python deps installed"

# ── 4. alembic migration ──────────────────────────────────────────────────────
log "Running database migrations…"
(
  cd "$DB"
  alembic upgrade head
)
ok "Migrations applied"

# ── 5. seed condiments ────────────────────────────────────────────────────────
log "Seeding condiments catalogue…"
(
  cd "$BACKEND"
  python -m scripts.seed_condiments
)
ok "Condiments seeded"

# ── 6. frontend deps ──────────────────────────────────────────────────────────
if [ ! -d "$FRONTEND/node_modules" ]; then
  log "Installing frontend dependencies…"
  (cd "$FRONTEND" && pnpm install)
  ok "Frontend deps installed"
fi

if [ ! -f "$FRONTEND/.env.local" ]; then
  echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > "$FRONTEND/.env.local"
fi

# ── 7. start services ─────────────────────────────────────────────────────────
mkdir -p "$ROOT/logs"

log "Starting backend (port 8000)…"
(
  cd "$BACKEND"
  uvicorn app.main:app --reload --port 8000
) > "$ROOT/logs/backend.log" 2>&1 &
PIDS+=($!)

log "Starting frontend (port 3000)…"
(
  cd "$FRONTEND"
  pnpm dev
) > "$ROOT/logs/frontend.log" 2>&1 &
PIDS+=($!)

# ── 8. wait for backend health ────────────────────────────────────────────────
log "Waiting for backend to be healthy…"
for i in $(seq 1 30); do
  curl -sf http://localhost:8000/health >/dev/null 2>&1 && break
  sleep 1
done

echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}${BOLD}  Cookit is running!${RESET}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "  Frontend  →  ${BOLD}http://localhost:3000${RESET}"
echo -e "  API       →  ${BOLD}http://localhost:8000${RESET}"
echo -e "  API docs  →  ${BOLD}http://localhost:8000/docs${RESET}"
echo -e "  Logs      →  ${BOLD}$ROOT/logs/${RESET}"
echo ""
echo -e "  Press ${BOLD}Ctrl+C${RESET} to stop all services."
echo ""

# ── tail logs ─────────────────────────────────────────────────────────────────
tail -f "$ROOT/logs/backend.log" "$ROOT/logs/frontend.log" &
PIDS+=($!)

wait
