"""Tests for src/agents/expense_checker.py - ExpenseChecker agent."""

from unittest.mock import patch

from google.adk.agents import LlmAgent
from google.genai import types

from src.agents.expense_checker import (
    build_receipt_image_part,
    create_expense_checker_agent,
    expense_checker_agent,
    get_receipt_image_from_drive,
)


class TestExpenseCheckerAgent:
    """Tests for the ExpenseChecker agent configuration."""

    def test_agent_is_llm_agent(self) -> None:
        assert isinstance(expense_checker_agent, LlmAgent)

    def test_agent_name(self) -> None:
        assert expense_checker_agent.name == "expense_checker"

    def test_agent_has_model(self) -> None:
        assert expense_checker_agent.model is not None
        assert "gemini" in expense_checker_agent.model

    def test_agent_has_output_key(self) -> None:
        assert expense_checker_agent.output_key == "check_result"

    def test_agent_instruction_mentions_calculation(self) -> None:
        instruction = expense_checker_agent.instruction
        assert "計算" in instruction or "算出" in instruction

    def test_agent_instruction_mentions_required_items(self) -> None:
        instruction = expense_checker_agent.instruction
        assert "必須" in instruction

    def test_agent_instruction_mentions_json(self) -> None:
        instruction = expense_checker_agent.instruction
        assert "JSON" in instruction

    def test_agent_instruction_references_extracted_rules(self) -> None:
        instruction = expense_checker_agent.instruction
        assert "{extracted_rules}" in instruction

    def test_agent_instruction_mentions_receipt_image(self) -> None:
        instruction = expense_checker_agent.instruction
        assert "領収書画像" in instruction or "画像" in instruction

    def test_agent_instruction_mentions_receipt_name_check(self) -> None:
        instruction = expense_checker_agent.instruction
        assert "上様" in instruction


class TestBuildReceiptImagePart:
    """Tests for build_receipt_image_part function."""

    def test_returns_part_with_inline_data(self) -> None:
        image_bytes = b"\x89PNG\r\n\x1a\n"
        part = build_receipt_image_part(image_bytes, "image/png")
        assert isinstance(part, types.Part)
        assert part.inline_data is not None

    def test_inline_data_has_correct_mime_type(self) -> None:
        image_bytes = b"\xff\xd8\xff\xe0"
        part = build_receipt_image_part(image_bytes, "image/jpeg")
        assert part.inline_data.mime_type == "image/jpeg"

    def test_inline_data_has_correct_data(self) -> None:
        image_bytes = b"fake-image-data"
        part = build_receipt_image_part(image_bytes, "image/png")
        assert part.inline_data.data == image_bytes


class TestGetReceiptImageFromDrive:
    """Tests for get_receipt_image_from_drive function."""

    def test_returns_bytes_and_mime_type(self) -> None:
        mock_bytes = b"\x89PNG"
        with patch("src.services.drive.DriveService") as mock_drive:
            instance = mock_drive.return_value
            instance.get_file_mime_type.return_value = "image/png"
            instance.get_receipt_image.return_value = mock_bytes

            image_data, mime_type = get_receipt_image_from_drive("test-file-id")
            assert image_data == mock_bytes
            assert mime_type == "image/png"

    def test_returns_none_when_not_found(self) -> None:
        with patch("src.services.drive.DriveService") as mock_drive:
            instance = mock_drive.return_value
            instance.get_file_mime_type.return_value = None
            instance.get_receipt_image.return_value = None

            image_data, mime_type = get_receipt_image_from_drive("nonexistent")
            assert image_data is None
            assert mime_type is None


class TestCreateExpenseCheckerAgent:
    """Tests for create_expense_checker_agent function."""

    def test_returns_llm_agent(self) -> None:
        agent = create_expense_checker_agent()
        assert isinstance(agent, LlmAgent)
        assert agent.name == "expense_checker"
