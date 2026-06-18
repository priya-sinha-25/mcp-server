"""
Phase 4 runner: load a validated pulse + Doc URL -> create Gmail draft via MCP.

Can be run standalone against a saved pulse.json, or chained after run_phase3.py.

Usage:
    python scripts/run_phase4.py
    python scripts/run_phase4.py --pulse out/pulse.json --to someone@example.com
    python scripts/run_phase4.py --doc-url https://docs.google.com/...

DRAFT_RECIPIENT in .env is the default recipient (overridden by --to).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pulse.models import DeliveryResult, ThemeCluster, ValidationResult, WeeklyPulse
from pulse.phase03.mcp_client import McpClient
from pulse.phase04 import DraftError, UnvalidatedPulseError, create_weekly_draft

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def load_pulse_from_file(
    path: Path,
) -> tuple[WeeklyPulse, ValidationResult, str | None, date | None, date | None, datetime | None]:
    """Load pulse.json written by run_phase2.py; return pulse, validation, doc_url, dates."""
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    accepted = data.get("validation_accepted", False)
    reasons = data.get("validation_reasons", [])
    validation = ValidationResult(accepted=accepted, reasons=reasons)

    # Doc URL may have been saved by a previous phase 3 run.
    doc_url: str | None = data.get("doc_url")

    date_start: date | None = None
    date_end: date | None = None
    raw_range = data.get("date_range")
    if isinstance(raw_range, dict):
        if raw_range.get("start"):
            date_start = date.fromisoformat(raw_range["start"])
        if raw_range.get("end"):
            date_end = date.fromisoformat(raw_range["end"])

    run_timestamp: datetime | None = None
    raw_ts = data.get("run_timestamp")
    if raw_ts:
        run_timestamp = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))

    p = data["pulse"]
    top_themes = [
        ThemeCluster(
            theme_id=t["theme_id"],
            label=t["label"],
            description=t["description"],
            review_ids=t.get("review_ids", []),
        )
        for t in p["top_themes"]
    ]
    pulse = WeeklyPulse(
        week_label=p["week_label"],
        top_themes=top_themes,
        quotes=p["quotes"],
        actions=p["actions"],
        headline=p["headline"],
        word_count=p.get("word_count", 0),
    )
    return pulse, validation, doc_url, date_start, date_end, run_timestamp


def derive_date_range_from_reviews(path: Path) -> tuple[date, date]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    reviews_raw = data.get("reviews", data) if isinstance(data, dict) else data
    dates = [date.fromisoformat(item["review_date"]) for item in reviews_raw]
    return min(dates), max(dates)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 4: create Gmail draft via MCP")
    parser.add_argument(
        "--pulse",
        default="out/pulse.json",
        help="Path to pulse.json from run_phase2.py (default: out/pulse.json)",
    )
    parser.add_argument(
        "--to",
        default=None,
        help="Recipient email (overrides DRAFT_RECIPIENT in .env)",
    )
    parser.add_argument(
        "--doc-url",
        default=None,
        help="Google Doc URL to include in email body (optional)",
    )
    parser.add_argument(
        "--reviews",
        default="data/groww/normalized_reviews.json",
        help="Path to normalized reviews for date-range fallback (default: data/groww/normalized_reviews.json)",
    )
    args = parser.parse_args()

    pulse_path = ROOT / args.pulse
    if not pulse_path.is_file():
        log.error("Pulse file not found: %s", pulse_path)
        sys.exit(1)

    log.info("Loading pulse from %s", pulse_path)
    pulse, validation, saved_doc_url, date_start, date_end, run_timestamp = load_pulse_from_file(
        pulse_path
    )

    if date_start is None or date_end is None:
        reviews_path = ROOT / args.reviews
        if not reviews_path.is_file():
            log.error(
                "Pulse file has no date_range and reviews file not found: %s",
                reviews_path,
            )
            sys.exit(1)
        date_start, date_end = derive_date_range_from_reviews(reviews_path)
        log.info("Derived date range from reviews: %s to %s", date_start, date_end)

    doc_url = args.doc_url or saved_doc_url
    if doc_url:
        log.info("Doc URL: %s", doc_url)

    log.info(
        "Pulse: week=%s  validation=%s  word_count=%d",
        pulse.week_label,
        "ACCEPTED" if validation.accepted else "REJECTED",
        pulse.word_count,
    )

    if not validation.accepted:
        log.error(
            "Pulse failed validation — cannot create draft. Reasons: %s",
            validation.reasons,
        )
        sys.exit(1)

    try:
        client = McpClient()
        delivery = create_weekly_draft(
            pulse,
            doc_url=doc_url,
            validation=validation,
            client=client,
            to=args.to or None,
            date_start=date_start,
            date_end=date_end,
            run_timestamp=run_timestamp,
        )
    except UnvalidatedPulseError as exc:
        log.error("Validation guard blocked draft: %s", exc)
        sys.exit(1)
    except DraftError as exc:
        log.error("Draft creation failed: %s", exc)
        sys.exit(1)

    print("\n" + "─" * 60)
    print("  PHASE 4 COMPLETE")
    print("─" * 60)
    print(f"  Draft ID : {delivery.draft_id}")
    if delivery.doc_url:
        print(f"  Doc URL  : {delivery.doc_url}")
    print("─" * 60 + "\n")

    log.info("Gmail draft created. Review it in Gmail Drafts before sending.")


if __name__ == "__main__":
    main()
