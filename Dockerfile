FROM python:3.12-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade "pip==25.2" && pip install .

FROM python:3.12-slim-bookworm AS runtime

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MCP_NAME=company-api-gateway \
    SKILLS_DIR=/app/skills

RUN groupadd --gid 10001 gateway \
    && useradd --uid 10001 --gid 10001 --no-create-home --home-dir /nonexistent gateway \
    && mkdir -p /app/skills /config \
    && chown -R 10001:10001 /app /config

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
USER 10001:10001
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)"]

CMD ["uvicorn", "company_mcp_gateway.app:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]

