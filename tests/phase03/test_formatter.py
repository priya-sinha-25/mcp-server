"""Tests for the pulse → Doc text formatter."""

from __future__ import annotations

from pulse.models import ThemeCluster, WeeklyPulse
from pulse.phase03.formatter import format_pulse_for_doc


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
    def test_contains_week_label(self):
        text = format_pulse_for_doc(_make_pulse())
        assert "2026-W23" in text

    def test_contains_product_name(self):
        text = format_pulse_for_doc(_make_pulse(), product_name="Groww")
        assert "Groww" in text

    def test_contains_headline(self):
        text = format_pulse_for_doc(_make_pulse())
        assert "High charges and technical issues" in text

    def test_contains_all_three_theme_labels(self):
        text = format_pulse_for_doc(_make_pulse())
        assert "High Brokerage Charges" in text
        assert "Technical Issues" in text
        assert "Poor Customer Support" in text

    def test_contains_all_three_quotes(self):
        text = format_pulse_for_doc(_make_pulse())
        assert "fraud application" in text
        assert "agent cut call purposefully" in text
        assert "maximum technical glitch" in text

    def test_contains_all_three_actions(self):
        text = format_pulse_for_doc(_make_pulse())
        assert "Reduce brokerage charges" in text
        assert "Improve app stability" in text
        assert "Enhance customer support" in text

    def test_contains_word_count(self):
        text = format_pulse_for_doc(_make_pulse())
        assert "139" in text
        assert "250" in text

    def test_sections_in_order(self):
        text = format_pulse_for_doc(_make_pulse())
        summary_pos = text.index("Summary:")
        themes_pos = text.index("TOP THEMES")
        quotes_pos = text.index("VERBATIM USER QUOTES")
        actions_pos = text.index("ACTION IDEAS")
        assert summary_pos < themes_pos < quotes_pos < actions_pos

    def test_returns_string(self):
        assert isinstance(format_pulse_for_doc(_make_pulse()), str)

    def test_non_empty(self):
        assert len(format_pulse_for_doc(_make_pulse())) > 0
