#!/bin/bash
# Hook script: Run ruff linter and formatter check on Python files
# Used as a kiro-cli stop hook to validate code quality after changes

set -euo pipefail

cd "$(dirname "$0")/../.."

# Check if ruff is available (local or via Docker)
if command -v ruff &> /dev/null; then
    echo "=== Running ruff lint ===" >&2
    ruff check src/ tests/ 2>&1 || true

    echo "=== Running ruff format check ===" >&2
    ruff format --check src/ tests/ 2>&1 || true
elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
    echo "=== Running ruff lint (Docker) ===" >&2
    docker compose -f compose.dev.yaml run --rm lint 2>&1 || true

    echo "=== Running ruff format check (Docker) ===" >&2
    docker compose -f compose.dev.yaml run --rm format-check 2>&1 || true
else
    echo "WARNING: ruff not found locally and Docker is not available. Skipping lint/format checks." >&2
fi
