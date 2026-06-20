"""Tests for Phase 3 publisher — mocked MCP client."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from pulse.models import DeliveryResult, ThemeCluster, ValidationResult, WeeklyPulse
from pulse.phase03.mcp_client import McpError
from pulse.phase03.publisher import PublishError, UnvalidatedPulseError, publish_pulse_to_docs

DATE_START = date(2026, 2, 15)
DATE_END = date(2026, 5, 10)
DATE_RANGE = "2026-02-15 to 2026-05-10"


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


def _mock_client(success: bool = True, raises: Exception | None = None) -> MagicMock:
    client = MagicMock()
    if raises is not None:
        client.append_to_doc.side_effect = raises
    elif success:
        client.append_to_doc.return_value = {
            "status": "success",
            "message": "Content appended to document",
            "document_id": "test_doc_123",
        }
    else:
        client.append_to_doc.return_value = {
            "status": "error",
            "message": "Google Docs API error",
        }
    return client


def _publish(pulse: WeeklyPulse, client: MagicMock, **kwargs):
    return publish_pulse_to_docs(
        pulse,
        client=client,
        date_start=DATE_START,
        date_end=DATE_END,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPublishPulseToDocs:
    def test_happy_path_returns_delivery_result(self):
        pulse = _make_pulse()
        client = _mock_client()
        result = _publish(pulse, client, doc_id="test_doc_123")
        assert isinstance(result, DeliveryResult)
        assert result.doc_id == "test_doc_123"
        assert result.doc_url is not None
        assert "test_doc_123" in result.doc_url

    def test_doc_url_is_google_docs_link(self):
        client = _mock_client()
        result = _publish(_make_pulse(), client, doc_id="abc123")
        assert result.doc_url.startswith("https://docs.google.com/document/d/")
        assert "abc123" in result.doc_url

    def test_append_called_once_with_doc_id_and_content(self):
        pulse = _make_pulse()
        client = _mock_client()
        _publish(pulse, client, doc_id="mydoc")
        client.append_to_doc.assert_called_once()
        call_kwargs = client.append_to_doc.call_args.kwargs
        assert call_kwargs["doc_id"] == "mydoc"
        assert isinstance(call_kwargs["content"], str)
        assert len(call_kwargs["content"]) > 0

    def test_content_contains_pulse_data(self):
        pulse = _make_pulse()
        client = _mock_client()
        _publish(pulse, client, doc_id="mydoc")
        content_sent = client.append_to_doc.call_args.kwargs["content"]
        assert DATE_RANGE in content_sent
        assert "High Brokerage Charges:" in content_sent
        assert "Issues dominate this week" in content_sent

    def test_missing_date_range_raises_publish_error(self):
        client = _mock_client()
        with pytest.raises(PublishError, match="date_start and date_end"):
            publish_pulse_to_docs(_make_pulse(), client=client, doc_id="mydoc")

    def test_mcp_error_raises_publish_error(self):
        client = _mock_client(raises=McpError("server unavailable"))
        with pytest.raises(PublishError, match="Failed to publish"):
            _publish(_make_pulse(), client, doc_id="mydoc")

    def test_missing_doc_id_raises_publish_error(self):
        client = _mock_client()
        with patch.dict("os.environ", {}, clear=False):
            import os
            old = os.environ.pop("GOOGLE_DOC_ID", None)
            try:
                with pytest.raises(PublishError, match="GOOGLE_DOC_ID"):
                    _publish(_make_pulse(), client)
            finally:
                if old is not None:
                    os.environ["GOOGLE_DOC_ID"] = old

    def test_product_name_appears_in_content(self):
        pulse = _make_pulse()
        client = _mock_client()
        _publish(pulse, client, doc_id="mydoc", product_name="Groww")
        content_sent = client.append_to_doc.call_args.kwargs["content"]
        assert "Groww" in content_sent


class TestValidationGuard:
    """Eval 3.2 — non-validated pulse must be refused."""

    def test_rejected_validation_raises_unvalidated_error(self):
        pulse = _make_pulse()
        client = _mock_client()
        bad_validation = ValidationResult(accepted=False, reasons=["word count exceeded"])
        with pytest.raises(UnvalidatedPulseError, match="failed validation"):
            _publish(pulse, validation=bad_validation, client=client, doc_id="mydoc")

    def test_rejected_validation_does_not_call_mcp(self):
        pulse = _make_pulse()
        client = _mock_client()
        bad_validation = ValidationResult(accepted=False, reasons=["PII detected"])
        with pytest.raises(UnvalidatedPulseError):
            _publish(pulse, validation=bad_validation, client=client, doc_id="mydoc")
        client.append_to_doc.assert_not_called()

    def test_accepted_validation_proceeds_normally(self):
        pulse = _make_pulse()
        client = _mock_client()
        good_validation = ValidationResult(accepted=True)
        result = _publish(
            pulse, validation=good_validation, client=client, doc_id="mydoc"
        )
        assert result.doc_id == "mydoc"
        client.append_to_doc.assert_called_once()

    def test_no_validation_arg_proceeds_normally(self):
        """Omitting validation= is allowed for backward-compat and scripted use."""
        pulse = _make_pulse()
        client = _mock_client()
        result = _publish(pulse, client=client, doc_id="mydoc")
        assert result.doc_id == "mydoc"
