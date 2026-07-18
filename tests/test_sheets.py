"""Tests for src/services/sheets.py - Google Sheets service."""

from unittest.mock import MagicMock, patch

from src.services.sheets import SheetsService


class TestSheetsService:
    """Tests for SheetsService."""

    def test_instantiation(self) -> None:
        service = SheetsService()
        assert service is not None

    def test_get_form_responses_returns_list(self) -> None:
        service = SheetsService()
        mock_rows = [
            [
                "タイムスタンプ",
                "申請種別",
                "金額",
                "人数",
                "参加者",
                "目的",
                "領収書ファイルID",
            ],
            [
                "2024/01/01",
                "社内懇親会",
                "24000",
                "6",
                "田中、山田、佐藤",
                "新年会",
                "file-id-123",
            ],
        ]
        with patch.object(
            service, "_fetch_sheet_values", return_value=mock_rows
        ):
            result = service.get_form_responses(
                spreadsheet_id="test-sheet-id",
                range_name="Form Responses 1!A:Z",
            )
            assert isinstance(result, list)
            assert len(result) == 1  # ヘッダー行を除く
            assert result[0]["申請種別"] == "社内懇親会"

    def test_get_form_responses_empty_sheet(self) -> None:
        service = SheetsService()
        with patch.object(service, "_fetch_sheet_values", return_value=[]):
            result = service.get_form_responses(
                spreadsheet_id="test-sheet-id",
                range_name="A:Z",
            )
            assert result == []

    def test_get_form_responses_header_only(self) -> None:
        service = SheetsService()
        mock_rows = [["タイムスタンプ", "申請種別", "金額"]]
        with patch.object(
            service, "_fetch_sheet_values", return_value=mock_rows
        ):
            result = service.get_form_responses(
                spreadsheet_id="test-sheet-id",
                range_name="A:Z",
            )
            assert result == []

    def test_get_latest_response(self) -> None:
        service = SheetsService()
        mock_rows = [
            ["タイムスタンプ", "申請種別", "金額", "人数", "参加者", "目的"],
            ["2024/01/01", "社内懇親会", "24000", "6", "田中", "新年会"],
            ["2024/01/02", "社外接待", "50000", "5", "佐藤", "商談"],
        ]
        with patch.object(
            service, "_fetch_sheet_values", return_value=mock_rows
        ):
            result = service.get_latest_response(
                spreadsheet_id="test-sheet-id",
                range_name="A:Z",
            )
            assert result is not None
            assert result["申請種別"] == "社外接待"

    def test_get_latest_response_empty_returns_none(self) -> None:
        service = SheetsService()
        with patch.object(service, "_fetch_sheet_values", return_value=[]):
            result = service.get_latest_response(
                spreadsheet_id="test-sheet-id",
                range_name="A:Z",
            )
            assert result is None

    def test_build_service_uses_service_account(self) -> None:
        """Verify that _build_service creates a Sheets API client."""
        with patch("src.services.sheets.google.auth.default") as mock_auth:
            mock_auth.return_value = (MagicMock(), "test-project")
            with patch("src.services.sheets.build") as mock_build:
                mock_build.return_value = MagicMock()
                service = SheetsService()
                service._build_service()
                mock_build.assert_called_once()
