"""Tests for the pulse → Doc text formatter."""

from __future__ import annotations

from datetime import datetime

from pulse.models import ThemeCluster, WeeklyPulse
from pulse.phase03.formatter import format_pulse_for_doc
from pulse.phase04.email_formatter import format_email_body

DATE_RANGE = "2026-02-15 to 2026-05-10"
RUN_TS = datetime(2026, 5, 15, 14, 56, 37)


def _make_pulse() -> WeeklyPulse:
    return WeeklyPulse(
        week_label="2026-W23",
        top_themes=[
            ThemeCluster("t1", "High Brokerage Charges",
                         "Users complain about high charges eating into profits.", []),
            ThemeCluster("t2", "Technical Issues",
                         "Glitches and slow execution hinder trading.", []),
            ThemeCluster("t3", "Poor Customer Support",
                         "Unhelpful agents and long wait times frustrate users.", []),
        ],
        quotes=[
            "fraud application, there minimum charges increased to rs 5",
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


class TestFormatPulseForDoc:
    def test_matches_email_body_without_doc_link(self):
        pulse = _make_pulse()
        doc_text = format_pulse_for_doc(
            pulse, date_range=DATE_RANGE, run_timestamp=RUN_TS
        )
        email_text = format_email_body(
            pulse,
            date_range=DATE_RANGE,
            run_timestamp=RUN_TS,
            include_doc_link=False,
        )
        assert doc_text == email_text

    def test_contains_date_range_not_week_label_only(self):
        text = format_pulse_for_doc(
            _make_pulse(), date_range=DATE_RANGE, run_timestamp=RUN_TS
        )
        assert DATE_RANGE in text
        assert f"Weekly review pulse for Groww ({DATE_RANGE})." in text

    def test_contains_product_name(self):
        text = format_pulse_for_doc(
            _make_pulse(), product_name="Groww", date_range=DATE_RANGE, run_timestamp=RUN_TS
        )
        assert "Groww" in text

    def test_contains_headline(self):
        text = format_pulse_for_doc(
            _make_pulse(), date_range=DATE_RANGE, run_timestamp=RUN_TS
        )
        assert "High charges and technical issues" in text

    def test_contains_all_three_theme_labels(self):
        text = format_pulse_for_doc(
            _make_pulse(), date_range=DATE_RANGE, run_timestamp=RUN_TS
        )
        assert "High Brokerage Charges:" in text
        assert "Technical Issues:" in text
        assert "Poor Customer Support:" in text

    def test_contains_all_three_quotes(self):
        text = format_pulse_for_doc(
            _make_pulse(), date_range=DATE_RANGE, run_timestamp=RUN_TS
        )
        assert "fraud application" in text
        assert "agent cut call purposefully" in text
        assert "maximum technical glitch" in text

    def test_contains_all_three_actions(self):
        text = format_pulse_for_doc(
            _make_pulse(), date_range=DATE_RANGE, run_timestamp=RUN_TS
        )
        assert "Reduce brokerage charges" in text
        assert "Improve app stability" in text
        assert "Enhance customer support" in text

    def test_sections_in_order(self):
        text = format_pulse_for_doc(
            _make_pulse(), date_range=DATE_RANGE, run_timestamp=RUN_TS
        )
        themes_pos = text.index("Top themes:")
        quotes_pos = text.index("User quotes:")
        actions_pos = text.index("Action ideas:")
        assert themes_pos < quotes_pos < actions_pos

    def test_returns_string(self):
        assert isinstance(
            format_pulse_for_doc(_make_pulse(), date_range=DATE_RANGE), str
        )

    def test_non_empty(self):
        assert len(format_pulse_for_doc(_make_pulse(), date_range=DATE_RANGE)) > 0
