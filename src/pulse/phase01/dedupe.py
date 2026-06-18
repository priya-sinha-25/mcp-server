"""Deduping rules (DEC-008)."""

from __future__ import annotations

import re

from pulse.models import NormalizedReview


def _normalize_body(body: str) -> str:
    text = body.lower().strip()
    return re.sub(r"\s+", " ", text)


def dedupe_reviews(
    reviews: list[NormalizedReview],
    cross_platform_days: int = 1,
) -> tuple[list[NormalizedReview], int]:
    """
    Collapse duplicates:
    1. Same platform + same calendar date + same normalized body → keep first by source_row.
    2. Cross-platform: same normalized body within cross_platform_days → keep earliest date.
    """
    removed = 0
    sorted_reviews = sorted(
        reviews, key=lambda r: (r.review_date, r.platform.value, r.source_row)
    )

    # Pass 1: same platform + date + body
    seen_platform: dict[str, NormalizedReview] = {}
    pass1: list[NormalizedReview] = []
    for r in sorted_reviews:
        key = f"{r.platform.value}|{r.review_date.isoformat()}|{_normalize_body(r.body)}"
        if key in seen_platform:
            removed += 1
            continue
        seen_platform[key] = r
        pass1.append(r)

    # Pass 2: cross-platform same body within N days
    by_body: dict[str, NormalizedReview] = {}
    final: list[NormalizedReview] = []
    for r in pass1:
        body_key = _normalize_body(r.body)
        if body_key not in by_body:
            by_body[body_key] = r
            final.append(r)
            continue

        prev = by_body[body_key]
        if prev.platform == r.platform:
            removed += 1
            continue

        delta = abs((r.review_date - prev.review_date).days)
        if delta <= cross_platform_days:
            removed += 1
            if r.review_date < prev.review_date:
                final.remove(prev)
                final.append(r)
                by_body[body_key] = r
        else:
            final.append(r)
            by_body[f"{body_key}|{r.platform.value}|{r.review_date}"] = r

    final.sort(key=lambda r: (r.review_date, r.platform.value, r.review_id))
    return final, removed
