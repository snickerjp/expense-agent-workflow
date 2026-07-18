"""Tests for src/agents/router.py - ExpenseRouter workflow agent."""

from google.adk.agents import SequentialAgent

from src.agents.expense_checker import expense_checker_agent
from src.agents.router import create_expense_router_agent, expense_router_agent
from src.agents.rule_finder import rule_finder_agent


class TestExpenseRouterAgent:
    """Tests for the ExpenseRouter sequential workflow agent."""

    def test_agent_is_sequential_agent(self) -> None:
        assert isinstance(expense_router_agent, SequentialAgent)

    def test_agent_name(self) -> None:
        assert expense_router_agent.name == "expense_router"

    def test_agent_has_two_sub_agents(self) -> None:
        assert len(expense_router_agent.sub_agents) == 2

    def test_first_sub_agent_is_rule_finder(self) -> None:
        assert expense_router_agent.sub_agents[0] is rule_finder_agent

    def test_second_sub_agent_is_expense_checker(self) -> None:
        assert expense_router_agent.sub_agents[1] is expense_checker_agent

    def test_execution_order_rule_finder_then_checker(self) -> None:
        """Verify Sequential ensures rule_finder runs before expense_checker."""
        agents = expense_router_agent.sub_agents
        assert agents[0].name == "rule_finder"
        assert agents[1].name == "expense_checker"

    def test_agent_has_description(self) -> None:
        assert expense_router_agent.description is not None
        assert len(expense_router_agent.description) > 0


class TestCreateExpenseRouterAgent:
    """Tests for create_expense_router_agent function."""

    def test_function_exists(self) -> None:
        """Verify create_expense_router_agent is importable."""
        assert callable(create_expense_router_agent)
