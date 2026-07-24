FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (dev extras: ruff, pytest, etc.)
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy source code (will be overridden by volume mount in dev)
COPY src/ ./src/

# Default environment
ENV EXPENSE_MODE=demo

# Run uvicorn with hot-reload for local development
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
