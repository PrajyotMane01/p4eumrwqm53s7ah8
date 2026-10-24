# Wind Forecast Monitor

UK national wind generation: day-ahead forecasts vs actuals (Elexon BMRS), for purchase decisions in January 2026.

## Layout

| Path | Contents |
| --- | --- |
| `backend/` | FastAPI app (Python 3.12, managed with uv) |
| `backend/app/main.py` | App entry point and `/api/v1` routes |
| `backend/app/config.py` | Settings loaded from env / `.env` |
| `backend/app/db.py` | Async client for Cloudflare D1 (HTTP API) |
| `backend/tests/` | pytest tests |
| `frontend/` | React + TypeScript app (Vite) |
| `Docs/` | Problem statement and tech stack notes |

## Run locally

Backend:

```bash
cd backend
cp .env.example .env   # fill in Cloudflare D1 credentials (optional for now)
uv sync
uv run uvicorn app.main:app --reload --port 8000
uv run pytest          # tests
```

Frontend (proxies `/api` to the backend on port 8000):

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173
```
