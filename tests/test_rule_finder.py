"""Tests for src/agents/rule_finder.py - RuleFinder agent."""

import os
from unittest.mock import patch

from google.adk.agents import LlmAgent

from src.agents.rule_finder import (
    RULES_TEXT_HARDCODED,
    build_instruction,
    create_rule_finder_agent,
    get_rules_text,
    rule_finder_agent,
)


class TestRuleFinderAgent:
    """Tests for the RuleFinder agent configuration."""

    def test_agent_is_llm_agent(self) -> None:
        assert isinstance(rule_finder_agent, LlmAgent)

    def test_agent_name(self) -> None:
        assert rule_finder_agent.name == "rule_finder"

    def test_agent_has_model(self) -> None:
        assert rule_finder_agent.model is not None
        assert "gemini" in rule_finder_agent.model

    def test_agent_instruction_contains_rules(self) -> None:
        instruction = rule_finder_agent.instruction
        assert "社内懇親会" in instruction
        assert "社外接待" in instruction
        assert "5,000円" in instruction or "5000" in instruction
        assert "10,000円" in instruction or "10000" in instruction

    def test_agent_instruction_contains_prohibition(self) -> None:
        instruction = rule_finder_agent.instruction
        assert "上様" in instruction

    def test_agent_has_output_key(self) -> None:
        assert rule_finder_agent.output_key == "extracted_rules"


class TestRulesTextHardcoded:
    """Tests for hardcoded rules text content."""

    def test_contains_social_gathering_rules(self) -> None:
        assert "社内懇親会" in RULES_TEXT_HARDCODED
        assert "5,000円" in RULES_TEXT_HARDCODED
        assert "全員の氏名" in RULES_TEXT_HARDCODED

    def test_contains_external_entertainment_rules(self) -> None:
        assert "社外接待" in RULES_TEXT_HARDCODED
        assert "10,000円" in RULES_TEXT_HARDCODED
        assert "役員" in RULES_TEXT_HARDCODED
        assert "15,000円" in RULES_TEXT_HARDCODED
        assert "取引先名" in RULES_TEXT_HARDCODED

    def test_contains_prohibited_items(self) -> None:
        assert "上様" in RULES_TEXT_HARDCODED


class TestGetRulesText:
    """Tests for get_rules_text function."""

    def test_demo_mode_returns_hardcoded(self) -> None:
        with patch.dict(os.environ, {"EXPENSE_MODE": "demo"}):
            from src.config import Settings

            with patch(
                "src.agents.rule_finder.get_settings",
                return_value=Settings(EXPENSE_MODE="demo"),
            ):
                result = get_rules_text()
                assert result == RULES_TEXT_HARDCODED

    def test_production_mode_without_file_id_falls_back(self) -> None:
        from src.config import Settings

        settings = Settings(
            EXPENSE_MODE="production", GOOGLE_CLOUD_PROJECT="test-project"
        )
        with patch(
            "src.agents.rule_finder.get_settings", return_value=settings
        ):
            result = get_rules_text()
            assert result == RULES_TEXT_HARDCODED


class TestBuildInstruction:
    """Tests for build_instruction function."""

    def test_includes_rules_text(self) -> None:
        result = build_instruction("test rules")
        assert "test rules" in result

    def test_includes_task_section(self) -> None:
        result = build_instruction("rules")
        assert "タスク" in result

    def test_includes_output_format(self) -> None:
        result = build_instruction("rules")
        assert "出力形式" in result


class TestCreateRuleFinderAgent:
    """Tests for create_rule_finder_agent function."""

    def test_returns_llm_agent(self) -> None:
        with patch.dict(os.environ, {"EXPENSE_MODE": "demo"}):
            from src.config import Settings

            with patch(
                "src.agents.rule_finder.get_settings",
                return_value=Settings(EXPENSE_MODE="demo"),
            ):
                agent = create_rule_finder_agent()
                assert isinstance(agent, LlmAgent)
                assert agent.name == "rule_finder"
