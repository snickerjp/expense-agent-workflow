"""Tests for src/main.py - FastAPI application with expense check endpoint."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app, run_expense_check


class TestFastAPIApp:
    """Tests for the FastAPI application setup."""

    def test_app_exists(self) -> None:
        from fastapi import FastAPI

        assert isinstance(app, FastAPI)

    def test_app_has_expense_check_endpoint(self) -> None:
        routes = [r.path for r in app.routes]
        assert "/api/expense-check" in routes

    def test_app_version(self) -> None:
        assert app.version == "2.0.0"

    def test_app_has_lifespan(self) -> None:
        """Verify lifespan is configured (FastAPI recommended pattern)."""
        assert app.router.lifespan_context is not None


class TestExpenseCheckEndpoint:
    """Tests for POST /api/expense-check endpoint."""

    @pytest.fixture
    def valid_payload(self) -> dict:
        return {
            "type": "社内懇親会",
            "amount": 24000,
            "count": 6,
            "participants_raw": "田中太郎、山田花子、佐藤一郎、鈴木次郎、高橋三郎、伊藤四郎",
            "purpose": "チームビルディング",
            "receipt_url": "https://example.com/receipt.pdf",
        }

    @pytest.fixture
    def mock_response_data(self) -> dict:
        return {
            "status": "承認",
            "confidence_score": 4.5,
            "details": {"per_person_amount": 4000, "limit_amount": 5000},
            "rejection_reason": None,
        }

    @pytest.mark.asyncio
    async def test_endpoint_returns_200_on_valid_request(
        self, valid_payload: dict, mock_response_data: dict
    ) -> None:
        with patch(
            "src.main.run_expense_check", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = mock_response_data
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/expense-check", json=valid_payload
                )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_endpoint_returns_expense_check_response(
        self, valid_payload: dict, mock_response_data: dict
    ) -> None:
        with patch(
            "src.main.run_expense_check", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = mock_response_data
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/expense-check", json=valid_payload
                )
            data = response.json()
            assert data["status"] == "承認"
            assert data["confidence_score"] == 4.5
            assert data["details"]["per_person_amount"] == 4000

    @pytest.mark.asyncio
    async def test_endpoint_returns_422_on_invalid_request(self) -> None:
        invalid_payload = {"type": "社内懇親会"}
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/expense-check", json=invalid_payload
            )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_endpoint_calls_run_expense_check(
        self, valid_payload: dict, mock_response_data: dict
    ) -> None:
        with patch(
            "src.main.run_expense_check", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = mock_response_data
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                await client.post("/api/expense-check", json=valid_payload)
            mock_run.assert_called_once()


class TestRunExpenseCheck:
    """Tests for the run_expense_check function."""

    def test_run_expense_check_is_async(self) -> None:
        assert asyncio.iscoroutinefunction(run_expense_check)

    def test_run_expense_check_accepts_receipt_file_id(self) -> None:
        """Verify the function signature accepts receipt_file_id parameter."""
        import inspect

        sig = inspect.signature(run_expense_check)
        params = list(sig.parameters.keys())
        assert "receipt_file_id" in params
