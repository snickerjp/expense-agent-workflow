"""RuleFinder Agent - 社内規程から申請種別に応じたルールを抽出するサブエージェント.

動作モードにより社内規程の取得元を切り替える:
- demo: ハードコードされたRULES_TEXTを使用
- production: Google Driveから動的に取得
"""

from google.adk.agents import LlmAgent

from src.config import get_settings

# デモ用ハードコードルール（production時はDriveから取得で上書きされる）
RULES_TEXT_HARDCODED = """
【社内規程: 経費精算ルール】

■ 社内懇親会
- 1人あたり上限: 5,000円
- 全員の氏名を記載すること（必須）
- 領収書の宛名は正式社名であること

■ 社外接待
- 1人あたり上限: 10,000円
- 役員同席時は1人あたり上限: 15,000円
- 取引先名の記載が必須
- 目的の記載が必須

■ 禁止事項
- 領収書の宛名が「上様」のものは一切認めない
- 同日に同一店舗での複数回精算は禁止
"""


def get_rules_text() -> str:
    """動作モードに応じて社内規程テキストを取得.

    Returns:
        社内規程テキスト
    """
    settings = get_settings()

    if settings.is_demo:
        return RULES_TEXT_HARDCODED

    # Production: Google Driveから取得
    from src.services.drive import DriveService

    if not settings.DRIVE_RULES_FILE_ID:
        # Drive file IDが未設定の場合はフォールバック
        return RULES_TEXT_HARDCODED

    drive_service = DriveService()
    return drive_service.get_rules_text(file_id=settings.DRIVE_RULES_FILE_ID)


def build_instruction(rules_text: str) -> str:
    """ルールテキストからインストラクションを構築."""
    return f"""あなたは経費精算の社内規程に精通した専門家です。
以下の社内規程テキストを参照し、ユーザーの申請種別に応じた適用ルールを抽出してください。

{rules_text}

【タスク】
ユーザーから提供された申請情報（申請種別、金額、人数など）を確認し、
該当する規程のルール（上限金額、必須項目、禁止事項）を抽出して、
次のエージェントが照合しやすい形式で出力してください。

出力形式:
- 適用カテゴリ: （社内懇親会 or 社外接待）
- 1人あたり上限金額: （円）
- 必須記載項目: （リスト）
- 適用される禁止事項: （リスト）
- 特記事項: （該当する場合のみ）
"""


def create_rule_finder_agent() -> LlmAgent:
    """RuleFinder エージェントを作成.

    モードに応じてルールテキストの取得元を切り替える。
    """
    settings = get_settings()
    rules_text = get_rules_text()
    instruction = build_instruction(rules_text)

    return LlmAgent(
        name="rule_finder",
        model=settings.model_name,
        instruction=instruction,
        output_key="extracted_rules",
        description="社内規程から申請種別に応じたルールを抽出するエージェント",
    )


# デフォルトインスタンス（後方互換性のため）
rule_finder_agent = create_rule_finder_agent()
