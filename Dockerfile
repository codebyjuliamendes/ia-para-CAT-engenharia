# syntax=docker/dockerfile:1

# ---------- build: resolve dependências com uv a partir do lockfile ----------
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra postgres --no-install-project
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra postgres --no-editable

# ---------- runtime: imagem enxuta, usuário sem privilégios ----------
FROM python:3.12-slim AS runtime
ARG APP_UID=10001
RUN groupadd --system --gid ${APP_UID} app \
    && useradd --system --uid ${APP_UID} --gid app --home-dir /home/app --create-home app \
    && mkdir -p /data && chown app:app /data
WORKDIR /app
COPY --from=builder --chown=root:root /app/.venv /app/.venv
COPY --chown=root:root .streamlit ./.streamlit
COPY --chown=root:root streamlit_app.py docker-entrypoint.sh ./
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/app \
    PORT=8502 \
    SAFECAT_DATABASE_URL=sqlite:////data/safecat.db \
    SAFECAT_TABLES_DIR=/data/tabelas
USER app
VOLUME ["/data"]
EXPOSE 8502
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('PORT', '8502')}/_stcore/health\", timeout=4)"]
ENTRYPOINT ["/bin/sh", "/app/docker-entrypoint.sh"]
