"""Pydantic schemas for expense check request/response."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ExpenseCheckRequest(BaseModel):
    """経費精算チェックのリクエストスキーマ（フォームデータ用）."""

    type: str = Field(..., description="申請種別（例: 社内懇親会、社外接待）")
    amount: int = Field(..., gt=0, description="合計金額（円）")
    count: int = Field(..., gt=0, description="参加人数")
    participants_raw: str = Field(
        ..., description="参加者氏名（カンマ区切り等）"
    )
    purpose: str = Field(..., description="目的")
    receipt_url: str | None = Field(default=None, description="領収書URL")
    receipt_image_base64: str | None = Field(
        default=None,
        description="領収書画像（base64エンコード、直接アップロード用）",
    )
    receipt_mime_type: str | None = Field(
        default=None, description="領収書画像のMIMEタイプ（例: image/jpeg）"
    )


class ExpenseCheckResponse(BaseModel):
    """経費精算チェックのレスポンススキーマ（AIの審査結果用）."""

    status: Literal["承認", "却下", "要人間確認"] = Field(
        ..., description="審査結果ステータス"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=5.0, description="確信度スコア（0.0〜5.0）"
    )
    details: dict[str, Any] = Field(
        default_factory=dict, description="審査詳細"
    )
    rejection_reason: str | None = Field(default=None, description="却下理由")
