FROM node:20-slim AS frontend-build
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
        libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY backend/ backend/
WORKDIR /app/backend
RUN uv sync --frozen --no-cache \
    && uv run python -m playwright install --with-deps chromium
WORKDIR /app

COPY --from=frontend-build /src/frontend/dist ./frontend/dist

RUN mkdir -p /app/data
VOLUME ["/app/data"]

ENV ARESES_DATABASE_URL=sqlite+aiosqlite:////app/data/areses.db \
    ARESES_LOCAL_MODE=false \
    PYTHONUNBUFFERED=1

EXPOSE 8000

WORKDIR /app/backend
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]
