"""Tests for src/schemas.py - Pydantic request/response models."""

import pytest
from pydantic import ValidationError

from src.schemas import ExpenseCheckRequest, ExpenseCheckResponse


class TestExpenseCheckRequest:
    """Tests for the request schema."""

    def test_valid_request_all_fields(self) -> None:
        req = ExpenseCheckRequest(
            type="社内懇親会",
            amount=30000,
            count=6,
            participants_raw="田中太郎、山田花子、佐藤一郎、鈴木次郎、高橋三郎、伊藤四郎",
            purpose="チームビルディング",
            receipt_url="https://example.com/receipt.pdf",
        )
        assert req.type == "社内懇親会"
        assert req.amount == 30000
        assert req.count == 6
        assert (
            req.participants_raw
            == "田中太郎、山田花子、佐藤一郎、鈴木次郎、高橋三郎、伊藤四郎"
        )
        assert req.purpose == "チームビルディング"
        assert req.receipt_url == "https://example.com/receipt.pdf"

    def test_valid_request_optional_fields_omitted(self) -> None:
        req = ExpenseCheckRequest(
            type="社外接待",
            amount=50000,
            count=5,
            participants_raw="田中太郎、クライアントA",
            purpose="商談",
        )
        assert req.receipt_url is None

    def test_invalid_amount_negative(self) -> None:
        with pytest.raises(ValidationError):
            ExpenseCheckRequest(
                type="社内懇親会",
                amount=-1000,
                count=3,
                participants_raw="A、B、C",
                purpose="飲み会",
            )

    def test_invalid_count_zero(self) -> None:
        with pytest.raises(ValidationError):
            ExpenseCheckRequest(
                type="社内懇親会",
                amount=10000,
                count=0,
                participants_raw="",
                purpose="飲み会",
            )

    def test_type_is_required(self) -> None:
        with pytest.raises(ValidationError):
            ExpenseCheckRequest(
                amount=10000,
                count=3,
                participants_raw="A、B、C",
                purpose="飲み会",
            )


class TestExpenseCheckResponse:
    """Tests for the response schema."""

    def test_valid_response_approved(self) -> None:
        resp = ExpenseCheckResponse(
            status="承認",
            confidence_score=4.5,
            details={"per_person": 5000, "rule": "社内懇親会1人5,000円上限"},
        )
        assert resp.status == "承認"
        assert resp.confidence_score == 4.5
        assert resp.details["per_person"] == 5000
        assert resp.rejection_reason is None

    def test_valid_response_rejected(self) -> None:
        resp = ExpenseCheckResponse(
            status="却下",
            confidence_score=5.0,
            details={"reason": "上限超過"},
            rejection_reason="1人あたりの金額が上限を超えています",
        )
        assert resp.status == "却下"
        assert resp.rejection_reason == "1人あたりの金額が上限を超えています"

    def test_valid_response_needs_human_review(self) -> None:
        resp = ExpenseCheckResponse(
            status="要人間確認",
            confidence_score=2.0,
            details={"note": "判断が困難"},
        )
        assert resp.status == "要人間確認"

    def test_confidence_score_range_min(self) -> None:
        with pytest.raises(ValidationError):
            ExpenseCheckResponse(
                status="承認",
                confidence_score=-0.1,
                details={},
            )

    def test_confidence_score_range_max(self) -> None:
        with pytest.raises(ValidationError):
            ExpenseCheckResponse(
                status="承認",
                confidence_score=5.1,
                details={},
            )

    def test_invalid_status(self) -> None:
        with pytest.raises(ValidationError):
            ExpenseCheckResponse(
                status="保留",
                confidence_score=3.0,
                details={},
            )
