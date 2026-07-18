"""Application configuration with environment-based mode switching."""

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """アプリケーション設定.

    EXPENSE_MODE で動作モードを切り替える:
    - demo: ハードコードデータ、APIキー認証
    - production: Google Drive/Sheets連携、Vertex AI + サービスアカウント認証
    """

    EXPENSE_MODE: Literal["demo", "production"] = "demo"

    # Google Cloud settings (required for production)
    GOOGLE_CLOUD_PROJECT: str | None = None
    GOOGLE_CLOUD_LOCATION: str = "asia-northeast1"
    GOOGLE_GENAI_USE_VERTEXAI: bool = False

    # Google API Key (demo mode)
    GOOGLE_API_KEY: str | None = None

    # Google Drive settings (production)
    DRIVE_RULES_FILE_ID: str | None = None
    DRIVE_RECEIPTS_FOLDER_ID: str | None = None

    # Google Sheets settings (production)
    SHEETS_FORM_RESPONSES_ID: str | None = None
    SHEETS_FORM_RESPONSES_RANGE: str = "Form Responses 1!A:Z"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @model_validator(mode="after")
    def validate_production_requirements(self) -> "Settings":
        """Validate that production mode has required settings."""
        if self.EXPENSE_MODE == "production" and not self.GOOGLE_CLOUD_PROJECT:
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT is required in production mode"
            )
        return self

    @property
    def is_demo(self) -> bool:
        """Check if running in demo mode."""
        return self.EXPENSE_MODE == "demo"

    @property
    def model_name(self) -> str:
        """Get the LLM model name.

        Uses gemini-3.5-flash (GA stable) for both modes.
        Multimodal, function calling, thinking capable.
        Best cost-efficiency in the Flash tier.
        """
        return "gemini-3.5-flash"


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
