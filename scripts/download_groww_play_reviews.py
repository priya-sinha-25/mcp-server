#!/usr/bin/env python3
"""
Download public Google Play reviews for Groww (com.nextbillion.groww).

Source: public Play Store listing / "See all reviews" data (same app page as):
https://play.google.com/store/apps/details?id=com.nextbillion.groww&hl=en_IN

Writes a Play Console–compatible CSV for Phase 1 ingestion.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google_play_scraper import Sort, reviews

PACKAGE = "com.nextbillion.groww"
DEFAULT_OUTPUT = Path("data/groww/groww_play_store_reviews.csv")

CSV_HEADERS = [
    "Package Name",
    "App Version Name",
    "Review Submit Date and Time",
    "Star Rating",
    "Review Title",
    "Review Text",
    "Reviewer Name",
    "Device",
]


def fetch_reviews(
    *,
    lookback_weeks: int = 12,
    lang: str = "en",
    country: str = "in",
    batch_size: int = 200,
    max_pages: int = 100,
    pause_seconds: float = 0.5,
) -> list[dict]:
    """Paginate newest-first until reviews are older than lookback window."""
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=lookback_weeks)
    collected: list[dict] = []
    token = None

    for page in range(max_pages):
        kwargs = {
            "lang": lang,
            "country": country,
            "sort": Sort.NEWEST,
            "count": batch_size,
        }
        if token:
            batch, token = reviews(PACKAGE, continuation_token=token, **kwargs)
        else:
            batch, token = reviews(PACKAGE, **kwargs)

        if not batch:
            break

        reached_cutoff = False
        for item in batch:
            at = item["at"]
            if at.tzinfo is None:
                at = at.replace(tzinfo=timezone.utc)
            else:
                at = at.astimezone(timezone.utc)
            if at < cutoff:
                reached_cutoff = True
                break
            collected.append(item)

        if reached_cutoff or not token:
            break

        time.sleep(pause_seconds)

    return collected


def write_csv(rows: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for r in rows:
            at: datetime = r["at"]
            if at.tzinfo is None:
                at = at.replace(tzinfo=timezone.utc)
            writer.writerow(
                {
                    "Package Name": PACKAGE,
                    "App Version Name": r.get("reviewCreatedVersion") or "",
                    "Review Submit Date and Time": at.strftime("%Y-%m-%d %H:%M:%S"),
                    "Star Rating": r.get("score", ""),
                    "Review Title": "",
                    "Review Text": (r.get("content") or "").replace("\n", " ").strip(),
                    "Reviewer Name": "",
                    "Device": "",
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Groww Play Store reviews")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"CSV output path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--weeks",
        type=int,
        default=12,
        help="Lookback weeks to fetch (8-12 recommended)",
    )
    parser.add_argument("--lang", default="en")
    parser.add_argument("--country", default="in")
    args = parser.parse_args()

    if not (8 <= args.weeks <= 12):
        print("Warning: weeks outside 8-12 milestone range; using anyway.", file=sys.stderr)

    print(f"Fetching reviews for {PACKAGE} (last {args.weeks} weeks)...")
    try:
        rows = fetch_reviews(lookback_weeks=args.weeks, lang=args.lang, country=args.country)
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        sys.exit(1)

    if not rows:
        print("No reviews returned.", file=sys.stderr)
        sys.exit(1)

    write_csv(rows, args.output)
    dates = [r["at"] for r in rows]
    oldest = min(dates)
    newest = max(dates)
    print(f"Saved {len(rows)} reviews to {args.output}")
    print(f"Date range: {oldest.date()} .. {newest.date()}")


if __name__ == "__main__":
    main()
