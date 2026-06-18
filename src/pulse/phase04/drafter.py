"""Phase 4 — create Gmail draft via MCP (architecture §5.5).

create_weekly_draft(pulse, doc_url, client, to, product_name)
    → DeliveryResult with draft_id added.

Default: draft only, never auto-send (DEC-005).
Raises DraftError if the MCP call fails after retries.
Raises UnvalidatedPulseError if a rejected ValidationResult is passed.
"""

from __future__ import annotations

import logging
import os
from datetime import date, datetime

from pulse.models import DeliveryResult, ValidationResult, WeeklyPulse
from pulse.phase03.mcp_client import McpClient, McpError
from pulse.phase04.email_formatter import format_date_range, format_email_body, format_subject

log = logging.getLogger(__name__)


class DraftError(Exception):
    """Raised when the Gmail MCP call fails and cannot be retried."""


class UnvalidatedPulseError(DraftError):
    """Raised when draft is attempted with a pulse that failed validation."""


def _load_recipient() -> str:
    """Read DRAFT_RECIPIENT from environment (.env loaded by McpClient)."""
    to = os.environ.get("DRAFT_RECIPIENT", "")
    if not to:
        raise DraftError(
            "DRAFT_RECIPIENT is not set. "
            "Add it to .env — the email address the weekly draft is sent to."
        )
    return to


def create_weekly_draft(
    pulse: WeeklyPulse,
    *,
    doc_url: str | None = None,
    validation: ValidationResult | None = None,
    client: McpClient | None = None,
    to: str | None = None,
    product_name: str = "Groww",
    date_start: date | None = None,
    date_end: date | None = None,
    run_timestamp: datetime | None = None,
    delivery: DeliveryResult | None = None,
) -> DeliveryResult:
    """
    Create a Gmail draft containing the validated pulse via MCP (DEC-005).

    Args:
        pulse:        A WeeklyPulse that has passed validate_pulse().
        doc_url:      Google Doc URL from Phase 3 (included in email body).
        validation:   If supplied and not accepted, draft is refused.
        client:       Optional McpClient (constructed from env if not supplied).
        to:           Recipient email. Falls back to DRAFT_RECIPIENT env var.
        product_name: Display name used in subject and body.
        date_start:   Inclusive start of the review window (required with date_end).
        date_end:     Inclusive end of the review window (required with date_start).
        run_timestamp: Timestamp shown in the email body; defaults to now.
        delivery:     Existing DeliveryResult from Phase 3 to augment; a new
                      one is created if not provided.

    Returns:
        DeliveryResult with draft_id filled in (doc fields preserved if passed).

    Raises:
        UnvalidatedPulseError: If validation result is supplied and rejected.
        DraftError:            If the MCP call fails.
    """
    # Guard: refuse unvalidated pulse (mirrors Phase 3 pattern).
    if validation is not None and not validation.accepted:
        raise UnvalidatedPulseError(
            "Cannot create draft for a pulse that failed validation. "
            f"Reasons: {validation.reasons}"
        )

    if date_start is None or date_end is None:
        raise DraftError(
            "date_start and date_end are required for the email draft "
            "(review window bounds, e.g. from pulse.json date_range)."
        )

    mcp = client or McpClient()
    recipient = to or _load_recipient()

    date_range = format_date_range(date_start, date_end)
    subject = format_subject(product_name, date_range)
    body = format_email_body(
        pulse,
        doc_url=doc_url,
        product_name=product_name,
        date_range=date_range,
        run_timestamp=run_timestamp,
    )

    log.info(
        "Creating Gmail draft: to=%s  subject=%r", recipient, subject
    )

    try:
        result = mcp.create_email_draft(to=recipient, subject=subject, body=body)
    except McpError as exc:
        raise DraftError(
            f"Failed to create Gmail draft: {exc}"
        ) from exc

    draft_id = result.get("draft_id")
    log.info("Gmail draft created. draft_id=%s", draft_id)

    # Augment or create a DeliveryResult.
    if delivery is not None:
        delivery.draft_id = draft_id
        return delivery

    return DeliveryResult(
        doc_id=None,
        doc_url=doc_url,
        draft_id=draft_id,
    )
