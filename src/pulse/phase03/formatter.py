"""Format a validated WeeklyPulse into human-readable Google Doc content."""

from __future__ import annotations

from pulse.models import WeeklyPulse


def format_pulse_for_doc(pulse: WeeklyPulse, product_name: str = "Groww") -> str:
    """
    Render a WeeklyPulse as plain text suitable for appending to a Google Doc.

    The MCP server prepends a timestamp automatically, so we only emit the
    structured content itself. Sections are separated by blank lines for
    readability in Docs' append-text view.
    """
    lines: list[str] = []

    # --- Title ---
    lines.append(f"Weekly Review Pulse — {product_name} ({pulse.week_label})")
    lines.append("=" * 60)
    lines.append("")

    # --- Headline ---
    lines.append(f"Summary: {pulse.headline}")
    lines.append("")

    # --- Top Themes ---
    lines.append("TOP THEMES")
    lines.append("-" * 40)
    for i, theme in enumerate(pulse.top_themes, 1):
        lines.append(f"{i}. {theme.label}")
        lines.append(f"   {theme.description}")
    lines.append("")

    # --- Verbatim Quotes ---
    lines.append("VERBATIM USER QUOTES")
    lines.append("-" * 40)
    for i, quote in enumerate(pulse.quotes, 1):
        lines.append(f'{i}. "{quote}"')
    lines.append("")

    # --- Action Ideas ---
    lines.append("ACTION IDEAS")
    lines.append("-" * 40)
    for i, action in enumerate(pulse.actions, 1):
        lines.append(f"{i}. {action}")
    lines.append("")

    # --- Footer ---
    lines.append(f"Word count: {pulse.word_count} / 250")
    lines.append("=" * 60)

    return "\n".join(lines)
