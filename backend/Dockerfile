# Stage 1: Base image
FROM ghcr.io/astral-sh/uv:python3.12-alpine AS base

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1

# Stage 2: Development stage
FROM base AS development

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

CMD ["uv", "run", "watchmedo", "auto-restart", "--patterns=*.py", "--recursive", "--signal=SIGTERM", "python", "src/backend/main.py"]

# Stage 3: Build stage
FROM base AS builder

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Stage 4: Production stage
FROM python:3.12-alpine AS production

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1

COPY . .

USER nobody

EXPOSE 6767

CMD ["python", "src/backend/main.py"]
