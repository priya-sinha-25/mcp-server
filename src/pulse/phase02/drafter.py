"""Stage B — Pulse drafting via Groq (architecture §5.2).

draft_pulse(clusters, evidence, week_label, cfg, client) → WeeklyPulse

Sends discovered themes + supporting evidence to Groq and parses the
response into a WeeklyPulse. Retries on validation failure with corrective
instructions. Rate-limit-aware: skips retry if TPD headroom is too low.
"""

from __future__ import annotations

import json
import logging
import re

from pulse.models import NormalizedReview, ThemeCluster, WeeklyPulse
from pulse.phase02.config import Phase2Config
from pulse.phase02.groq_client import GroqAPIError, GroqClient
from pulse.phase02.prompts import build_stage_b_messages

logger = logging.getLogger(__name__)

# Rough token estimate: 1 token ≈ 0.75 words, or ~1.35 tokens/word.
# Stage B retry costs ~2,600 tokens.
_STAGE_B_RETRY_TOKEN_COST = 2_600


class PulseDraftError(Exception):
    """Raised when Stage B cannot produce a valid WeeklyPulse after all retries."""


def _count_words(text: str) -> int:
    """Count whitespace-delimited words (headings included)."""
    return len(text.split())


def _pulse_word_count(data: dict) -> int:
    """Count words across all prose fields of a WeeklyPulse dict."""
    parts: list[str] = []
    parts.append(str(data.get("headline", "")))
    for theme in data.get("top_themes", []):
        parts.append(str(theme.get("label", "")))
        parts.append(str(theme.get("description", "")))
    parts.extend(str(q) for q in data.get("quotes", []))
    parts.extend(str(a) for a in data.get("actions", []))
    return _count_words(" ".join(parts))


def _parse_pulse(content: str, week_label: str) -> tuple[WeeklyPulse, list[str]]:
    """
    Parse Stage B response into a WeeklyPulse and a list of structural errors.

    Returns (pulse, errors). errors is empty on success.
    """
    errors: list[str] = []

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        return _empty_pulse(week_label), [f"Response is not valid JSON: {exc}"]

    if not isinstance(data, dict):
        return _empty_pulse(week_label), ["Response must be a JSON object"]

    # --- structural checks ---
    top_themes_raw = data.get("top_themes", [])
    quotes = data.get("quotes", [])
    actions = data.get("actions", [])

    if not isinstance(top_themes_raw, list) or len(top_themes_raw) != 3:
        errors.append(
            f"top_themes must be a list of exactly 3 items "
            f"(got {len(top_themes_raw) if isinstance(top_themes_raw, list) else type(top_themes_raw).__name__})"
        )
    if not isinstance(quotes, list) or len(quotes) != 3:
        errors.append(
            f"quotes must be a list of exactly 3 items "
            f"(got {len(quotes) if isinstance(quotes, list) else type(quotes).__name__})"
        )
    if not isinstance(actions, list) or len(actions) != 3:
        errors.append(
            f"actions must be a list of exactly 3 items "
            f"(got {len(actions) if isinstance(actions, list) else type(actions).__name__})"
        )

    if errors:
        return _empty_pulse(week_label), errors

    # --- build theme objects ---
    themes: list[ThemeCluster] = []
    for i, t in enumerate(top_themes_raw):
        if not isinstance(t, dict):
            errors.append(f"top_themes[{i}] is not an object")
            continue
        for key in ("theme_id", "label", "description", "review_ids"):
            if key not in t:
                errors.append(f'top_themes[{i}] missing key "{key}"')
        if not errors:
            themes.append(
                ThemeCluster(
                    theme_id=str(t["theme_id"]),
                    label=str(t["label"]),
                    description=str(t["description"]),
                    review_ids=list(t.get("review_ids", [])),
                )
            )

    if errors:
        return _empty_pulse(week_label), errors

    wc = _pulse_word_count(data)

    pulse = WeeklyPulse(
        week_label=str(data.get("week_label", week_label)),
        top_themes=themes,
        quotes=[str(q) for q in quotes],
        actions=[str(a) for a in actions],
        headline=str(data.get("headline", "")),
        word_count=wc,
    )
    return pulse, []


def _empty_pulse(week_label: str) -> WeeklyPulse:
    return WeeklyPulse(
        week_label=week_label,
        top_themes=[],
        quotes=[],
        actions=[],
        headline="",
        word_count=0,
    )


def _collect_evidence(
    clusters: list[ThemeCluster],
    corpus: list[NormalizedReview],
) -> list[NormalizedReview]:
    """Return reviews referenced by any theme cluster (deduped, order preserved)."""
    needed_ids: set[str] = set()
    for c in clusters:
        needed_ids.update(c.review_ids)
    seen: set[str] = set()
    result: list[NormalizedReview] = []
    for r in corpus:
        if r.review_id in needed_ids and r.review_id not in seen:
            result.append(r)
            seen.add(r.review_id)
    return result


def draft_pulse(
    clusters: list[ThemeCluster],
    corpus: list[NormalizedReview],
    week_label: str,
    cfg: Phase2Config,
    client: GroqClient,
    *,
    tpd_used: int = 0,
) -> WeeklyPulse:
    """
    Stage B: send themes + evidence to Groq, return a WeeklyPulse.

    *tpd_used* is an optional running token count for the current day.
    If a retry would push usage past (100_000 - cfg.groq.min_tpd_headroom),
    the retry is skipped and the validation error is surfaced instead.

    Raises PulseDraftError if all attempts fail.
    """
    if not clusters:
        raise PulseDraftError("Cannot draft pulse: no theme clusters provided.")

    evidence = _collect_evidence(clusters, corpus)
    if not evidence:
        raise PulseDraftError(
            "Cannot draft pulse: no evidence reviews found for the given clusters."
        )

    repair_reasons: list[str] | None = None
    last_error: str = ""
    _tpd = tpd_used

    for attempt in range(cfg.groq.max_retries + 1):
        if attempt > 0:
            # Rate-limit guard: skip retry if daily headroom is too thin.
            remaining_tpd = 100_000 - _tpd
            if remaining_tpd < cfg.groq.min_tpd_headroom + _STAGE_B_RETRY_TOKEN_COST:
                raise PulseDraftError(
                    f"Stage B retry {attempt} skipped: insufficient TPD headroom "
                    f"({remaining_tpd} tokens remaining, need "
                    f"{cfg.groq.min_tpd_headroom + _STAGE_B_RETRY_TOKEN_COST}). "
                    f"Last validation errors: {repair_reasons}"
                )
            logger.warning(
                "Stage B retry %d/%d. Repair reasons: %s",
                attempt,
                cfg.groq.max_retries,
                repair_reasons,
            )

        messages = build_stage_b_messages(
            clusters, evidence, week_label, repair_reasons=repair_reasons
        )

        try:
            content = client.chat_completion(
                model=cfg.groq.model,
                messages=messages,
                temperature=cfg.groq.stage_b_temperature,
                response_format={"type": "json_object"},
            )
            # Rough token accounting (input ~2300 + response ~340).
            _tpd += 2_640
        except GroqAPIError as exc:
            last_error = str(exc)
            logger.error("Stage B Groq API error (attempt %d): %s", attempt + 1, exc)
            repair_reasons = [f"API error: {exc}"]
            continue

        pulse, parse_errors = _parse_pulse(content, week_label)
        if parse_errors:
            repair_reasons = parse_errors
            last_error = "; ".join(parse_errors)
            logger.warning(
                "Stage B parse/structural errors (attempt %d): %s",
                attempt + 1,
                parse_errors,
            )
            continue

        logger.info(
            "Stage B complete: pulse drafted (%d words, attempt %d)",
            pulse.word_count,
            attempt + 1,
        )
        return pulse

    raise PulseDraftError(
        f"Stage B failed after {cfg.groq.max_retries + 1} attempt(s). "
        f"Last error: {last_error}"
    )
