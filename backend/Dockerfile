FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.12 /uv /bin/uv

WORKDIR /app

# Install dependencies first so they are cached between code changes
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY migrations ./migrations
COPY app ./app

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
# Load the January data on first start if the database is empty, then serve.
# A failed load does not stop the server; the app then shows that no data is loaded.
CMD ["sh", "-c", "python -m app.ingest refresh --if-empty; exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
