# AGENTS.md

Guidance for AI coding agents (Claude Code, Codex, Cursor, etc.) working in this repository.

## Project overview

FastAPI + Google ADK multi-agent system that auto-reviews expense claims (経費精算). Two agents run in an ADK `Workflow` pipeline: `rule_finder` extracts the applicable company rules for a claim type, then `expense_checker` (multimodal — can read a receipt image) validates the claim against those rules and returns a structured verdict. Deployed to Cloud Run; intended to sit behind a Google Form → Sheets → Apps Script trigger (see `gas/`).

Everything in the repo — code, comments, README, API payloads — is in Japanese. Match that when editing docstrings/instructions/comments in `src/`.

## Commands

```bash
# Run the app (demo mode by default, reads .env)
docker compose up

# Tests
pytest tests/ -v
pytest tests/test_router.py -v          # single file
pytest tests/test_main.py::TestExpenseCheckEndpoint -v   # single class/test

# Lint / format (Google Python Style Guide, 80 char lines)
ruff check src/ tests/
ruff format src/ tests/

# Deploy to Cloud Run (creates service account + IAM roles, then `adk deploy cloud_run`)
python deploy_cloudrun.py
```

There's no local venv setup script — `docker compose up` builds via `docker/dev.Dockerfile`. `requirements-dev.txt` pulls in pytest/ruff/httpx for local tool use outside Docker.

## Architecture

**Two operating modes, controlled by `EXPENSE_MODE` in `src/config.py` (`Settings.is_demo`):**
- `demo` (default): hardcoded rules text, Gemini API key auth, no image reading, model `gemini-3.5-flash`.
- `production`: rules fetched from Google Drive, form data from Sheets, receipt images fetched from Drive and passed to the LLM, Vertex AI + service account auth, model `gemini-3.1-flash-lite`.

Nearly every module branches on `get_settings().is_demo` rather than having separate code paths — check both branches when touching `rule_finder.py`, `expense_checker.py`, or `main.py`.

**Request flow** (`src/main.py::run_expense_check`):
1. `ExpenseCheckRequest` (Pydantic) comes in via `POST /api/expense-check`.
2. A fresh ADK `InMemoryRunner` session is created per request; the request is rendered into a Japanese prompt string plus an optional image `Part` (production mode, when `receipt_url` resolves to a Drive file ID).
3. `expense_router_agent` (`src/agents/router.py`) runs the `Workflow`: `rule_finder` → `expense_checker`, wired via ADK's `edges=[(START, rule_finder_agent, expense_checker_agent)]`.
4. `rule_finder` writes its output to session state key `extracted_rules`; `expense_checker`'s instruction interpolates `{extracted_rules}` and writes `check_result`.
5. `check_result` is a JSON string (no `output_schema` — Gemini doesn't support the needed `additionalProperties` shape) that `main.py::_extract_json` strips out of markdown fences and parses into `ExpenseCheckResponse`. Falls back to a `"要人間確認"` (needs human review) response if parsing fails at any stage.

**Agent factories**: each agent module exposes both a `create_*_agent()` factory and a module-level default instance (e.g. `rule_finder_agent`) built at import time — the factory reads `get_settings()` fresh, so tests can monkeypatch settings and call the factory rather than relying on the cached default instance.

**Services** (`src/services/drive.py`, `sheets.py`) are thin wrappers over `googleapiclient` using `google.auth.default()` — only relevant/called in production mode.

**ADK version note**: the codebase runs ADK 2.0's `Workflow`/`edges`/`START` API (not the deprecated `SequentialAgent`); `pyproject.toml` filters ADK's own `DeprecationWarning` noise in tests.

## Key files

- `src/config.py` — `Settings` (pydantic-settings, env-driven), the demo/production switch, model name selection.
- `src/schemas.py` — request/response Pydantic models; `status` is a closed `Literal["承認", "却下", "要人間確認"]`.
- `src/agents/router.py`, `rule_finder.py`, `expense_checker.py` — the two-agent pipeline and its prompts.
- `src/main.py` — FastAPI app, lifespan-managed `InMemoryRunner`, response parsing/fallback logic.

## Coding conventions

- All code must pass `ruff check` and `ruff format --check` (Google Python Style Guide, 80-char lines; see `pyproject.toml` for the exact rule set and ignores).
- Use type hints throughout, following the existing style in `src/`.
