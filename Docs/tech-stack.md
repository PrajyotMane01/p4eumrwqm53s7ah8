# Wind Forecast App — Tech Stack

The stack is FastAPI + pandas on the backend and React + TypeScript on the frontend. It is deployed on Vercel: the React build is served as a static site, and FastAPI runs as a Python serverless function. Docker is used to run the whole app locally with one command. Each choice either meets a hard requirement of the challenge or shows a skill the Gridbricks job description asks for.

## Context

- **The challenge:** a web app that shows UK national wind forecasts as they stood at the day-ahead decision time, and measures their error against actual output. The data is Elexon BMRS FUELHH and WINDFOR, for decisions made in January 2026.
- **Hard requirements:** a React frontend, a Python backend, Docker, and deployment on Vercel or Heroku.
- **Time left:** 8 of the 16 hours. The stack favours tools that are quick to set up and keep the demo reliable.
- **Principles:** get the core logic right and tested, keep the parts few, and show good engineering habits without over-engineering.

## Tech stack

| Layer | Choice | Why we use it | JD requirement it shows |
| --- | --- | --- | --- |
| Backend framework | FastAPI (async), httpx for Elexon calls | Async I/O for API fetches, automatic OpenAPI docs, fast to build | "Strong Python FastAPI or an equivalent async framework" |
| API design | Pydantic models, versioned routes (`/api/v1/...`) | Typed request and response contracts; versioning lets the API change without breaking clients | "Design an API that ages well" |
| Data and analysis | pandas + NumPy | Joins actuals to forecasts, applies the decision-cutoff rule, computes error metrics in a few lines | Scientific or numerical computing (nice to have) |
| Storage / cache | CSV or SQLite snapshot of January data, committed to the repo, refreshed by a script | The dataset is small; a snapshot keeps the demo working if Elexon is slow or down. Avoids pyarrow, which is too large for a Vercel function | Engineering judgement, avoiding over-engineering |
| Frontend | React + TypeScript + Vite | Required by the brief; TypeScript catches errors early; Vite builds fast | "Strong React" |
| Server state | TanStack Query | Caching, loading and error states without hand-written boilerplate | Complex client-side state |
| UI state | URL query parameters (date range, cutoff, horizon) | Every view can be shared and bookmarked; no extra state library needed | Interfaces beyond CRUD forms |
| Charts | ECharts, or Visx/D3 if time allows | Interactive actual-vs-forecast chart with error band, zoom and linked histogram | Custom visualisation (nice to have) |
| Backend tests | pytest | Covers forecast selection, cutoff edge cases, missing data and metrics | "Real rigour… edge cases" |
| Frontend tests | Vitest + React Testing Library | A few tests on key components and data handling | "You write tests" |
| Code quality | ruff, ESLint, Prettier, pre-commit | Consistent style and lint checks on every commit | Engineering discipline |
| CI | GitHub Actions | Lint, test and Docker build on every push | "CI… best practices as habit" |
| Containers | Docker multi-stage build + docker-compose | Required by the brief; one command runs the whole app locally | Engineering discipline |
| Deployment | Vercel (static React + FastAPI Python function) | Free Hobby tier, deploys from GitHub on every push, one URL for app and API | Ownership: shipping a working product |
| Observability | Structured logging, `/api/v1/health` endpoint, request timing | Shows what the app is doing; Vercel's function logs collect the output | "Observability" |
| Docs | README, architecture diagram, decision notes | Explains how to run it and why each assumption was made | Documentation; "chase down ambiguity" |

## What we leave out

The data is a few tens of thousands of rows, so anything built for scale would add setup time without adding value.

| Left out | Why | When it would make sense |
| --- | --- | --- |
| Celery / Ray / Dask | One month of data loads in seconds; no background jobs needed | Scheduled ingestion of many datasets in production |
| Kubernetes | One app is enough for a demo | Multiple services at real traffic |
| PostgreSQL server | A file snapshot is enough and needs no hosting | Many users, frequent writes, longer history |
| LLM features | Not part of the brief; would distract from the core analysis | Natural-language questions about forecast error |
| Redux or similar | TanStack Query and URL parameters already cover the state | Large shared client-side state |
| Playwright end-to-end tests | Too slow to set up in 8 hours | Once the UI is stable |

The tech-lead video can mention in one line how ingestion would grow into scheduled jobs at production scale.

## Deployment

Vercel hosts the app for free. Heroku has no free tier (its cheapest plan is paid), so it is the fallback only.

```
                 Vercel (one URL)
 ┌───────────────────────────────────────────────┐
 │  Static site: React build  (/)                │
 │                                               │
 │  Python function: FastAPI  (/api/v1/...)      │
 │     └─ reads bundled snapshot (CSV / SQLite)  │
 └───────────────────────────────────────────────┘
        ▲                         ▲
        │ loads app + JSON        │ git push → auto deploy
   User's browser           GitHub repo + Actions (lint, test, docker build)

 Local: docker-compose up → same FastAPI + React in containers
 Refresh: script fetches FUELHH + WINDFOR from Elexon → rewrites snapshot
```

### Vercel risks and how we avoid them

| Risk | Mitigation |
| --- | --- |
| Function bundle size limit (roughly 250 MB) | Use pandas + NumPy only; no pyarrow, SciPy or other heavy libraries |
| Function time limits and cold starts | No Elexon calls at request time; read the bundled snapshot and cache the computed tables in memory |
| No persistent disk | Snapshot is read-only and committed to the repo; changing it means redeploying |
| Vercel does not run our Docker image | Docker is for local runs and CI, which meets the brief's "use docker"; state this in the README |
| Routing between `/` and `/api` | `vercel.json` rewrites `/api/*` to the FastAPI function; test the deployed URL early, not at the end |

Deploy a "hello world" version to Vercel in the first hour. If it fails there, there is still time to switch to Heroku.

## 8-hour plan

The core logic and the video get the most protected time; UI polish is the first thing to cut.

1. **Data and core logic, 1.5 h:** fetch FUELHH and WINDFOR, save the January snapshot, write the forecast-selection rule and metrics, with pytest tests. Deploy a skeleton to Vercel in this slot.
2. **API, 1 h:** FastAPI routes for the series and the metrics, Pydantic models, `/api/v1/health`.
3. **Frontend, 2.5 h:** the decision view (actual vs forecast chart with cutoff control) and the accuracy view (headline metrics, error histogram, error by horizon).
4. **Docker, CI and deploy, 1 h:** multi-stage Dockerfile, docker-compose, GitHub Actions, final Vercel deploy.
5. **README and video, 2 h:** README with layout, run steps, app link and AI-use note; record the two 5-minute parts.

If time runs short, drop in this order: frontend tests, the error-by-horizon chart, then pre-commit hooks.
