"""PydanticAI agent registry.

Each agent is built lazily so importing this package does not require
ANTHROPIC_API_KEY. Use the `get_*_agent()` accessors when you actually need
to run.
"""

from app.agents.deps import AgentDeps, build_agent_deps
from app.agents.financials import get_financials_agent, run_financials_agent
from app.agents.management import get_management_agent, run_management_agent
from app.agents.orchestrator import run_analysis
from app.agents.risk import get_risk_agent, run_risk_agent
from app.agents.thesis import get_thesis_agent, run_thesis_agent
from app.agents.valuation import get_valuation_agent, run_valuation_agent

__all__ = [
    "AgentDeps",
    "build_agent_deps",
    "get_financials_agent",
    "get_management_agent",
    "get_risk_agent",
    "get_thesis_agent",
    "get_valuation_agent",
    "run_analysis",
    "run_financials_agent",
    "run_management_agent",
    "run_risk_agent",
    "run_thesis_agent",
    "run_valuation_agent",
]
