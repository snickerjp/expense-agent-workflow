"""Tests for src/agents/router.py - ExpenseRouter workflow."""

from google.adk import Workflow

from src.agents.router import (
    create_expense_router_agent,
    expense_router_agent,
)


class TestExpenseRouterAgent:
    """Tests for the ExpenseRouter Workflow agent."""

    def test_agent_is_workflow(self) -> None:
        assert isinstance(expense_router_agent, Workflow)

    def test_agent_name(self) -> None:
        assert expense_router_agent.name == "expense_router"

    def test_agent_has_description(self) -> None:
        assert expense_router_agent.description is not None
        assert len(expense_router_agent.description) > 0

    def test_agent_has_edges(self) -> None:
        assert expense_router_agent.edges is not None
        assert len(expense_router_agent.edges) > 0


class TestCreateExpenseRouterAgent:
    """Tests for create_expense_router_agent function."""

    def test_function_exists(self) -> None:
        assert callable(create_expense_router_agent)
