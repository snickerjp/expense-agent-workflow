"""ExpenseRouter - Workflow で RuleFinder → ExpenseChecker を実行.

ADK 2.0 Workflow pattern:
- edges define execution flow between nodes
- START → rule_finder → expense_checker (sequential)
- output_key stores result in session state
- Next agent references output via {state_key}
"""

from google.adk import Workflow
from google.adk.workflow import START

from src.agents.expense_checker import expense_checker_agent
from src.agents.rule_finder import rule_finder_agent


def create_expense_router_agent() -> Workflow:
    """ExpenseRouter Workflow を作成.

    Pipeline:
        rule_finder (output_key="extracted_rules")
        → expense_checker (reads {extracted_rules},
                           output_key="check_result")
    """
    return Workflow(
        name="expense_router",
        description=("経費精算チェックのパイプライン: ルール抽出 → 審査判定"),
        edges=[
            (
                START,
                rule_finder_agent,
                expense_checker_agent,
            ),
        ],
    )


# Default instance
expense_router_agent = create_expense_router_agent()
