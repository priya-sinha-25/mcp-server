"""Unit tests for text cleaning helpers."""

from pulse.phase01.text_clean import is_english, strip_emojis, word_count


def test_word_count():
    assert word_count("one two three four five six") == 6
    assert word_count("one two three four five six seven") == 7


def test_strip_emojis():
    text, changed = strip_emojis("Great app really good 👍👍")
    assert changed
    assert "👍" not in text
    assert "Great app" in text


def test_is_english_rejects_hindi():
    assert not is_english("यह ऐप बहुत अच्छा है लेकिन सपोर्ट धीमा है")


def test_is_english_accepts_plain():
    assert is_english("Customer support was slow but the app works well overall.")
