# Wind Forecast Monitor

UK national wind generation: day-ahead forecasts vs actuals (Elexon BMRS), for purchase decisions in January 2026.

## Layout

| Path | Contents |
| --- | --- |
| `backend/` | FastAPI app (Python 3.12, managed with uv) |
| `backend/app/main.py` | App entry point and `/api/v1` routes |
| `backend/app/config.py` | Settings loaded from env / `.env` |
| `backend/app/db.py` | Database layer: local SQLite or Cloudflare D1 (same SQL) |
| `backend/app/ingest/` | Loads wind actuals (FUELHH) and forecasts (WINDFOR) from Elexon into the database |
| `backend/migrations/` | SQL schema, applied automatically by the loader |
| `backend/app/analysis/selection.py` | Picks the forecast available at the day-ahead decision cutoff (default 09:50 UK time on D-1) for each half-hour |
| `backend/app/wrangler_auth.py` | Local-only: reuse the Wrangler login to reach D1 |
| `backend/tests/` | pytest tests |
| `frontend/` | React + TypeScript app (Vite) |
| `Docs/` | Problem statement and tech stack notes |
| `compose.yaml` | Runs backend and frontend together in Docker |
| `backend/Dockerfile` | Backend image (uvicorn on port 8000) |
| `frontend/Dockerfile`, `frontend/nginx.conf` | Frontend image: static build served by nginx, `/api` proxied to the backend |

## Run with Docker

```bash
docker compose up --build
```

- App: http://localhost:8080
- API: http://localhost:8000/api/v1/health (docs at http://localhost:8000/docs)

Settings are read from `backend/.env` if it exists. Load data first (see below); the database file in `backend/data/` is shared with the container.

## Run locally without Docker

Backend:

```bash
cd backend
cp .env.example .env   # defaults to a local SQLite file
uv sync
uv run python -m app.ingest refresh   # load data from Elexon
uv run uvicorn app.main:app --reload --port 8000
uv run pytest          # tests
```

Frontend (proxies `/api` to the backend on port 8000):

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173
```

## Loading data

The app serves stored data rather than calling Elexon on every request: the January 2026 data is fixed, stored data is fast, and the app keeps working if Elexon is unavailable.

```bash
cd backend
uv run python -m app.ingest refresh                                  # default: target times 2026-01-01 to 2026-02-02
uv run python -m app.ingest refresh --start 2026-03-01 --end 2026-03-08  # any other range (end exclusive, UTC)
uv run python -m app.ingest migrate                                  # create tables only
```

Refresh is safe to re-run: rows are upserted, and each run is logged in `ingest_runs`. Forecast runs published up to 3 days before the range are included, so the earliest target days still have day-ahead forecasts.

## Database: local SQLite or Cloudflare D1

Set in `backend/.env` (see `.env.example`):

| Setting | Local file | Cloudflare D1 |
| --- | --- | --- |
| `DB_BACKEND` | `sqlite` | `d1` |
| Connection | `SQLITE_PATH` (default `data/wind.db`) | `CLOUDFLARE_ACCOUNT_ID`, `D1_DATABASE_ID` |
| Auth | none | `D1_AUTH=token` + `CLOUDFLARE_API_TOKEN` (deployed), or `D1_AUTH=wrangler` (local development: reuses `wrangler login`, renewed automatically) |

D1 is SQLite, so both use the same schema and queries. Loading January into D1 takes about 2.5 minutes, as rows are sent in batches over the D1 HTTP API.
