"""Format a validated WeeklyPulse into a Gmail draft subject + body (architecture §5.5).

Body policy: link-first — Doc URL near the top, then themes / quotes / actions inline.
"""

from __future__ import annotations

from datetime import date, datetime

from pulse.models import WeeklyPulse


def format_date_range(start: date, end: date) -> str:
    """e.g. '2026-02-15 to 2026-05-10'"""
    return f"{start.isoformat()} to {end.isoformat()}"


def format_subject(
    product_name: str,
    date_range: str,
) -> str:
    """e.g. 'Weekly pulse - Groww - 2026-02-15 to 2026-05-10'"""
    return f"Weekly pulse - {product_name} - {date_range}"


def format_email_body(
    pulse: WeeklyPulse,
    doc_url: str | None = None,
    product_name: str = "Groww",
    *,
    date_range: str,
    run_timestamp: datetime | None = None,
    include_doc_link: bool = True,
) -> str:
    """
    Render pulse as an email body.

    Structure mirrors the operator draft template:
        subject line (repeated)
        [timestamp]
        intro sentence with date range
        summary
        canonical Doc link (if available)
        top themes, user quotes, action ideas
    """
    ts = (run_timestamp or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    subject_line = format_subject(product_name, date_range)

    lines: list[str] = [
        subject_line,
        f"[{ts}]",
        f"Weekly review pulse for {product_name} ({date_range}).",
        f"Summary: {pulse.headline}",
        "",
    ]

    if doc_url and include_doc_link:
        lines.append(f"Canonical pulse (Google Doc): {doc_url}")
        lines.append("")

    lines.append("Top themes:")
    for i, theme in enumerate(pulse.top_themes, 1):
        lines.append(f"{i}. {theme.label}: {theme.description}")
    lines.append("")

    lines.append("User quotes:")
    for quote in pulse.quotes:
        lines.append(f'- "{quote}"')
    lines.append("")

    lines.append("Action ideas:")
    for action in pulse.actions:
        lines.append(f"- {action}")

    return "\n".join(lines)
