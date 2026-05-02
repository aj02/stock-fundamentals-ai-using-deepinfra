"""Tests for pure-Python valuation math."""

from __future__ import annotations

from datetime import date

import pytest

from app.schemas.valuation import HistoricalValuationPoint
from app.services.valuation import compute_medians


def _point(year: int, pe: float | None, pb: float | None) -> HistoricalValuationPoint:
    return HistoricalValuationPoint(
        period_end=date(year, 3, 31),
        fy_end_close_price=1000.0,
        eps_for_year=50.0 if pe else None,
        book_value_per_share=500.0 if pb else None,
        pe=pe,
        pb=pb,
    )


def test_medians_computed_across_full_window() -> None:
    points = [
        _point(2026, 25.0, 3.0),
        _point(2025, 20.0, 2.5),
        _point(2024, 15.0, 2.0),
        _point(2023, 10.0, 1.5),
    ]
    medians = compute_medians(points)
    assert medians.pe_median == pytest.approx(17.5)  # median of [10,15,20,25]
    assert medians.pb_median == pytest.approx(2.25)
    assert medians.pe_min == 10.0
    assert medians.pe_max == 25.0
    assert medians.years_in_window == 4


def test_negative_or_none_pe_excluded_from_medians() -> None:
    points = [
        _point(2026, 25.0, 3.0),
        _point(2025, None, 2.5),
        _point(2024, -5.0, 2.0),  # filtered: pe must be > 0
        _point(2023, 10.0, 1.5),
    ]
    medians = compute_medians(points)
    # Only positive P/Es contribute: [10, 25] → median 17.5.
    assert medians.pe_median == pytest.approx(17.5)
    # All P/Bs are positive.
    assert medians.pb_median == pytest.approx(2.25)


def test_empty_input_yields_none_medians() -> None:
    medians = compute_medians([])
    assert medians.pe_median is None
    assert medians.pb_median is None
    assert medians.years_in_window == 0
