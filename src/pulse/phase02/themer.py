"""Stage A — Theme discovery via Groq (architecture §5.2).

discover_themes(sample, cfg, client) → ThemeCluster[]

Sends the stratified sample to Groq and parses the JSON response into
ThemeCluster objects. Retries up to cfg.groq.max_retries times with a
stricter system prompt on JSON parse failure.
"""

from __future__ import annotations

import json
import logging

from pulse.models import NormalizedReview, ThemeCluster
from pulse.phase02.config import Phase2Config
from pulse.phase02.groq_client import GroqAPIError, GroqClient
from pulse.phase02.prompts import build_stage_a_messages

logger = logging.getLogger(__name__)


class ThemeDiscoveryError(Exception):
    """Raised when Stage A cannot produce valid themes after all retries."""


def _parse_themes(content: str, valid_ids: set[str]) -> list[ThemeCluster]:
    """
    Parse Stage A response content into ThemeCluster list.

    Raises ValueError with a descriptive message on any structural problem
    so the caller can decide whether to retry.
    """
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Response is not valid JSON: {exc}") from exc

    if not isinstance(data, dict) or "themes" not in data:
        raise ValueError(
            f'Expected JSON object with "themes" key, got: {str(data)[:200]}'
        )

    raw_themes = data["themes"]
    if not isinstance(raw_themes, list):
        raise ValueError(f'"themes" must be a list, got {type(raw_themes).__name__}')

    clusters: list[ThemeCluster] = []
    for i, item in enumerate(raw_themes):
        if not isinstance(item, dict):
            raise ValueError(f"themes[{i}] is not an object")
        for key in ("theme_id", "label", "description", "review_ids"):
            if key not in item:
                raise ValueError(f'themes[{i}] missing required key "{key}"')
        if not isinstance(item["review_ids"], list):
            raise ValueError(f'themes[{i}]["review_ids"] must be a list')
        # Validate that every cited review_id exists in the sample.
        bad_ids = [rid for rid in item["review_ids"] if rid not in valid_ids]
        if bad_ids:
            raise ValueError(
                f'themes[{i}] references unknown review_ids: {bad_ids[:5]}'
            )
        clusters.append(
            ThemeCluster(
                theme_id=str(item["theme_id"]),
                label=str(item["label"]),
                description=str(item["description"]),
                review_ids=list(item["review_ids"]),
            )
        )
    return clusters


def discover_themes(
    sample: list[NormalizedReview],
    cfg: Phase2Config,
    client: GroqClient,
) -> list[ThemeCluster]:
    """
    Stage A: send stratified sample to Groq, return ≤5 ThemeCluster objects.

    Retries up to cfg.groq.max_retries times on JSON/structural errors.
    Raises ThemeDiscoveryError if all attempts fail.
    """
    if not sample:
        raise ThemeDiscoveryError("Cannot discover themes: sample is empty.")

    valid_ids = {r.review_id for r in sample}
    messages = build_stage_a_messages(sample, max_themes=cfg.groq.max_themes)
    last_error: str = ""

    for attempt in range(cfg.groq.max_retries + 1):
        if attempt > 0:
            logger.warning(
                "Stage A retry %d/%d after error: %s",
                attempt,
                cfg.groq.max_retries,
                last_error,
            )
            # Stricter system prompt on retry: emphasise JSON-only output.
            messages[0]["content"] = (
                messages[0]["content"]
                + "\n\nCRITICAL: Your previous response could not be parsed. "
                "Return ONLY the JSON object. No prose, no markdown, no code fences."
            )

        try:
            content = client.chat_completion(
                model=cfg.groq.model,
                messages=messages,
                temperature=cfg.groq.stage_a_temperature,
                response_format={"type": "json_object"},
            )
        except GroqAPIError as exc:
            last_error = str(exc)
            logger.error("Stage A Groq API error (attempt %d): %s", attempt + 1, exc)
            continue

        try:
            clusters = _parse_themes(content, valid_ids)
        except ValueError as exc:
            last_error = str(exc)
            logger.warning("Stage A parse error (attempt %d): %s", attempt + 1, exc)
            continue

        if not clusters:
            last_error = "Groq returned zero themes"
            logger.warning("Stage A returned empty themes (attempt %d)", attempt + 1)
            continue

        # Cap to max_themes (model should respect this, but enforce defensively).
        if len(clusters) > cfg.groq.max_themes:
            logger.info(
                "Stage A returned %d themes; capping to %d",
                len(clusters),
                cfg.groq.max_themes,
            )
            clusters = clusters[: cfg.groq.max_themes]

        logger.info(
            "Stage A complete: %d themes discovered (attempt %d)",
            len(clusters),
            attempt + 1,
        )
        return clusters

    raise ThemeDiscoveryError(
        f"Stage A failed after {cfg.groq.max_retries + 1} attempt(s). "
        f"Last error: {last_error}"
    )
