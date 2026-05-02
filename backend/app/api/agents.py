"""HTTP endpoint for running individual agents in isolation.

STEP 4 PURPOSE: lets a developer hit the Financials Agent end-to-end via
plain HTTP without the orchestrator. The orchestrator (step 8) becomes the
public entry point — these temp endpoints will be folded under `/internal`
or removed once the orchestrator covers them.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.agents.deps import build_agent_deps
from app.agents.financials import run_financials_agent
from app.agents.management import run_management_agent
from app.agents.risk import run_risk_agent
from app.agents.valuation import run_valuation_agent
from app.core.config import DISCLAIMER
from app.schemas.agents import FinancialsReport
from app.schemas.management import ManagementReport
from app.schemas.risk import RiskReport
from app.schemas.valuation import ValuationReport

router = APIRouter(prefix="/agents", tags=["agents"])
log = structlog.get_logger(__name__)


class FinancialsAgentResponse(BaseModel):
    report: FinancialsReport
    disclaimer: str = Field(default=DISCLAIMER)


class ValuationAgentResponse(BaseModel):
    report: ValuationReport
    disclaimer: str = Field(default=DISCLAIMER)


class ManagementAgentResponse(BaseModel):
    report: ManagementReport
    disclaimer: str = Field(default=DISCLAIMER)


class RiskAgentResponse(BaseModel):
    report: RiskReport
    disclaimer: str = Field(default=DISCLAIMER)


@router.post(
    "/financials/{ticker}",
    response_model=FinancialsAgentResponse,
    summary="Run the Financials Agent in isolation (step 4 dev endpoint).",
)
async def run_financials_endpoint(ticker: str) -> FinancialsAgentResponse:
    deps, stack = await build_agent_deps()
    try:
        try:
            report = await run_financials_agent(ticker, deps)
        except RuntimeError as e:
            log.warning("agents.financials.runtime_error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e),
            ) from e
    finally:
        await stack.aclose()
    return FinancialsAgentResponse(report=report)


@router.post(
    "/valuation/{ticker}",
    response_model=ValuationAgentResponse,
    summary="Run the Valuation Agent in isolation (step 5 dev endpoint).",
)
async def run_valuation_endpoint(ticker: str) -> ValuationAgentResponse:
    deps, stack = await build_agent_deps()
    try:
        try:
            report = await run_valuation_agent(ticker, deps)
        except RuntimeError as e:
            log.warning("agents.valuation.runtime_error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e),
            ) from e
    finally:
        await stack.aclose()
    return ValuationAgentResponse(report=report)


@router.post(
    "/management/{ticker}",
    response_model=ManagementAgentResponse,
    summary="Run the Management Agent in isolation (step 6 dev endpoint).",
)
async def run_management_endpoint(ticker: str) -> ManagementAgentResponse:
    deps, stack = await build_agent_deps()
    try:
        try:
            report = await run_management_agent(ticker, deps)
        except RuntimeError as e:
            log.warning("agents.management.runtime_error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e),
            ) from e
    finally:
        await stack.aclose()
    return ManagementAgentResponse(report=report)


@router.post(
    "/risk/{ticker}",
    response_model=RiskAgentResponse,
    summary="Run the Risk Agent in isolation (step 7 dev endpoint).",
)
async def run_risk_endpoint(ticker: str) -> RiskAgentResponse:
    deps, stack = await build_agent_deps()
    try:
        try:
            report = await run_risk_agent(ticker, deps)
        except RuntimeError as e:
            log.warning("agents.risk.runtime_error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e),
            ) from e
    finally:
        await stack.aclose()
    return RiskAgentResponse(report=report)
