"""Phase 3 — publish validated pulse to Google Docs via MCP (architecture §5.4).

publish_pulse_to_docs(pulse, client, doc_id, product_name)
    → DeliveryResult with doc_id and doc_url populated.

Only accepts a pulse that has already passed validate_pulse().
Raises PublishError if the MCP call fails after retries.
"""

from __future__ import annotations

import logging
import os
from datetime import date, datetime
from pathlib import Path

from pulse.models import DeliveryResult, ValidationResult, WeeklyPulse
from pulse.phase03.formatter import format_pulse_for_doc
from pulse.phase03.mcp_client import McpClient, McpError
from pulse.phase04.email_formatter import format_date_range

log = logging.getLogger(__name__)

DOCS_BASE_URL = "https://docs.google.com/document/d/{doc_id}/edit"


class PublishError(Exception):
    """Raised when the Docs MCP call fails and cannot be retried."""


class UnvalidatedPulseError(PublishError):
    """Raised when publish is attempted with a pulse that failed validation."""


def _load_doc_id() -> str:
    """Read GOOGLE_DOC_ID from environment (loaded from .env by McpClient)."""
    doc_id = os.environ.get("GOOGLE_DOC_ID", "")
    if not doc_id:
        raise PublishError(
            "GOOGLE_DOC_ID is not set. "
            "Add it to .env — set it to the ID of the Google Doc you want to write to."
        )
    return doc_id


def publish_pulse_to_docs(
    pulse: WeeklyPulse,
    *,
    validation: ValidationResult | None = None,
    client: McpClient | None = None,
    doc_id: str | None = None,
    product_name: str = "Groww",
    date_start: date | None = None,
    date_end: date | None = None,
    run_timestamp: datetime | None = None,
) -> DeliveryResult:
    """
    Append the validated pulse to the configured Google Doc via MCP.

    Args:
        pulse:        A WeeklyPulse that has passed validate_pulse().
        validation:   The ValidationResult from validate_pulse(). If supplied
                      and not accepted, publish is refused (eval 3.2).
        client:       Optional McpClient (constructed from env if not supplied).
        doc_id:       Target Google Doc ID. Falls back to GOOGLE_DOC_ID env var.
        product_name: Display name used in the Doc header.
        date_start:   Inclusive start of the review window.
        date_end:     Inclusive end of the review window.
        run_timestamp: Timestamp shown in the Doc body; defaults to now.

    Returns:
        DeliveryResult with doc_id and doc_url filled in.

    Raises:
        UnvalidatedPulseError: If validation result is supplied and rejected.
        PublishError: If the MCP call fails.
    """
    # Guard: refuse to publish a pulse that failed validation (eval 3.2).
    if validation is not None and not validation.accepted:
        raise UnvalidatedPulseError(
            "Cannot publish a pulse that failed validation. "
            f"Reasons: {validation.reasons}"
        )

    mcp = client or McpClient()
    target_doc_id = doc_id or _load_doc_id()

    if date_start is None or date_end is None:
        raise PublishError(
            "date_start and date_end are required for Google Docs publish "
            "(review window bounds, e.g. from pulse.json date_range)."
        )

    date_range = format_date_range(date_start, date_end)
    content = format_pulse_for_doc(
        pulse,
        product_name=product_name,
        date_range=date_range,
        run_timestamp=run_timestamp,
    )

    log.info(
        "Publishing pulse %s (%s) to Google Doc %s…",
        pulse.week_label,
        date_range,
        target_doc_id,
    )

    try:
        result = mcp.append_to_doc(doc_id=target_doc_id, content=content)
    except McpError as exc:
        raise PublishError(
            f"Failed to publish pulse to Google Docs: {exc}"
        ) from exc

    doc_url = DOCS_BASE_URL.format(doc_id=target_doc_id)
    log.info("Pulse published. Doc URL: %s", doc_url)

    return DeliveryResult(
        doc_id=target_doc_id,
        doc_url=doc_url,
    )
