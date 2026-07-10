# Build stage: install deps separately for layer caching
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .

# Install only production-relevant packages (skip ipykernel)
RUN pip install --no-cache-dir -r requirements.txt

# ──────────────────────────────────────────────
# Runtime stage
# ──────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code (secrets are excluded via .dockerignore)
COPY . /app

# Google Sheets credentials: mount at runtime via volume or secret.
# Example: docker run -v /host/path/creds.json:/app/credentials/google-service-account.json ...
# The path is controlled by env var GOOGLE_SHEETS_CREDENTIALS_FILE.
RUN mkdir -p /app/credentials

EXPOSE 8000

CMD [uvicorn, main_chatwoot:app, --host, 0.0.0.0, --port, 8000]
