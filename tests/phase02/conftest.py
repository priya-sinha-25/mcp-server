"""Shared fixtures for Phase 2 tests."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from pulse.models import NormalizedReview, Platform, ThemeCluster, WeeklyPulse
from pulse.phase02.config import GroqConfig, Phase2Config, SamplingConfig


# ---------------------------------------------------------------------------
# Review corpus helpers
# ---------------------------------------------------------------------------

def _make_review(
    review_id: str,
    rating: int,
    body: str,
    week_offset: int = 0,
    platform: Platform = Platform.PLAY_STORE,
) -> NormalizedReview:
    base = date(2026, 3, 2)  # a Monday (week 10)
    review_date = base + timedelta(weeks=week_offset)
    return NormalizedReview(
        review_id=review_id,
        platform=platform,
        review_date=review_date,
        rating=rating,
        title="",
        body=body,
        source_row=1,
    )


@pytest.fixture
def small_corpus() -> list[NormalizedReview]:
    """30 reviews across 3 weeks, balanced across tiers."""
    reviews: list[NormalizedReview] = []
    for week in range(3):
        for i in range(4):  # 4 negative per week
            reviews.append(_make_review(
                f"neg_w{week}_{i}", 1,
                f"Cannot withdraw funds since last update week {week} review {i} terrible experience",
                week_offset=week,
            ))
        for i in range(3):  # 3 neutral per week
            reviews.append(_make_review(
                f"neu_w{week}_{i}", 3,
                f"App works okay but charts need improvement week {week} review {i} average experience",
                week_offset=week,
            ))
        for i in range(3):  # 3 positive per week
            reviews.append(_make_review(
                f"pos_w{week}_{i}", 5,
                f"Best investment app easy transfers smooth onboarding week {week} review {i}",
                week_offset=week,
            ))
    return reviews


@pytest.fixture
def large_corpus() -> list[NormalizedReview]:
    """1500 reviews for pre-sampling tests."""
    reviews: list[NormalizedReview] = []
    for i in range(800):
        reviews.append(_make_review(
            f"neg_{i}", 1,
            f"App crashes during trading session order not executed failure number {i}",
            week_offset=i % 10,
        ))
    for i in range(200):
        reviews.append(_make_review(
            f"neu_{i}", 3,
            f"Average performance could be better mutual fund section needs work {i}",
            week_offset=i % 10,
        ))
    for i in range(500):
        reviews.append(_make_review(
            f"pos_{i}", 5,
            f"Excellent app best trading platform easy to use smooth experience {i}",
            week_offset=i % 10,
        ))
    return reviews


@pytest.fixture
def default_cfg() -> Phase2Config:
    return Phase2Config(
        sampling=SamplingConfig(
            pre_sample_n=1000,
            neg_cap=7,
            neu_cap=3,
            pos_cap=5,
            seed=42,
        ),
        groq=GroqConfig(
            model="llama-3.3-70b-versatile",
            stage_a_temperature=0.2,
            stage_b_temperature=0.5,
            max_themes=5,
            max_retries=2,
            min_tpd_headroom=3000,
        ),
    )


# ---------------------------------------------------------------------------
# Groq mock helpers
# ---------------------------------------------------------------------------

import json
from unittest.mock import MagicMock

from pulse.phase02.groq_client import GroqClient


def make_mock_client(response: str | Exception) -> GroqClient:
    """Return a GroqClient whose chat_completion is mocked."""
    client = MagicMock(spec=GroqClient)
    if isinstance(response, Exception):
        client.chat_completion.side_effect = response
    else:
        client.chat_completion.return_value = response
    return client


def stage_a_response(
    themes: list[dict],
) -> str:
    return json.dumps({"themes": themes})


def stage_b_response(
    week_label: str = "2026-W18",
    top_themes: list[dict] | None = None,
    quotes: list[str] | None = None,
    actions: list[str] | None = None,
    headline: str = "Users face withdrawal and trading issues this week.",
) -> str:
    if top_themes is None:
        top_themes = [
            {"theme_id": "theme_1", "label": "Withdrawal Delays", "description": "Users report funds stuck", "review_ids": []},
            {"theme_id": "theme_2", "label": "Trading Failures", "description": "Orders not executed", "review_ids": []},
            {"theme_id": "theme_3", "label": "Good UI", "description": "Interface praised", "review_ids": []},
        ]
    if quotes is None:
        quotes = [
            "Cannot withdraw funds since last update week 0 review 0 terrible experience",
            "App crashes during trading session order not executed failure number 0",
            "Best investment app easy transfers smooth onboarding week 0 review 0",
        ]
    if actions is None:
        actions = [
            "Fix withdrawal processing pipeline to resolve stuck transactions",
            "Improve order execution reliability during high-traffic periods",
            "Add real-time status updates for pending transactions",
        ]
    return json.dumps({
        "week_label": week_label,
        "headline": headline,
        "top_themes": top_themes,
        "quotes": quotes,
        "actions": actions,
    })


@pytest.fixture
def mock_themes() -> list[ThemeCluster]:
    return [
        ThemeCluster("theme_1", "Withdrawal Delays", "Funds stuck for days", ["neg_w0_0", "neg_w0_1"]),
        ThemeCluster("theme_2", "Trading Failures", "Orders not executed", ["neg_w0_2", "neg_w0_3"]),
        ThemeCluster("theme_3", "Positive UX", "Interface is praised", ["pos_w0_0"]),
        ThemeCluster("theme_4", "Chart Issues", "Charts hard to read", ["neu_w0_0"]),
        ThemeCluster("theme_5", "Support Quality", "Support team unhelpful", ["neg_w1_0"]),
    ]


@pytest.fixture
def valid_pulse(small_corpus) -> WeeklyPulse:
    """A pulse that passes all validation checks — quotes drawn from small_corpus."""
    return WeeklyPulse(
        week_label="2026-W10",
        top_themes=[
            ThemeCluster("theme_1", "Withdrawal Delays", "Funds stuck for days", ["neg_w0_0"]),
            ThemeCluster("theme_2", "Trading Failures", "Orders not executed", ["neg_w0_1"]),
            ThemeCluster("theme_3", "Positive UX", "Easy transfers praised", ["pos_w0_0"]),
        ],
        # Exact body strings from small_corpus (neg_w0_0, neg_w0_1, pos_w0_0).
        quotes=[
            small_corpus[0].body,   # neg_w0_0
            small_corpus[1].body,   # neg_w0_1
            small_corpus[9].body,   # pos_w0_0
        ],
        actions=[
            "Fix withdrawal processing to unblock stuck transactions",
            "Improve order execution during peak trading hours",
            "Add transaction status push notifications for users",
        ],
        headline="Withdrawal and trading failures dominate negative feedback this week.",
        word_count=0,  # validator recounts
    )
