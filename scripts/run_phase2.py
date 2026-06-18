"""
Phase 2 runner: load normalized reviews → sample → Stage A → Stage B → validate.

Usage:
    python scripts/run_phase2.py
    python scripts/run_phase2.py --input data/groww/normalized_reviews.json
    python scripts/run_phase2.py --input data/groww/normalized_reviews.json --output out/pulse.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path

# Ensure src/ is on the path when running as a script.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pulse.models import NormalizedReview, Platform
from pulse.phase02 import (
    PulseDraftError,
    ThemeDiscoveryError,
    discover_themes,
    draft_pulse,
    load_phase2_config,
    stratified_sample,
    validate_pulse,
)
from pulse.phase02.groq_client import GroqAPIError, GroqClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_reviews(path: Path) -> list[NormalizedReview]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    reviews_raw = data.get("reviews", data) if isinstance(data, dict) else data
    reviews: list[NormalizedReview] = []
    for item in reviews_raw:
        reviews.append(
            NormalizedReview(
                review_id=item["review_id"],
                platform=Platform(item["platform"]),
                review_date=date.fromisoformat(item["review_date"]),
                rating=item["rating"],
                title=item.get("title", ""),
                body=item["body"],
                source_row=item.get("source_row", 0),
                version=item.get("version"),
                country=item.get("country"),
            )
        )
    return reviews


def derive_week_label(reviews: list[NormalizedReview]) -> str:
    """Use the ISO week of the most recent review date."""
    latest = max(r.review_date for r in reviews)
    iso = latest.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def print_pulse(pulse, result):
    sep = "─" * 60
    print(f"\n{sep}")
    print(f"  WEEKLY PULSE  {pulse.week_label}")
    print(sep)
    print(f"\n📰  {pulse.headline}\n")

    print("🔍  TOP THEMES")
    for i, t in enumerate(pulse.top_themes, 1):
        print(f"  {i}. {t.label}")
        print(f"     {t.description}")

    print("\n💬  VERBATIM QUOTES")
    for i, q in enumerate(pulse.quotes, 1):
        # Truncate very long quotes for display
        display = q if len(q) <= 160 else q[:157] + "..."
        print(f"  {i}. \"{display}\"")

    print("\n⚡  ACTION IDEAS")
    for i, a in enumerate(pulse.actions, 1):
        print(f"  {i}. {a}")

    print(f"\n📊  Word count: {pulse.word_count} / 250")
    print(f"✅  Validation: {'ACCEPTED' if result.accepted else 'REJECTED'}")
    if not result.accepted:
        for reason in result.reasons:
            print(f"   ✗ {reason}")
    print(sep)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 2 pulse generation")
    parser.add_argument(
        "--input",
        default="data/groww/normalized_reviews.json",
        help="Path to normalized_reviews.json (default: data/groww/normalized_reviews.json)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to write pulse JSON output (e.g. out/pulse.json)",
    )
    parser.add_argument(
        "--week",
        default=None,
        help="Override week label, e.g. 2026-W20",
    )
    args = parser.parse_args()

    input_path = ROOT / args.input
    if not input_path.is_file():
        log.error("Input file not found: %s", input_path)
        sys.exit(1)

    # Load config and reviews
    cfg = load_phase2_config()
    log.info("Loaded config: model=%s, pre_sample_n=%d, caps=neg%d/neu%d/pos%d",
             cfg.groq.model, cfg.sampling.pre_sample_n,
             cfg.sampling.neg_cap, cfg.sampling.neu_cap, cfg.sampling.pos_cap)

    log.info("Loading reviews from %s", input_path)
    reviews = load_reviews(input_path)
    log.info("Loaded %d normalized reviews", len(reviews))

    # Step 1+2: stratified sample
    log.info("Running stratified sample...")
    sample_result = stratified_sample(reviews, cfg.sampling)
    meta = sample_result.metadata
    log.info(
        "Sample: pre=%d → final=%d reviews across %d weeks (seed=%d)",
        meta.pre_sample_size, meta.final_sample_size,
        len(meta.weeks_covered), meta.seed,
    )
    review_dates = [r.review_date for r in reviews]
    date_start = min(review_dates)
    date_end = max(review_dates)
    for w in meta.warnings:
        log.debug("  sampler: %s", w)

    week_label = args.week or derive_week_label(reviews)
    log.info("Week label: %s", week_label)

    # Init Groq client (loads .env automatically)
    try:
        client = GroqClient()
    except GroqAPIError as exc:
        log.error("%s", exc)
        sys.exit(1)

    # Stage A: theme discovery
    log.info("Stage A — discovering themes via Groq (%s)...", cfg.groq.model)
    try:
        clusters = discover_themes(sample_result.reviews, cfg, client)
    except ThemeDiscoveryError as exc:
        log.error("Theme discovery failed: %s", exc)
        sys.exit(1)

    log.info("Discovered %d themes:", len(clusters))
    for c in clusters:
        log.info("  [%s] %s — %s (%d reviews)",
                 c.theme_id, c.label, c.description, len(c.review_ids))

    # Stage B: pulse drafting
    log.info("Stage B — drafting pulse via Groq...")
    try:
        pulse = draft_pulse(clusters, reviews, week_label, cfg, client)
    except PulseDraftError as exc:
        log.error("Pulse drafting failed: %s", exc)
        sys.exit(1)

    # Validate
    log.info("Validating pulse...")
    validation = validate_pulse(pulse, reviews)

    # Print results
    print_pulse(pulse, validation)

    if not validation.accepted:
        log.warning("Pulse did not pass validation — see reasons above.")
    else:
        log.info("Pulse accepted by validator.")

    # Optionally save to file
    if args.output:
        out_path = ROOT / args.output
        out_path.parent.mkdir(parents=True, exist_ok=True)
        output = {
            "run_timestamp": datetime.utcnow().isoformat() + "Z",
            "week_label": pulse.week_label,
            "date_range": {
                "start": date_start.isoformat(),
                "end": date_end.isoformat(),
            },
            "validation_accepted": validation.accepted,
            "validation_reasons": validation.reasons,
            "sample_metadata": {
                "pre_sample_size": meta.pre_sample_size,
                "final_sample_size": meta.final_sample_size,
                "seed": meta.seed,
                "weeks_covered": meta.weeks_covered,
                "neg_cap": meta.neg_cap,
                "neu_cap": meta.neu_cap,
                "pos_cap": meta.pos_cap,
            },
            "pulse": pulse.to_dict(),
            "all_themes": [c.to_dict() for c in clusters],
        }
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        log.info("Pulse saved to %s", out_path)


if __name__ == "__main__":
    main()
