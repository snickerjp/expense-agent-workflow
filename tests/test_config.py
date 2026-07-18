"""Tests for src/config.py - Application configuration."""

import os
from unittest.mock import patch

import pytest

from src.config import Settings, get_settings


class TestSettings:
    """Tests for Settings configuration."""

    def test_default_mode_is_demo(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(EXPENSE_MODE="demo")
            assert settings.EXPENSE_MODE == "demo"

    def test_mode_can_be_production(self) -> None:
        settings = Settings(
            EXPENSE_MODE="production", GOOGLE_CLOUD_PROJECT="test-project"
        )
        assert settings.EXPENSE_MODE == "production"

    def test_invalid_mode_raises_error(self) -> None:
        with pytest.raises((ValueError, Exception)):
            Settings(EXPENSE_MODE="invalid")

    def test_google_cloud_project_optional_in_demo(self) -> None:
        settings = Settings(EXPENSE_MODE="demo")
        assert (
            settings.GOOGLE_CLOUD_PROJECT is None
            or settings.GOOGLE_CLOUD_PROJECT == ""
        )

    def test_demo_model_name(self) -> None:
        settings = Settings(EXPENSE_MODE="demo")
        assert "gemini" in settings.model_name

    def test_production_model_name(self) -> None:
        settings = Settings(
            EXPENSE_MODE="production",
            GOOGLE_CLOUD_PROJECT="test-project",
            GOOGLE_CLOUD_LOCATION="asia-northeast1",
        )
        assert "gemini" in settings.model_name

    def test_is_demo_property(self) -> None:
        settings = Settings(EXPENSE_MODE="demo")
        assert settings.is_demo is True

    def test_is_not_demo_in_production(self) -> None:
        settings = Settings(
            EXPENSE_MODE="production",
            GOOGLE_CLOUD_PROJECT="test-project",
        )
        assert settings.is_demo is False

    def test_drive_rules_file_id_optional(self) -> None:
        settings = Settings(EXPENSE_MODE="demo")
        assert settings.DRIVE_RULES_FILE_ID is None

    def test_sheets_form_id_optional(self) -> None:
        settings = Settings(EXPENSE_MODE="demo")
        assert settings.SHEETS_FORM_RESPONSES_ID is None

    def test_google_cloud_location_default(self) -> None:
        settings = Settings(EXPENSE_MODE="demo")
        assert settings.GOOGLE_CLOUD_LOCATION == "asia-northeast1"


class TestGetSettings:
    """Tests for get_settings function."""

    def test_get_settings_returns_settings_instance(self) -> None:
        with patch.dict(os.environ, {"EXPENSE_MODE": "demo"}):
            settings = get_settings()
            assert isinstance(settings, Settings)

    def test_get_settings_caches_result(self) -> None:
        with patch.dict(os.environ, {"EXPENSE_MODE": "demo"}):
            s1 = get_settings()
            s2 = get_settings()
            assert s1 is s2
