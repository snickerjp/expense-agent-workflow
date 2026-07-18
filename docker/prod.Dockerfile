# =============================================================================
# Stage 1: Builder - Install dependencies
# =============================================================================
FROM python:3.13-slim AS builder

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# =============================================================================
# Stage 2: Runner - Minimal runtime
# =============================================================================
FROM python:3.13-slim AS runner

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY src/ ./src/

# Production mode by default
ENV EXPENSE_MODE=production
ENV PORT=8080

# Cloud Run uses PORT environment variable (default 8080)
CMD exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT}
