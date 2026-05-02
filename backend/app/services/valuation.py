"""Pure-Python historical valuation math.

Same discipline as `services.ratios`: the LLM never does arithmetic. The
agent calls `compute_historical_medians` as a tool, which delegates here.
"""

from __future__ import annotations

import statistics

from app.schemas.valuation import (
    HistoricalMedians,
    HistoricalValuation,
    HistoricalValuationPoint,
)


def _safe_median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def compute_medians(points: list[HistoricalValuationPoint]) -> HistoricalMedians:
    pe_values = [p.pe for p in points if p.pe is not None and p.pe > 0]
    pb_values = [p.pb for p in points if p.pb is not None and p.pb > 0]

    return HistoricalMedians(
        pe_median=_safe_median(pe_values),
        pb_median=_safe_median(pb_values),
        pe_min=min(pe_values) if pe_values else None,
        pe_max=max(pe_values) if pe_values else None,
        pb_min=min(pb_values) if pb_values else None,
        pb_max=max(pb_values) if pb_values else None,
        years_in_window=len({p.period_end.year for p in points}),
    )


def assemble_historical_valuation(
    points: list[HistoricalValuationPoint],
) -> HistoricalValuation:
    return HistoricalValuation(
        yearly=sorted(points, key=lambda p: p.period_end, reverse=True),
        medians=compute_medians(points),
    )
