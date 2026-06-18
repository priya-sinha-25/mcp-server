"""Tests for the pulse → email subject + body formatter."""

from __future__ import annotations

from datetime import date, datetime

from pulse.models import ThemeCluster, WeeklyPulse
from pulse.phase04.email_formatter import (
    format_date_range,
    format_email_body,
    format_subject,
)

DATE_RANGE = "2026-02-15 to 2026-05-10"
RUN_TS = datetime(2026, 5, 15, 14, 56, 37)


def _make_pulse() -> WeeklyPulse:
    return WeeklyPulse(
        week_label="2026-W23",
        top_themes=[
            ThemeCluster("t1", "High Brokerage Charges",
                         "Users complain about fees eating into profits.", []),
            ThemeCluster("t2", "Technical Issues",
                         "Glitches and slow execution hinder trading.", []),
            ThemeCluster("t3", "Poor Customer Support",
                         "Unhelpful agents and long wait times.", []),
        ],
        quotes=[
            "fraud application, minimum charges increased to rs 5",
            "agent cut call purposefully and never called back",
            "maximum technical glitch. unable to connect with customer care.",
        ],
        actions=[
            "Reduce brokerage charges to stay competitive",
            "Improve app stability and fix technical issues",
            "Enhance customer support with trained staff",
        ],
        headline="High charges and technical issues dominate this week.",
        word_count=139,
    )


class TestFormatDateRange:
    def test_iso_dates(self):
        assert format_date_range(date(2026, 2, 15), date(2026, 5, 10)) == DATE_RANGE


class TestFormatSubject:
    def test_contains_product_name(self):
        assert "Groww" in format_subject("Groww", DATE_RANGE)

    def test_contains_date_range(self):
        assert DATE_RANGE in format_subject("Groww", DATE_RANGE)

    def test_format_pattern(self):
        assert format_subject("Groww", DATE_RANGE) == f"Weekly pulse - Groww - {DATE_RANGE}"


class TestFormatEmailBody:
    def test_contains_subject_line(self):
        body = format_email_body(_make_pulse(), date_range=DATE_RANGE, run_timestamp=RUN_TS)
        assert body.startswith(f"Weekly pulse - Groww - {DATE_RANGE}")

    def test_contains_timestamp(self):
        body = format_email_body(_make_pulse(), date_range=DATE_RANGE, run_timestamp=RUN_TS)
        assert "[2026-05-15 14:56:37]" in body

    def test_contains_intro_with_date_range(self):
        body = format_email_body(_make_pulse(), date_range=DATE_RANGE, run_timestamp=RUN_TS)
        assert f"Weekly review pulse for Groww ({DATE_RANGE})." in body

    def test_contains_headline(self):
        body = format_email_body(_make_pulse(), date_range=DATE_RANGE, run_timestamp=RUN_TS)
        assert "Summary: High charges and technical issues" in body

    def test_contains_all_themes(self):
        body = format_email_body(_make_pulse(), date_range=DATE_RANGE, run_timestamp=RUN_TS)
        assert "High Brokerage Charges:" in body
        assert "Technical Issues:" in body
        assert "Poor Customer Support:" in body

    def test_contains_all_quotes(self):
        body = format_email_body(_make_pulse(), date_range=DATE_RANGE, run_timestamp=RUN_TS)
        assert "fraud application" in body
        assert "agent cut call purposefully" in body
        assert "maximum technical glitch" in body

    def test_contains_all_actions(self):
        body = format_email_body(_make_pulse(), date_range=DATE_RANGE, run_timestamp=RUN_TS)
        assert "Reduce brokerage charges" in body
        assert "Improve app stability" in body
        assert "Enhance customer support" in body

    def test_doc_url_present_when_provided(self):
        body = format_email_body(
            _make_pulse(),
            doc_url="https://docs.google.com/d/abc",
            date_range=DATE_RANGE,
            run_timestamp=RUN_TS,
        )
        assert "Canonical pulse (Google Doc): https://docs.google.com/d/abc" in body

    def test_no_doc_url_when_not_provided(self):
        body = format_email_body(_make_pulse(), date_range=DATE_RANGE, run_timestamp=RUN_TS)
        assert "Canonical pulse" not in body

    def test_doc_url_appears_before_themes(self):
        body = format_email_body(
            _make_pulse(),
            doc_url="https://docs.google.com/d/abc",
            date_range=DATE_RANGE,
            run_timestamp=RUN_TS,
        )
        url_pos = body.index("https://docs.google.com/d/abc")
        themes_pos = body.index("Top themes:")
        assert url_pos < themes_pos

    def test_returns_string(self):
        assert isinstance(format_email_body(_make_pulse(), date_range=DATE_RANGE), str)

    def test_sections_in_order(self):
        body = format_email_body(_make_pulse(), date_range=DATE_RANGE, run_timestamp=RUN_TS)
        themes_pos = body.index("Top themes:")
        quotes_pos = body.index("User quotes:")
        actions_pos = body.index("Action ideas:")
        assert themes_pos < quotes_pos < actions_pos
