# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm AS builder

WORKDIR /build
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
RUN pip install --no-cache-dir "uv>=0.13,<0.14"
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --locked --all-extras --no-dev

FROM python:3.12-slim-bookworm AS runtime

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y default-mysql-client postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin crosserp \
    && mkdir -p /data \
    && chown crosserp:crosserp /data

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/src /app/src
COPY scripts/docker-init.sh /app/scripts/docker-init.sh
COPY scripts/render_grant_sql.py /app/scripts/render_grant_sql.py
COPY scripts/sql /app/scripts/sql
RUN chmod 0755 /app/scripts/docker-init.sh /app/scripts/render_grant_sql.py

USER crosserp
WORKDIR /app
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]

CMD ["crosserp", "serve", "--host", "0.0.0.0", "--port", "8000", "--i-understand-https"]
