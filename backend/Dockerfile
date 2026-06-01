FROM python:3.12-slim

# Install curl (healthcheck) + security updates
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd --system appgroup \
    && useradd --system --gid appgroup --no-create-home appuser

WORKDIR /app

# Install dependencies as root (needs write to site-packages)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app
COPY scripts ./scripts
# eval result snapshots (JSON) — powers the "Latest RAG Eval" card in /analytics
COPY eval/results ./eval/results

RUN chown -R appuser:appgroup /app
USER appuser

# Railway injects $PORT at runtime; falls back to 8080 for local docker/podman.
EXPOSE 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
