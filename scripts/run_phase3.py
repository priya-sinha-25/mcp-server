"""
Phase 3 runner: load a validated pulse → publish to Google Docs via MCP.

Can be run standalone against a saved pulse.json, or called after run_phase2.py.

Usage:
    python scripts/run_phase3.py
    python scripts/run_phase3.py --pulse out/pulse.json --doc-id <GOOGLE_DOC_ID>

The Google Doc ID can also be set in .env as GOOGLE_DOC_ID.
The MCP server URL defaults to the deployed instance; override with MCP_SERVER_URL.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pulse.models import ThemeCluster, ValidationResult, WeeklyPulse
from pulse.phase03 import McpError, PublishError, UnvalidatedPulseError, publish_pulse_to_docs
from pulse.phase03.mcp_client import McpClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def load_pulse_from_file(path: Path) -> tuple[WeeklyPulse, ValidationResult]:
    """Load a pulse.json written by run_phase2.py."""
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    accepted = data.get("validation_accepted", False)
    reasons = data.get("validation_reasons", [])
    validation = ValidationResult(accepted=accepted, reasons=reasons)

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
    return pulse, validation


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3: publish pulse to Google Docs via MCP")
    parser.add_argument(
        "--pulse",
        default="out/pulse.json",
        help="Path to pulse.json from run_phase2.py (default: out/pulse.json)",
    )
    parser.add_argument(
        "--doc-id",
        default=None,
        help="Google Doc ID to publish into (overrides GOOGLE_DOC_ID in .env)",
    )
    args = parser.parse_args()

    pulse_path = ROOT / args.pulse
    if not pulse_path.is_file():
        log.error("Pulse file not found: %s", pulse_path)
        sys.exit(1)

    log.info("Loading pulse from %s", pulse_path)
    pulse, validation = load_pulse_from_file(pulse_path)

    log.info(
        "Pulse: week=%s  validation=%s  word_count=%d",
        pulse.week_label,
        "ACCEPTED" if validation.accepted else "REJECTED",
        pulse.word_count,
    )

    if not validation.accepted:
        log.error(
            "Pulse failed validation — cannot publish. Reasons: %s",
            validation.reasons,
        )
        sys.exit(1)

    try:
        client = McpClient()
        delivery = publish_pulse_to_docs(
            pulse,
            validation=validation,
            client=client,
            doc_id=args.doc_id or None,
        )
    except UnvalidatedPulseError as exc:
        log.error("Validation guard blocked publish: %s", exc)
        sys.exit(1)
    except PublishError as exc:
        log.error("Publish failed: %s", exc)
        sys.exit(1)

    print("\n" + "─" * 60)
    print("  PHASE 3 COMPLETE")
    print("─" * 60)
    print(f"  Doc ID  : {delivery.doc_id}")
    print(f"  Doc URL : {delivery.doc_url}")
    print("─" * 60 + "\n")

    log.info("Pulse successfully published to Google Docs.")


if __name__ == "__main__":
    main()
