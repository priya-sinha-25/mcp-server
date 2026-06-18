"""Deterministic validation layer (architecture §5.3).

validate_pulse(pulse, corpus) → ValidationResult

Acts as the contract enforcer between LLM output and MCP delivery.
Nothing leaves this layer for Phases 3–4 unless accepted is True.
"""

from __future__ import annotations

import re

from pulse.models import NormalizedReview, ValidationResult, WeeklyPulse
from pulse.phase01.pii import EMAIL_RE, HANDLE_RE, PHONE_RE

# Maximum total word count for the pulse body (DEC-003).
MAX_WORD_COUNT = 250

# PII patterns that must not appear in any deliverable artifact (DEC-004).
_PII_PATTERNS: list[re.Pattern[str]] = [EMAIL_RE, PHONE_RE, HANDLE_RE]


def _count_words(text: str) -> int:
    """Whitespace-delimited word count (headings included per fixed policy)."""
    return len(text.split())


def _pulse_text(pulse: WeeklyPulse) -> str:
    """Concatenate all prose fields for word counting and PII scanning."""
    parts: list[str] = [pulse.headline]
    for t in pulse.top_themes:
        parts.append(t.label)
        parts.append(t.description)
    parts.extend(pulse.quotes)
    parts.extend(pulse.actions)
    return " ".join(p for p in parts if p)


def _normalize_body(text: str) -> str:
    """Collapse whitespace for substring matching."""
    return re.sub(r"\s+", " ", text).strip()


def validate_pulse(
    pulse: WeeklyPulse,
    corpus: list[NormalizedReview],
) -> ValidationResult:
    """
    Run all deterministic checks on *pulse* against the normalized *corpus*.

    Returns ValidationResult(accepted=True) if all pass,
    or ValidationResult(accepted=False, reasons=[...]) listing every failure.
    """
    reasons: list[str] = []

    # 1. Structural counts (DEC-003).
    if len(pulse.top_themes) != 3:
        reasons.append(
            f"top_themes must have exactly 3 items (got {len(pulse.top_themes)})"
        )
    if len(pulse.quotes) != 3:
        reasons.append(
            f"quotes must have exactly 3 items (got {len(pulse.quotes)})"
        )
    if len(pulse.actions) != 3:
        reasons.append(
            f"actions must have exactly 3 items (got {len(pulse.actions)})"
        )

    # 2. Word count ≤ 250 (DEC-003). Recount rather than trusting pulse.word_count.
    full_text = _pulse_text(pulse)
    actual_wc = _count_words(full_text)
    if actual_wc > MAX_WORD_COUNT:
        reasons.append(
            f"Pulse body is {actual_wc} words; must be ≤ {MAX_WORD_COUNT}"
        )

    # 3. Quote provenance: each quote must be a substring of a corpus body (DEC-002).
    corpus_bodies = [_normalize_body(r.body) for r in corpus]
    for i, quote in enumerate(pulse.quotes):
        norm_quote = _normalize_body(quote)
        if not norm_quote:
            reasons.append(f"quotes[{i}] is empty")
            continue
        if not any(norm_quote in body for body in corpus_bodies):
            reasons.append(
                f'quotes[{i}] not found in any corpus review body: '
                f'"{quote[:80]}{"..." if len(quote) > 80 else ""}"'
            )

    # 4. PII blocklist in all prose fields (DEC-004).
    for pattern in _PII_PATTERNS:
        if pattern.search(full_text):
            reasons.append(
                f"PII pattern {pattern.pattern[:40]} matched in pulse text"
            )

    # 5. Non-empty required fields.
    if not pulse.headline.strip():
        reasons.append("headline is empty")
    for i, action in enumerate(pulse.actions):
        if not str(action).strip():
            reasons.append(f"actions[{i}] is empty")

    accepted = len(reasons) == 0
    return ValidationResult(accepted=accepted, reasons=reasons)
