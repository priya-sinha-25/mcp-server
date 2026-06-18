"""Tests for Phase 4 Gmail drafter — mocked MCP client."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from pulse.models import DeliveryResult, ThemeCluster, ValidationResult, WeeklyPulse
from pulse.phase03.mcp_client import McpError
from pulse.phase04.drafter import DraftError, UnvalidatedPulseError, create_weekly_draft


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_pulse() -> WeeklyPulse:
    return WeeklyPulse(
        week_label="2026-W23",
        top_themes=[
            ThemeCluster("t1", "High Brokerage Charges", "Fees too high.", []),
            ThemeCluster("t2", "Technical Issues", "App crashes.", []),
            ThemeCluster("t3", "Poor Customer Support", "No help.", []),
        ],
        quotes=["quote one", "quote two", "quote three"],
        actions=["action one", "action two", "action three"],
        headline="Issues dominate this week.",
        word_count=50,
    )


def _mock_client(draft_id: str = "draft_abc", raises: Exception | None = None) -> MagicMock:
    client = MagicMock()
    if raises is not None:
        client.create_email_draft.side_effect = raises
    else:
        client.create_email_draft.return_value = {
            "status": "success",
            "message": "Draft created",
            "draft_id": draft_id,
        }
    return client


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

DATE_START = date(2026, 2, 15)
DATE_END = date(2026, 5, 10)


def _draft_kwargs(**overrides):
    base = {
        "date_start": DATE_START,
        "date_end": DATE_END,
    }
    base.update(overrides)
    return base


class TestCreateWeeklyDraft:
    def test_returns_delivery_result(self):
        client = _mock_client()
        result = create_weekly_draft(_make_pulse(), client=client, to="a@b.com", **_draft_kwargs())
        assert isinstance(result, DeliveryResult)
        assert result.draft_id == "draft_abc"

    def test_mcp_called_with_correct_fields(self):
        client = _mock_client()
        create_weekly_draft(_make_pulse(), client=client, to="a@b.com", **_draft_kwargs())
        call_kwargs = client.create_email_draft.call_args.kwargs
        assert call_kwargs["to"] == "a@b.com"
        assert call_kwargs["subject"] == "Weekly pulse - Groww - 2026-02-15 to 2026-05-10"
        assert isinstance(call_kwargs["body"], str)
        assert len(call_kwargs["body"]) > 0

    def test_subject_contains_date_range_and_product(self):
        client = _mock_client()
        create_weekly_draft(
            _make_pulse(), client=client, to="a@b.com", product_name="Groww", **_draft_kwargs()
        )
        subject = client.create_email_draft.call_args.kwargs["subject"]
        assert subject == "Weekly pulse - Groww - 2026-02-15 to 2026-05-10"

    def test_body_contains_pulse_content(self):
        client = _mock_client()
        create_weekly_draft(_make_pulse(), client=client, to="a@b.com", **_draft_kwargs())
        body = client.create_email_draft.call_args.kwargs["body"]
        assert "High Brokerage Charges" in body
        assert "Issues dominate this week" in body

    def test_doc_url_included_in_body(self):
        client = _mock_client()
        create_weekly_draft(
            _make_pulse(),
            doc_url="https://docs.google.com/d/abc",
            client=client,
            to="a@b.com",
            **_draft_kwargs(),
        )
        body = client.create_email_draft.call_args.kwargs["body"]
        assert "https://docs.google.com/d/abc" in body

    def test_doc_url_preserved_in_delivery_result(self):
        client = _mock_client()
        result = create_weekly_draft(
            _make_pulse(),
            doc_url="https://docs.google.com/d/abc",
            client=client,
            to="a@b.com",
            **_draft_kwargs(),
        )
        assert result.doc_url == "https://docs.google.com/d/abc"

    def test_augments_existing_delivery_result(self):
        client = _mock_client(draft_id="draft_xyz")
        existing = DeliveryResult(doc_id="doc123", doc_url="https://docs.google.com/d/doc123")
        result = create_weekly_draft(
            _make_pulse(), client=client, to="a@b.com", delivery=existing, **_draft_kwargs()
        )
        # Same object returned with draft_id filled in.
        assert result is existing
        assert result.doc_id == "doc123"
        assert result.draft_id == "draft_xyz"


# ---------------------------------------------------------------------------
# Validation guard (DEC-005)
# ---------------------------------------------------------------------------

class TestValidationGuard:
    def test_rejected_pulse_raises_unvalidated_error(self):
        client = _mock_client()
        bad = ValidationResult(accepted=False, reasons=["word count exceeded"])
        with pytest.raises(UnvalidatedPulseError, match="failed validation"):
            create_weekly_draft(
                _make_pulse(), validation=bad, client=client, to="a@b.com", **_draft_kwargs()
            )

    def test_rejected_pulse_does_not_call_mcp(self):
        client = _mock_client()
        bad = ValidationResult(accepted=False, reasons=["PII detected"])
        with pytest.raises(UnvalidatedPulseError):
            create_weekly_draft(
                _make_pulse(), validation=bad, client=client, to="a@b.com", **_draft_kwargs()
            )
        client.create_email_draft.assert_not_called()

    def test_accepted_validation_proceeds(self):
        client = _mock_client()
        good = ValidationResult(accepted=True)
        result = create_weekly_draft(
            _make_pulse(), validation=good, client=client, to="a@b.com", **_draft_kwargs()
        )
        assert result.draft_id == "draft_abc"

    def test_no_validation_arg_proceeds(self):
        """Omitting validation= is allowed (backward-compat)."""
        client = _mock_client()
        result = create_weekly_draft(
            _make_pulse(), client=client, to="a@b.com", **_draft_kwargs()
        )
        assert result.draft_id is not None


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_mcp_error_raises_draft_error(self):
        client = _mock_client(raises=McpError("Gmail API down"))
        with pytest.raises(DraftError, match="Failed to create Gmail draft"):
            create_weekly_draft(_make_pulse(), client=client, to="a@b.com", **_draft_kwargs())

    def test_missing_recipient_raises_draft_error(self):
        client = _mock_client()
        with patch.dict("os.environ", {}, clear=False):
            import os
            old = os.environ.pop("DRAFT_RECIPIENT", None)
            try:
                with pytest.raises(DraftError, match="DRAFT_RECIPIENT"):
                    create_weekly_draft(_make_pulse(), client=client, **_draft_kwargs())
            finally:
                if old is not None:
                    os.environ["DRAFT_RECIPIENT"] = old

    def test_mcp_called_only_once_on_success(self):
        client = _mock_client()
        create_weekly_draft(_make_pulse(), client=client, to="a@b.com", **_draft_kwargs())
        assert client.create_email_draft.call_count == 1
