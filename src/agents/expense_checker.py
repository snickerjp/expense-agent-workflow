"""ExpenseChecker Agent.

ルールとフォームデータを照合し審査結果を返すサブエージェント。
マルチモーダル対応: テキストデータに加えて領収書画像も解析可能。
"""

from google.adk.agents import LlmAgent
from google.genai import types

from src.config import get_settings

INSTRUCTION = """あなたは経費精算の審査担当者です。
前のエージェント（rule_finder）が抽出したルール情報が以下に展開されます:

--- 抽出されたルール ---
{extracted_rules}
--- ルールここまで ---

上記ルールとユーザーから提供された申請データを照合し、審査結果を出力してください。

【審査手順】
1. 算術計算: 合計金額 ÷ 参加人数 = 1人あたり金額を算出
2. 上限チェック: 1人あたり金額が規程の上限以内か確認
3. 必須項目チェック: 規程で求められる必須記載項目がすべて揃っているか確認
4. 禁止事項チェック: 禁止事項に該当しないか確認
5. 領収書画像チェック（画像が提供された場合）:
   - 宛名が「上様」でないか確認
   - 金額が申請額と一致するか確認
   - 日付が妥当か確認

【判定基準】
- 全条件クリア → status: "承認", confidence_score: 4.0〜5.0
- 明確な規程違反 → status: "却下", confidence_score: 4.0〜5.0,
  rejection_reasonに理由記載
- 判断に迷う場合 → status: "要人間確認", confidence_score: 1.0〜3.0

【出力形式】
以下のJSON構造で出力してください:
{
  "status": "承認" | "却下" | "要人間確認",
  "confidence_score": 0.0〜5.0,
  "details": {
    "per_person_amount": <1人あたり金額>,
    "limit_amount": <適用上限>,
    "required_items_check": <必須項目の充足状況>,
    "prohibition_check": <禁止事項の該当有無>,
    "receipt_check": <領収書の確認結果（画像提供時）>
  },
  "rejection_reason": <却下の場合の理由 or null>
}
"""


def build_receipt_image_part(image_bytes: bytes, mime_type: str) -> types.Part:
    """領収書画像をLLM用のPartに変換.

    Args:
        image_bytes: 画像のバイナリデータ
        mime_type: 画像のMIMEタイプ (e.g., "image/jpeg", "image/png")

    Returns:
        google.genai.types.Part with inline image data
    """
    blob = types.Blob(mime_type=mime_type, data=image_bytes)
    return types.Part(inline_data=blob)


def get_receipt_image_from_drive(
    file_id: str,
) -> tuple[bytes | None, str | None]:
    """Google Driveから領収書画像を取得.

    Args:
        file_id: Google Drive上の画像ファイルID

    Returns:
        (画像バイナリ, MIMEタイプ) のタプル。取得失敗時は (None, None)
    """
    from src.services.drive import DriveService

    drive = DriveService()
    mime_type = drive.get_file_mime_type(file_id)
    image_bytes = drive.get_receipt_image(file_id)
    return image_bytes, mime_type


def create_expense_checker_agent() -> LlmAgent:
    """ExpenseChecker エージェントを作成.

    gemini はマルチモーダル対応のため、
    テキストと画像の両方を入力として処理可能。

    Note: output_schema は使用しない。Gemini APIが
    dict[str, Any]のadditionalPropertiesを未サポートの
    ため、instruction内でJSON出力形式を指定し、
    main.py側でパースする。
    """
    settings = get_settings()

    return LlmAgent(
        name="expense_checker",
        model=settings.model_name,
        instruction=INSTRUCTION,
        output_key="check_result",
        description=(
            "抽出されたルールとフォームデータを照合し審査結果を返すエージェント"
        ),
    )


# デフォルトインスタンス
expense_checker_agent = create_expense_checker_agent()
