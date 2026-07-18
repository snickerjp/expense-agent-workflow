"""Tests for src/services/drive.py - Google Drive service."""

from unittest.mock import MagicMock, patch

from src.services.drive import DriveService


class TestDriveService:
    """Tests for DriveService."""

    def test_instantiation(self) -> None:
        service = DriveService()
        assert service is not None

    def test_get_rules_text_returns_string(self) -> None:
        service = DriveService()
        with patch.object(
            service, "_download_document_text", return_value="mock rules text"
        ):
            result = service.get_rules_text(file_id="test-file-id")
            assert isinstance(result, str)
            assert result == "mock rules text"

    def test_get_receipt_image_returns_bytes(self) -> None:
        service = DriveService()
        mock_bytes = b"\x89PNG\r\n"
        with patch.object(
            service, "_download_file_bytes", return_value=mock_bytes
        ):
            result = service.get_receipt_image(file_id="test-receipt-id")
            assert isinstance(result, bytes)
            assert result == mock_bytes

    def test_get_receipt_image_returns_none_when_not_found(self) -> None:
        service = DriveService()
        with patch.object(service, "_download_file_bytes", return_value=None):
            result = service.get_receipt_image(file_id="nonexistent-id")
            assert result is None

    def test_get_file_mime_type(self) -> None:
        service = DriveService()
        with patch.object(
            service,
            "_get_file_metadata",
            return_value={"mimeType": "image/jpeg"},
        ):
            result = service.get_file_mime_type(file_id="test-id")
            assert result == "image/jpeg"

    def test_list_receipts_in_folder(self) -> None:
        service = DriveService()
        mock_files = [
            {"id": "file1", "name": "receipt1.jpg", "mimeType": "image/jpeg"},
            {"id": "file2", "name": "receipt2.png", "mimeType": "image/png"},
        ]
        with patch.object(
            service, "_list_files_in_folder", return_value=mock_files
        ):
            result = service.list_receipts_in_folder(folder_id="test-folder-id")
            assert len(result) == 2
            assert result[0]["id"] == "file1"

    def test_build_service_uses_service_account(self) -> None:
        """Verify that _build_service creates a Drive API client."""
        with patch("src.services.drive.google.auth.default") as mock_auth:
            mock_auth.return_value = (MagicMock(), "test-project")
            with patch("src.services.drive.build") as mock_build:
                mock_build.return_value = MagicMock()
                service = DriveService(use_service_account=True)
                service._build_service()
                mock_build.assert_called_once()
