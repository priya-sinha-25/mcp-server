"""CLI for Phase 1 ingestion."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pulse.phase01.ingest import ingest_reviews
from pulse.phase01.parsers import ParseError


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest store review exports (Phase 1)")
    parser.add_argument("exports", nargs="+", help="CSV export file path(s)")
    parser.add_argument("--config", type=Path, default=None, help="product.yaml path")
    parser.add_argument("--output", type=Path, default=None, help="Write JSON output")
    args = parser.parse_args()

    try:
        result = ingest_reviews(args.exports, config_path=args.config)
    except (ParseError, ValueError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    payload = {
        "reviews": [r.to_dict() for r in result.reviews],
        "metadata": {
            "parsed_rows": result.metadata.parsed_rows,
            "after_window": result.metadata.after_window,
            "after_quality_filter": result.metadata.after_quality_filter,
            "after_dedupe": result.metadata.after_dedupe,
            "dropped_too_few_words": result.metadata.dropped_too_few_words,
            "dropped_non_english": result.metadata.dropped_non_english,
            "dropped_empty_body": result.metadata.dropped_empty_body,
            "emoji_stripped": result.metadata.emoji_stripped,
            "pii_redactions": result.metadata.pii_redactions,
            "warnings": result.metadata.warnings,
        },
    }

    text = json.dumps(payload, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote {len(result.reviews)} reviews to {args.output}")
    else:
        print(text)


if __name__ == "__main__":
    main()
