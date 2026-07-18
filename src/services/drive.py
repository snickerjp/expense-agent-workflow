"""Google Drive service - 社内規程ドキュメント・領収書画像の取得."""

import io
import logging
from typing import Any

import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

logger = logging.getLogger(__name__)


class DriveService:
    """Google Drive API を使用してファイルを取得するサービス.

    サービスアカウント認証でDrive APIにアクセスし、
    社内規程ドキュメントや領収書画像をダウンロードする。
    """

    def __init__(self, use_service_account: bool = True) -> None:
        self._use_service_account = use_service_account
        self._service = None

    def _build_service(self):
        """Build the Drive API service client."""
        if self._service is None:
            credentials, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/drive.readonly"]
            )
            self._service = build("drive", "v3", credentials=credentials)
        return self._service

    def get_rules_text(self, file_id: str) -> str:
        """Googleドライブからルールドキュメントのテキストを取得.

        Google Docs形式のファイルをプレーンテキストとしてエクスポートする。

        Args:
            file_id: Google Drive のファイルID

        Returns:
            ドキュメントのテキスト内容
        """
        return self._download_document_text(file_id)

    def get_receipt_image(self, file_id: str) -> bytes | None:
        """Googleドライブから領収書画像のバイナリデータを取得.

        Args:
            file_id: 領収書画像ファイルのID

        Returns:
            画像のバイナリデータ、見つからない場合はNone
        """
        return self._download_file_bytes(file_id)

    def get_file_mime_type(self, file_id: str) -> str | None:
        """ファイルのMIMEタイプを取得.

        Args:
            file_id: Google Drive のファイルID

        Returns:
            MIMEタイプ文字列
        """
        metadata = self._get_file_metadata(file_id)
        if metadata:
            return metadata.get("mimeType")
        return None

    def list_receipts_in_folder(self, folder_id: str) -> list[dict[str, Any]]:
        """フォルダ内の領収書ファイル一覧を取得.

        Args:
            folder_id: Google Drive のフォルダID

        Returns:
            ファイルメタデータのリスト
        """
        return self._list_files_in_folder(folder_id)

    def _download_document_text(self, file_id: str) -> str:
        """Google Docsをプレーンテキストとしてエクスポート."""
        service = self._build_service()
        request = service.files().export_media(
            fileId=file_id, mimeType="text/plain"
        )
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue().decode("utf-8")

    def _download_file_bytes(self, file_id: str) -> bytes | None:
        """ファイルのバイナリデータをダウンロード."""
        try:
            service = self._build_service()
            request = service.files().get_media(fileId=file_id)
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            return buffer.getvalue()
        except Exception:
            logger.exception("Failed to download file: %s", file_id)
            return None

    def _get_file_metadata(self, file_id: str) -> dict[str, Any] | None:
        """ファイルのメタデータを取得."""
        try:
            service = self._build_service()
            return (
                service.files()
                .get(fileId=file_id, fields="id,name,mimeType")
                .execute()
            )
        except Exception:
            logger.exception("Failed to get file metadata: %s", file_id)
            return None

    def _list_files_in_folder(self, folder_id: str) -> list[dict[str, Any]]:
        """フォルダ内のファイル一覧を取得."""
        try:
            service = self._build_service()
            query = f"'{folder_id}' in parents and trashed = false"
            results = (
                service.files()
                .list(q=query, fields="files(id,name,mimeType)", pageSize=100)
                .execute()
            )
            return results.get("files", [])
        except Exception:
            logger.exception("Failed to list files in folder: %s", folder_id)
            return []
