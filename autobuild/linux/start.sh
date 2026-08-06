#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

command -v node >/dev/null 2>&1 || { echo "Node.js not found. Install it from https://nodejs.org"; exit 1; }

if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

cd "$FRONTEND_DIR"
npm ci
npm run build

cd "$BACKEND_DIR"
uv sync
uv run python -m playwright install --with-deps chromium || true

if [ ! -f "$BACKEND_DIR/.env" ] && [ -f "$BACKEND_DIR/.env.example" ]; then
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
fi

export ARESES_DATABASE_URL="${ARESES_DATABASE_URL:-sqlite+aiosqlite:///./data/areses.db}"
export ARESES_LOCAL_MODE="${ARESES_LOCAL_MODE:-true}"
mkdir -p data

uv run alembic upgrade head

echo ""
echo "ARESES is starting."
echo "Open your browser to: http://localhost:8000"
echo "(The server binds to 0.0.0.0 so other devices on your network can also reach it"
echo " at http://<this-machine's-LAN-IP>:8000 -- but push notifications and other"
echo " browser security features only work over http://localhost or HTTPS.)"
echo ""

uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
