"""PII minimization at ingestion (DEC-004)."""

from __future__ import annotations

import re

# Patterns applied to title and body; never log matched substrings.
EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)
PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)"
)
HANDLE_RE = re.compile(r"@[\w][\w.-]{0,30}\b")
URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)

REDACTION = "[redacted]"


def redact_pii(text: str) -> tuple[str, int]:
    """Return redacted text and count of redaction operations."""
    if not text:
        return text, 0

    count = 0
    out = text

    for pattern in (EMAIL_RE, PHONE_RE, HANDLE_RE, URL_RE):
        matches = pattern.findall(out)
        if matches:
            count += len(matches)
            out = pattern.sub(REDACTION, out)

    # Collapse repeated redaction tokens and extra whitespace.
    out = re.sub(r"(?:\[redacted\]\s*){2,}", REDACTION, out)
    out = re.sub(r"\s+", " ", out).strip()
    return out, count
