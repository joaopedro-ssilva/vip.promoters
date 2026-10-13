# syntax=docker/dockerfile:1
FROM python:3.13-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

FROM base AS builder-prod
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM base AS builder-dev
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

FROM python:3.13-slim AS runtime-base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH"
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --home /app app \
    && mkdir -p /data/uploads && chown -R app:app /data
WORKDIR /app

# Imagem de desenvolvimento/testes (inclui pytest e ruff)
FROM runtime-base AS dev
COPY --from=builder-dev /opt/venv /opt/venv
COPY --chown=app:app . /app
USER app
EXPOSE 8000
# Migracoes rodam no servico `migrate` (python -m app.cli preparar-banco), com o dono das
# tabelas; aqui o app sobe com o papel de aplicacao.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]

# Imagem final de producao
FROM runtime-base AS runtime
COPY --from=builder-prod /opt/venv /opt/venv
COPY --chown=app:app . /app
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
