"""ExpenseRouter - Sequential ワークフロー.

RuleFinder → ExpenseChecker を順番に実行する。

ADK SequentialAgent pattern:
- sub_agents are executed in order
- output_key stores result in session state
- Next agent references output via {state_key}
"""

from google.adk.agents import SequentialAgent

from src.agents.expense_checker import expense_checker_agent
from src.agents.rule_finder import rule_finder_agent


def create_expense_router_agent() -> SequentialAgent:
    """ExpenseRouter SequentialAgent を作成.

    Pipeline:
        rule_finder (output_key="extracted_rules")
        → expense_checker (reads {extracted_rules},
                           output_key="check_result")
    """
    return SequentialAgent(
        name="expense_router",
        description="経費精算チェックのパイプライン: ルール抽出 → 審査判定",
        sub_agents=[rule_finder_agent, expense_checker_agent],
    )


# Default instance
expense_router_agent = create_expense_router_agent()
