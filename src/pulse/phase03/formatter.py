"""Format a validated WeeklyPulse into Google Doc content."""

from __future__ import annotations

from datetime import datetime

from pulse.models import WeeklyPulse
from pulse.phase04.email_formatter import format_email_body


def format_pulse_for_doc(
    pulse: WeeklyPulse,
    product_name: str = "Groww",
    *,
    date_range: str,
    run_timestamp: datetime | None = None,
) -> str:
    """
    Render a WeeklyPulse using the same body template as the Gmail draft.

    The Doc link is omitted because the reader is already in the document.
    The MCP server prepends its own append timestamp before this content.
    """
    return format_email_body(
        pulse,
        doc_url=None,
        product_name=product_name,
        date_range=date_range,
        run_timestamp=run_timestamp,
        include_doc_link=False,
    )
