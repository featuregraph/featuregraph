# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[study-builder]"

COPY scripts ./scripts
COPY artifacts ./artifacts
COPY apps/assistant ./apps/assistant

# Nothing here executes researcher data. The public assistant proposes; the
# approval path and the compiler live behind the MCP runtime.
RUN useradd --create-home --uid 10001 assistant \
 && mkdir -p /var/lib/featuregraph-sessions \
 && chown assistant:assistant /var/lib/featuregraph-sessions
USER assistant

ENV PORT=8080 \
    FEATUREGRAPH_SESSION_DIR=/var/lib/featuregraph-sessions
EXPOSE 8080

CMD ["python", "apps/assistant/server.py"]
