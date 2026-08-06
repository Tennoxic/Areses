# ARESES

A self-hosted RSS/Atom news aggregator for a LAN. Runs on one machine (a spare PC, a home server, a Raspberry Pi), everyone on the network reads from it in a browser. No cloud account, no tracking, no ads.

## Features

- Standard feed subscriptions (RSS/Atom) with folders, drag-and-drop organization, and OPML import/export
- Full-text search with operators: `intitle:`, `intext:`, `inurl:`, `author:`, `f:`/`c:` (feed/category filters), `date:`/`pubdate:`/`mdate:`, boolean `AND`/`OR`/`NOT`, quoted phrases, and saved searches
- Unread / Starred / Read later / Summaries views, keyboard shortcuts, a distraction-free reading pane
- Optional AI-generated article summaries (Anthropic, OpenAI, Gemini, Groq, or a local Ollama instance) — bring your own API key, admin-configured, applies to all users
- Web Push notifications per feed
- Multi-user with per-user read state; the first account created becomes the admin
- Data export/import (JSON) and automatic encrypted-at-rest database backups
- English and Turkish UI

## Architecture

```
backend/    FastAPI + SQLAlchemy (async) + SQLite, Alembic migrations
frontend/   React + Vite, no external CSS framework
autobuild/  no-Docker startup scripts (Linux/macOS and Windows)
```

The backend serves the built frontend directly (`frontend/dist`) from the same origin and port, so there's exactly one URL to remember and no CORS to configure for normal use.

Secrets (SMTP password, AI provider API key, VAPID push key, per-feed HTTP auth passwords) are encrypted at rest. Outbound feed/article fetches are checked against a private-IP/loopback blocklist before every request (SSRF guard). Search input is checked for catastrophic-backtracking patterns before being turned into a query. See `backend/.env.example` for the handful of settings that affect any of this.

## Running it

### Option A — Docker

```
docker compose up -d
```

Open `http://localhost:8000`. Data persists in the `areses-data` volume. See the comments in `docker-compose.yml` before exposing this beyond your LAN (`ARESES_LOCAL_MODE`, `ARESES_BASE_URL`).

### Option B — no Docker

Requires [Node.js](https://nodejs.org) and [uv](https://astral.sh/uv). If you don't have `uv`, the scripts below install it for you.

```
# Linux / macOS
./autobuild/linux/start.sh

# Windows
autobuild\windows\start.bat
```

This builds the frontend, runs database migrations, and starts the server on `http://localhost:8000`.

> The server binds to `0.0.0.0` so other devices on your network can reach it too, at `http://<this-machine's-LAN-IP>:8000`. Open the app itself at `http://localhost:8000` — Web Push notifications and other browser security features only work over `localhost` or real HTTPS, not over a plain LAN IP.

### First run

Register the first account in the UI — it's made admin automatically. From Settings → Admin you can promote/demote other users, configure the AI provider, SMTP, and backups.

## CLI

```
uv run areses-cli <command>
```

`create-admin`, `list-users`, `delete-user`, `reset-password`, `backup`, `restore`, `list-feeds`, `refresh-feed`, `refresh-all`, `backfill-security`. Run `uv run areses-cli <command> --help` for arguments.

## Development

```
# backend
cd backend
uv sync --extra dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# frontend (separate terminal)
cd frontend
npm install
npm run dev
```

The dev frontend runs on `http://localhost:5173` and talks to the backend on `:8000` (see `frontend/.env.development`).

```
cd backend && uv run pytest
cd frontend && npm run lint
```

## Configuration

Everything is optional; ARESES runs zero-config with sensible defaults for LAN use. See `backend/.env.example` for the full list (`ARESES_DATABASE_URL`, `ARESES_LOCAL_MODE`, `ARESES_BASE_URL`, `ARESES_SECRET_KEY`, `ARESES_CORS_ORIGINS`).

## License

MIT — see [LICENSE](LICENSE).
