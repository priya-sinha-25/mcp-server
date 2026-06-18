"""Logical data contracts (architecture §7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class Platform(str, Enum):
    APP_STORE = "app_store"
    PLAY_STORE = "play_store"


@dataclass(frozen=True)
class NormalizedReview:
    """Canonical review record after Phase 1 ingestion."""

    review_id: str
    platform: Platform
    review_date: date
    rating: int
    title: str
    body: str
    source_row: int
    version: str | None = None
    country: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "platform": self.platform.value,
            "review_date": self.review_date.isoformat(),
            "rating": self.rating,
            "title": self.title,
            "body": self.body,
            "source_row": self.source_row,
            "version": self.version,
            "country": self.country,
        }


@dataclass
class IngestMetadata:
    """Run metadata for ingestion (no PII)."""

    input_rows: int = 0
    parsed_rows: int = 0
    after_window: int = 0
    after_quality_filter: int = 0
    after_dedupe: int = 0
    dropped_empty_body: int = 0
    dropped_too_few_words: int = 0
    dropped_non_english: int = 0
    emoji_stripped: int = 0
    pii_redactions: int = 0
    warnings: list[str] = field(default_factory=list)


@dataclass
class IngestResult:
    reviews: list[NormalizedReview]
    metadata: IngestMetadata


# ---------------------------------------------------------------------------
# Phase 2 data contracts (architecture §7)
# ---------------------------------------------------------------------------


@dataclass
class SampleMetadata:
    """Sampling run metadata — enough to reproduce the sample."""

    pre_sample_size: int          # reviews after proportional pre-sample
    final_sample_size: int        # reviews sent to Stage A
    seed: int
    neg_cap: int                  # per-week caps used
    neu_cap: int
    pos_cap: int
    weeks_covered: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class SampleResult:
    """Output of the two-step sampling pipeline."""

    reviews: list[NormalizedReview]
    metadata: SampleMetadata


@dataclass
class ThemeCluster:
    """A single discovered theme from Stage A (architecture §7)."""

    theme_id: str           # short slug, e.g. "theme_1"
    label: str              # concise noun phrase, e.g. "Withdrawal Delays"
    description: str        # one-line explanation
    review_ids: list[str]   # supporting NormalizedReview.review_id values

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme_id": self.theme_id,
            "label": self.label,
            "description": self.description,
            "review_ids": self.review_ids,
        }


@dataclass
class WeeklyPulse:
    """Final deliverable from Stage B (architecture §7)."""

    week_label: str                    # e.g. "2026-W18"
    top_themes: list[ThemeCluster]     # exactly 3
    quotes: list[str]                  # exactly 3 verbatim quotes
    actions: list[str]                 # exactly 3 action ideas
    headline: str                      # optional executive framing (1 sentence)
    word_count: int                    # counted by validator

    def to_dict(self) -> dict[str, Any]:
        return {
            "week_label": self.week_label,
            "top_themes": [t.to_dict() for t in self.top_themes],
            "quotes": self.quotes,
            "actions": self.actions,
            "headline": self.headline,
            "word_count": self.word_count,
        }


@dataclass
class ValidationResult:
    """Output of validate_pulse (architecture §5.3)."""

    accepted: bool
    reasons: list[str] = field(default_factory=list)   # non-empty when rejected


@dataclass
class DeliveryResult:
    """Populated progressively by Phases 3 and 4 (architecture §7)."""

    doc_id: str | None = None
    doc_url: str | None = None
    draft_id: str | None = None
    run_id: str | None = None
    timestamp: str | None = None
