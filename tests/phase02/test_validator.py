"""Tests for the deterministic validation layer (architecture §5.3)."""

from __future__ import annotations

from pulse.models import ThemeCluster, WeeklyPulse
from pulse.phase02.validator import MAX_WORD_COUNT, validate_pulse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pulse(
    top_themes=None,
    quotes=None,
    actions=None,
    headline="Users face withdrawal and trading issues this week.",
    week_label="2026-W10",
) -> WeeklyPulse:
    if top_themes is None:
        top_themes = [
            ThemeCluster("t1", "Withdrawal Delays", "Funds stuck", []),
            ThemeCluster("t2", "Trading Failures", "Orders fail", []),
            ThemeCluster("t3", "Positive UX", "Easy to use", []),
        ]
    if quotes is None:
        quotes = ["quote one", "quote two", "quote three"]
    if actions is None:
        actions = ["action one", "action two", "action three"]
    return WeeklyPulse(
        week_label=week_label,
        top_themes=top_themes,
        quotes=quotes,
        actions=actions,
        headline=headline,
        word_count=0,
    )


# ---------------------------------------------------------------------------
# Acceptance
# ---------------------------------------------------------------------------

class TestValidatePulseAccept:
    def test_valid_pulse_accepted(self, valid_pulse, small_corpus):
        result = validate_pulse(valid_pulse, small_corpus)
        assert result.accepted is True
        assert result.reasons == []

    def test_accepted_flag_true_on_pass(self, valid_pulse, small_corpus):
        result = validate_pulse(valid_pulse, small_corpus)
        assert result.accepted


# ---------------------------------------------------------------------------
# Structural count failures
# ---------------------------------------------------------------------------

class TestStructuralCounts:
    def test_too_few_themes_rejected(self, small_corpus):
        pulse = _make_pulse(top_themes=[
            ThemeCluster("t1", "X", "Y", []),
            ThemeCluster("t2", "X", "Y", []),
        ])
        result = validate_pulse(pulse, small_corpus)
        assert not result.accepted
        assert any("top_themes" in r for r in result.reasons)

    def test_too_many_themes_rejected(self, small_corpus):
        pulse = _make_pulse(top_themes=[
            ThemeCluster(f"t{i}", "X", "Y", []) for i in range(4)
        ])
        result = validate_pulse(pulse, small_corpus)
        assert not result.accepted

    def test_two_quotes_rejected(self, small_corpus):
        pulse = _make_pulse(quotes=["a", "b"])
        result = validate_pulse(pulse, small_corpus)
        assert not result.accepted
        assert any("quotes" in r for r in result.reasons)

    def test_four_actions_rejected(self, small_corpus):
        pulse = _make_pulse(actions=["a", "b", "c", "d"])
        result = validate_pulse(pulse, small_corpus)
        assert not result.accepted
        assert any("actions" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# Word count
# ---------------------------------------------------------------------------

class TestWordCount:
    def test_pulse_under_250_words_accepted(self, valid_pulse, small_corpus):
        result = validate_pulse(valid_pulse, small_corpus)
        assert result.accepted

    def test_pulse_over_250_words_rejected(self, small_corpus):
        long_action = " ".join(["word"] * 100)
        pulse = _make_pulse(
            quotes=[
                "Cannot withdraw funds since last update week 0 review 0 terrible experience",
                "App crashes during trading session order not executed failure number 0",
                "Best investment app easy transfers smooth onboarding week 0 review 0",
            ],
            actions=[long_action, long_action, long_action],
        )
        result = validate_pulse(pulse, small_corpus)
        assert not result.accepted
        assert any(str(MAX_WORD_COUNT) in r for r in result.reasons)


# ---------------------------------------------------------------------------
# Quote provenance
# ---------------------------------------------------------------------------

class TestQuoteProvenance:
    def test_exact_quote_from_corpus_accepted(self, small_corpus):
        # Use a real body from small_corpus.
        real_body = small_corpus[0].body
        pulse = _make_pulse(quotes=[
            real_body,
            small_corpus[1].body,
            small_corpus[2].body,
        ])
        result = validate_pulse(pulse, small_corpus)
        provenance_errors = [r for r in result.reasons if "not found" in r]
        assert provenance_errors == []

    def test_fabricated_quote_rejected(self, small_corpus):
        pulse = _make_pulse(quotes=[
            "This quote was completely made up by the model",
            small_corpus[0].body,
            small_corpus[1].body,
        ])
        result = validate_pulse(pulse, small_corpus)
        assert not result.accepted
        assert any("not found in any corpus" in r for r in result.reasons)

    def test_partial_quote_substring_accepted(self, small_corpus):
        # A substring of a real body should still pass provenance.
        real_body = small_corpus[0].body
        # Take first 20 chars as a quote substring.
        partial = real_body[:20]
        # Only if partial is actually in the body (guaranteed since it's a slice).
        pulse = _make_pulse(quotes=[
            partial,
            small_corpus[1].body,
            small_corpus[2].body,
        ])
        result = validate_pulse(pulse, small_corpus)
        provenance_errors = [r for r in result.reasons if "not found" in r and partial in r]
        assert provenance_errors == []

    def test_empty_quote_rejected(self, small_corpus):
        pulse = _make_pulse(quotes=["", small_corpus[0].body, small_corpus[1].body])
        result = validate_pulse(pulse, small_corpus)
        assert not result.accepted
        assert any("empty" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# PII blocklist
# ---------------------------------------------------------------------------

class TestPIIBlocklist:
    def test_email_in_quote_rejected(self, small_corpus):
        pulse = _make_pulse(
            quotes=[
                "Contact me at user@example.com for more info please help",
                small_corpus[0].body,
                small_corpus[1].body,
            ]
        )
        result = validate_pulse(pulse, small_corpus)
        assert not result.accepted
        assert any("PII" in r for r in result.reasons)

    def test_phone_in_action_rejected(self, small_corpus):
        pulse = _make_pulse(
            actions=[
                "Call 555-867-5309 to report issues directly",
                "action two",
                "action three",
            ]
        )
        result = validate_pulse(pulse, small_corpus)
        assert not result.accepted

    def test_handle_in_headline_rejected(self, small_corpus):
        pulse = _make_pulse(headline="Contact @support_team for help this week.")
        result = validate_pulse(pulse, small_corpus)
        assert not result.accepted

    def test_clean_pulse_no_pii_error(self, valid_pulse, small_corpus):
        result = validate_pulse(valid_pulse, small_corpus)
        pii_errors = [r for r in result.reasons if "PII" in r]
        assert pii_errors == []


# ---------------------------------------------------------------------------
# Empty fields
# ---------------------------------------------------------------------------

class TestEmptyFields:
    def test_empty_headline_rejected(self, small_corpus):
        pulse = _make_pulse(headline="")
        result = validate_pulse(pulse, small_corpus)
        assert not result.accepted
        assert any("headline" in r for r in result.reasons)

    def test_empty_action_rejected(self, small_corpus):
        pulse = _make_pulse(actions=["valid action", "", "another valid action"])
        result = validate_pulse(pulse, small_corpus)
        assert not result.accepted
        assert any("actions" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# Multiple failures reported together
# ---------------------------------------------------------------------------

class TestMultipleFailures:
    def test_multiple_errors_all_reported(self, small_corpus):
        pulse = _make_pulse(
            top_themes=[ThemeCluster("t1", "X", "Y", [])],  # wrong count
            quotes=["fabricated quote not in corpus", "another fake", "third fake"],
            actions=["a", "b", "c"],
        )
        result = validate_pulse(pulse, small_corpus)
        assert not result.accepted
        # Should report theme count error + quote provenance errors.
        assert len(result.reasons) >= 2
