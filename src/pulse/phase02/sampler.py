"""Stratified sampling pipeline (architecture §5.2, DEC-012).

Two-step process:
  1. pre_sample()   — proportional draw per tier, capped at n=1000.
  2. stratified_sample() — per-tier per-week caps, produces ~190 reviews.
"""

from __future__ import annotations

import random
from collections import defaultdict

from pulse.models import NormalizedReview, SampleMetadata, SampleResult
from pulse.phase02.config import SamplingConfig


def _rating_tier(rating: int) -> str:
    """Map a 1–5 star rating to a tier label."""
    if rating <= 2:
        return "neg"
    if rating == 3:
        return "neu"
    return "pos"


def pre_sample(
    reviews: list[NormalizedReview],
    n: int,
    seed: int,
) -> list[NormalizedReview]:
    """
    Step 1: Proportional pre-sample to at most *n* reviews.

    Draws proportionally from each rating tier so the natural
    sentiment distribution is preserved. Reproducible via *seed*.
    """
    if len(reviews) <= n:
        return list(reviews)

    rng = random.Random(seed)

    # Group by tier.
    tiers: dict[str, list[NormalizedReview]] = defaultdict(list)
    for r in reviews:
        tiers[_rating_tier(r.rating)].append(r)

    result: list[NormalizedReview] = []
    total = len(reviews)
    remaining = n

    tier_keys = sorted(tiers.keys())  # deterministic iteration order
    for i, tier in enumerate(tier_keys):
        bucket = tiers[tier]
        is_last = i == len(tier_keys) - 1
        if is_last:
            # Give the last tier all remaining slots to avoid rounding gaps.
            quota = remaining
        else:
            quota = round(len(bucket) / total * n)
            quota = min(quota, remaining)
        take = min(quota, len(bucket))
        result.extend(rng.sample(bucket, take))
        remaining -= take
        if remaining <= 0:
            break

    rng.shuffle(result)
    return result


def stratified_sample(
    reviews: list[NormalizedReview],
    cfg: SamplingConfig,
) -> SampleResult:
    """
    Step 2: Stratified sample — per-tier per-week caps on the pre-sampled set.

    Buckets reviews by (tier × ISO week) and applies DEC-012 caps:
      negative ≤ neg_cap/week, neutral ≤ neu_cap/week, positive ≤ pos_cap/week.

    Returns a SampleResult with the selected reviews and full SampleMetadata.
    """
    rng = random.Random(cfg.seed)

    # Pre-sample first.
    pre_sampled = pre_sample(reviews, cfg.pre_sample_n, cfg.seed)

    # Bucket by (week, tier).
    buckets: dict[tuple[int, str], list[NormalizedReview]] = defaultdict(list)
    for r in pre_sampled:
        iso_week = r.review_date.isocalendar()[1]
        tier = _rating_tier(r.rating)
        buckets[(iso_week, tier)].append(r)

    caps = {"neg": cfg.neg_cap, "neu": cfg.neu_cap, "pos": cfg.pos_cap}
    selected: list[NormalizedReview] = []
    weeks_seen: set[int] = set()
    warnings: list[str] = []

    for (week, tier), bucket in sorted(buckets.items()):
        cap = caps[tier]
        take = min(len(bucket), cap)
        chosen = rng.sample(bucket, take)
        selected.extend(chosen)
        weeks_seen.add(week)
        if len(bucket) > cap:
            warnings.append(
                f"Week {week} {tier}: {len(bucket)} available, capped at {cap}"
            )

    # Shuffle so ordering doesn't leak tier grouping to the LLM.
    rng.shuffle(selected)

    metadata = SampleMetadata(
        pre_sample_size=len(pre_sampled),
        final_sample_size=len(selected),
        seed=cfg.seed,
        neg_cap=cfg.neg_cap,
        neu_cap=cfg.neu_cap,
        pos_cap=cfg.pos_cap,
        weeks_covered=sorted(weeks_seen),
        warnings=warnings,
    )
    return SampleResult(reviews=selected, metadata=metadata)
