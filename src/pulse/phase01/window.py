"""Time windowing for 8–12 week lookback (inclusive, UTC calendar dates)."""

from __future__ import annotations

from datetime import date, timedelta


def lookback_bounds(
    reference_date: date,
    lookback_weeks: int,
) -> tuple[date, date]:
    """
    Return (start_date, end_date) inclusive.
    end_date is reference_date; start_date is lookback_weeks * 7 days before.
    """
    end_date = reference_date
    start_date = reference_date - timedelta(days=lookback_weeks * 7 - 1)
    return start_date, end_date


def in_window(review_date: date, start: date, end: date) -> bool:
    return start <= review_date <= end
