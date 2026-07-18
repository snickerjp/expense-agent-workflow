"""FastAPI application for expense check multi-agent system.

動作モード:
- demo: APIリクエストで直接データを受け取り、
  APIキー認証でGeminiを呼び出す
- production: Google Form → Sheets経由のデータ取得、
  Drive領収書画像読み取り、Vertex AI + サービスアカウント認証

Design:
- InMemoryRunner (ADK recommended pattern)
- FastAPI lifespan context manager for lifecycle
"""

import json
import logging
import re
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from google.adk.runners import InMemoryRunner
from google.genai import types

from src.agents.expense_checker import (
    build_receipt_image_part,
    get_receipt_image_from_drive,
)
from src.agents.router import expense_router_agent
from src.config import get_settings
from src.schemas import ExpenseCheckRequest, ExpenseCheckResponse

logger = logging.getLogger(__name__)

# Application state - initialized during lifespan
_runner: InMemoryRunner | None = None

APP_NAME = "expense_agent"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle.

    Initialize ADK runner on startup, cleanup on shutdown.
    """
    global _runner

    # ADK reads GOOGLE_CLOUD_LOCATION for Vertex AI endpoint.
    # Global models (e.g. gemini-3.1-flash-lite-preview) require
    # location='global', separate from Cloud Run deploy region.
    settings = get_settings()
    if not settings.is_demo:
        import os

        os.environ["GOOGLE_CLOUD_LOCATION"] = settings.GEMINI_LOCATION

    _runner = InMemoryRunner(
        agent=expense_router_agent,
        app_name=APP_NAME,
    )
    logger.info("ADK InMemoryRunner initialized (app=%s)", APP_NAME)
    yield
    # Cleanup
    _runner = None
    logger.info("ADK InMemoryRunner shutdown")


app = FastAPI(
    title="経費精算マルチエージェントシステム",
    description=(
        "Google ADK を使用した経費精算の自動審査API（マルチモーダル対応）"
    ),
    version="2.0.0",
    lifespan=lifespan,
)


def get_runner() -> InMemoryRunner:
    """Get the InMemoryRunner instance. Raises if not initialized."""
    if _runner is None:
        raise RuntimeError(
            "Runner not initialized. Application lifespan not started."
        )
    return _runner


def _extract_json(text: str) -> str:
    """Extract JSON from text, handling markdown code blocks.

    LLMs often wrap JSON in ```json ... ``` blocks.
    This function extracts the raw JSON content.
    """
    match = re.search(
        r"```(?:json)?\s*\n?(.*?)\n?\s*```",
        text,
        re.DOTALL,
    )
    if match:
        return match.group(1).strip()
    return text.strip()


async def run_expense_check(
    request: ExpenseCheckRequest,
    receipt_file_id: str | None = None,
) -> dict:
    """Run the expense check workflow using ADK InMemoryRunner.

    マルチモーダル対応: 領収書画像がある場合はテキスト+画像でLLMに投入。

    Args:
        request: The expense check request data.
        receipt_file_id: Google Drive上の領収書画像ファイルID（production時）

    Returns:
        Dictionary containing the structured check result.
    """
    settings = get_settings()
    runner = get_runner()
    user_id = f"user_{uuid.uuid4().hex[:8]}"

    # Create a new session via InMemoryRunner's session_service
    session = await runner.session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
    )

    # Build the user message from request data
    user_message = (
        f"以下の経費精算申請を審査してください:\n"
        f"- 申請種別: {request.type}\n"
        f"- 合計金額: {request.amount}円\n"
        f"- 参加人数: {request.count}人\n"
        f"- 参加者: {request.participants_raw}\n"
        f"- 目的: {request.purpose}\n"
        f"- 領収書URL: {request.receipt_url or 'なし'}\n"
    )

    # Build parts (text + optional image for multimodal)
    parts: list[types.Part] = [types.Part(text=user_message)]

    # マルチモーダル: 領収書画像がある場合はPartに追加
    if receipt_file_id and not settings.is_demo:
        image_bytes, mime_type = get_receipt_image_from_drive(receipt_file_id)
        if image_bytes and mime_type:
            image_part = build_receipt_image_part(image_bytes, mime_type)
            parts.append(image_part)
            logger.info("Added receipt image to request (mime: %s)", mime_type)

    content = types.Content(role="user", parts=parts)

    # Run the agent workflow
    final_response_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    final_response_text = part.text

    # Parse the structured response from output_key="check_result"
    # First try to get from session state (ADK output_key stores here)
    session = await runner.session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session.id,
    )
    if session and session.state and "check_result" in session.state:
        state_result = session.state["check_result"]
        if isinstance(state_result, str):
            try:
                parsed = _extract_json(state_result)
                result = json.loads(parsed)
                validated = ExpenseCheckResponse(**result)
                return validated.model_dump()
            except (json.JSONDecodeError, Exception):
                pass

    # Fallback: parse from last event text
    try:
        parsed_text = _extract_json(final_response_text)
        result = json.loads(parsed_text)
        validated = ExpenseCheckResponse(**result)
        return validated.model_dump()
    except (json.JSONDecodeError, Exception):
        return ExpenseCheckResponse(
            status="要人間確認",
            confidence_score=1.0,
            details={"raw_response": final_response_text},
            rejection_reason=None,
        ).model_dump()


@app.post("/api/expense-check", response_model=ExpenseCheckResponse)
async def expense_check_endpoint(request: ExpenseCheckRequest) -> dict:
    """経費精算チェックエンドポイント.

    リクエストデータをExpenseRouterワークフローに投入し、
    AIの構造化審査結果をレスポンスとして返却する。

    production モードの場合、receipt_url にDriveファイルIDが含まれていれば
    領収書画像をマルチモーダル入力として処理する。
    """
    # receipt_urlからDriveファイルIDを抽出
    receipt_file_id = None
    if request.receipt_url and not get_settings().is_demo:
        url = request.receipt_url
        if "/d/" in url:
            receipt_file_id = url.split("/d/")[1].split("/")[0]
        elif not url.startswith("http"):
            receipt_file_id = url

    result = await run_expense_check(request, receipt_file_id=receipt_file_id)
    return result
