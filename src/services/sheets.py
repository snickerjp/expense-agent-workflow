"""Google Sheets service - Google Formの回答データを取得."""

import logging
from typing import Any

import google.auth
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


class SheetsService:
    """Google Sheets API を使用してフォーム回答データを取得するサービス.

    Google FormはSheetsに回答を書き出すため、
    Sheets APIで最新の回答データにアクセスする。
    """

    def __init__(self) -> None:
        self._service = None

    def _build_service(self):
        """Build the Sheets API service client."""
        if self._service is None:
            credentials, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
            )
            self._service = build("sheets", "v4", credentials=credentials)
        return self._service

    def get_form_responses(
        self,
        spreadsheet_id: str,
        range_name: str = "Form Responses 1!A:Z",
    ) -> list[dict[str, Any]]:
        """Google Sheetsからフォーム回答データを取得.

        ヘッダー行をキーとした辞書のリストとして返す。

        Args:
            spreadsheet_id: Google Sheets のスプレッドシートID
            range_name: データ範囲（デフォルト: Form Responses 1シート全体）

        Returns:
            回答データのリスト（各行がdict）
        """
        rows = self._fetch_sheet_values(spreadsheet_id, range_name)
        if not rows or len(rows) < 2:
            return []

        headers = rows[0]
        results = []
        for row in rows[1:]:
            # 行がヘッダーより短い場合、空文字で埋める
            padded_row = row + [""] * (len(headers) - len(row))
            results.append(dict(zip(headers, padded_row, strict=False)))

        return results

    def get_latest_response(
        self,
        spreadsheet_id: str,
        range_name: str = "Form Responses 1!A:Z",
    ) -> dict[str, Any] | None:
        """最新のフォーム回答データを1件取得.

        Args:
            spreadsheet_id: Google Sheets のスプレッドシートID
            range_name: データ範囲

        Returns:
            最新の回答データ（dict）、データがない場合はNone
        """
        responses = self.get_form_responses(spreadsheet_id, range_name)
        if not responses:
            return None
        return responses[-1]

    def _fetch_sheet_values(
        self, spreadsheet_id: str, range_name: str
    ) -> list[list[str]]:
        """Sheets APIからセルの値を取得."""
        try:
            service = self._build_service()
            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=range_name)
                .execute()
            )
            return result.get("values", [])
        except Exception:
            logger.exception("Failed to fetch sheet values: %s", spreadsheet_id)
            return []
