"""Review text cleaning: emojis, word count, English-only (Phase 1)."""

from __future__ import annotations

import re

# Broad emoji / pictograph removal (covers most Play Store emoji usage).
_EMOJI_RE = re.compile(
    "["
    "\U0001F1E0-\U0001F1FF"
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\u200d"
    "\ufe0f"
    "]+",
    flags=re.UNICODE,
)

# Non-Latin scripts commonly seen in Indian Play reviews (Hindi, Tamil, etc.).
_NON_LATIN_SCRIPT_RE = re.compile(
    r"[\u0900-\u097F"  # Devanagari
    r"\u0980-\u09FF"  # Bengali
    r"\u0A00-\u0A7F"  # Gurmukhi
    r"\u0A80-\u0AFF"  # Gujarati
    r"\u0B00-\u0B7F"  # Oriya
    r"\u0B80-\u0BFF"  # Tamil
    r"\u0C00-\u0C7F"  # Telugu
    r"\u0C80-\u0CFF"  # Kannada
    r"\u0D00-\u0D7F"  # Malayalam
    r"\u0600-\u06FF"  # Arabic
    r"\u4E00-\u9FFF"  # CJK
    r"]"
)

_WORD_RE = re.compile(r"[A-Za-z0-9']+(?:'[A-Za-z]+)?")


def strip_emojis(text: str) -> tuple[str, bool]:
    """Remove emoji characters; return cleaned text and whether any were removed."""
    if not text:
        return text, False
    cleaned = _EMOJI_RE.sub("", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned, cleaned != text.strip()


def word_count(text: str) -> int:
    """Count words (Latin letters/digits) in text."""
    if not text:
        return 0
    return len(_WORD_RE.findall(text))


def has_non_latin_script(text: str) -> bool:
    return bool(_NON_LATIN_SCRIPT_RE.search(text))


def is_english(text: str, *, min_chars_for_detect: int = 25) -> bool:
    """
    Keep only English reviews.
    Uses script heuristics first, then langdetect when enough text.
    """
    text = text.strip()
    if not text:
        return False

    if has_non_latin_script(text):
        return False

    # Mostly ASCII letters → likely English (incl. short reviews).
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    ascii_ratio = sum(1 for c in letters if ord(c) < 128) / len(letters)
    if ascii_ratio < 0.85:
        return False

    if len(text) < min_chars_for_detect:
        return True

    try:
        from langdetect import DetectorFactory, detect

        DetectorFactory.seed = 0
        return detect(text) == "en"
    except Exception:
        # langdetect unavailable or ambiguous → trust script heuristic
        return ascii_ratio >= 0.9
