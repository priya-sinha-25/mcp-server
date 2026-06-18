"""Main ingestion API: ingest_reviews(paths) → IngestResult."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

from pulse.models import IngestMetadata, IngestResult, NormalizedReview, Platform
from pulse.phase01.config import IngestConfig, load_ingest_config
from pulse.phase01.dedupe import dedupe_reviews
from pulse.phase01.parsers import ParseError, RawReviewRow, parse_csv_file
from pulse.phase01.pii import redact_pii
from pulse.phase01.text_clean import is_english, strip_emojis, word_count
from pulse.phase01.window import in_window, lookback_bounds


def _apply_text_cleaning(raw: RawReviewRow) -> tuple[RawReviewRow, bool]:
    """Strip emojis from title/body; return updated row and whether emojis were removed."""
    title, title_changed = strip_emojis(raw.title)
    body, body_changed = strip_emojis(raw.body)
    cleaned = replace(raw, title=title, body=body)
    return cleaned, title_changed or body_changed


def _raw_to_normalized(raw: RawReviewRow) -> tuple[NormalizedReview, int]:
    title, t_count = redact_pii(raw.title)
    body, b_count = redact_pii(raw.body)
    return (
        NormalizedReview(
            review_id=_stable_id(raw),
            platform=raw.platform,
            review_date=raw.review_date,
            rating=raw.rating,
            title=title,
            body=body,
            source_row=raw.source_row,
            version=raw.version,
            country=raw.country,
        ),
        t_count + b_count,
    )


def _stable_id(raw: RawReviewRow) -> str:
    import hashlib

    digest = hashlib.sha256(
        f"{raw.platform.value}:{raw.source_row}:{raw.review_date}:{raw.body[:200]}".encode()
    ).hexdigest()[:16]
    return f"{raw.platform.value}_{digest}"


def ingest_reviews(
    paths: list[Path | str],
    *,
    config_path: Path | str | None = None,
    reference_date: date | None = None,
    platform: Platform | None = None,
) -> IngestResult:
    """
    Ingest and normalize public store review exports.

    Quality filters (configurable):
    - More than min_word_count words in body (default: >6 → at least 7 words)
    - English only (non-English scripts / language detection)
    - Emojis stripped from title and body
    """
    cfg = load_ingest_config(Path(config_path) if config_path else None)
    ref = reference_date or date.today()
    start, end = lookback_bounds(ref, cfg.lookback_weeks)

    meta = IngestMetadata()
    all_raw: list[RawReviewRow] = []

    if not paths:
        raise ValueError("paths must contain at least one export file")

    for p in paths:
        path = Path(p)
        try:
            rows, warnings, scanned = parse_csv_file(path, platform, cfg)
            meta.warnings.extend(warnings)
            meta.input_rows += scanned
            meta.parsed_rows += len(rows)
            all_raw.extend(rows)
        except ParseError:
            raise
        except Exception as e:
            meta.warnings.append(f"{path.name}: unexpected error ({e})")

    windowed: list[RawReviewRow] = []
    for raw in all_raw:
        if in_window(raw.review_date, start, end):
            windowed.append(raw)
    meta.after_window = len(windowed)

    quality: list[RawReviewRow] = []
    for raw in windowed:
        cleaned, had_emoji = _apply_text_cleaning(raw)
        if had_emoji:
            meta.emoji_stripped += 1

        if not cleaned.body.strip():
            meta.dropped_empty_body += 1
            continue

        combined = f"{cleaned.title} {cleaned.body}".strip()
        if cfg.english_only and not is_english(combined):
            meta.dropped_non_english += 1
            continue

        if word_count(cleaned.body) <= cfg.min_word_count:
            meta.dropped_too_few_words += 1
            continue

        quality.append(cleaned)

    meta.after_quality_filter = len(quality)

    normalized: list[NormalizedReview] = []
    for raw in quality:
        review, redactions = _raw_to_normalized(raw)
        meta.pii_redactions += redactions
        normalized.append(review)

    deduped, removed = dedupe_reviews(
        normalized, cross_platform_days=cfg.cross_platform_dedupe_days
    )
    meta.after_dedupe = len(deduped)
    if removed:
        meta.warnings.append(f"Deduped {removed} duplicate review(s)")

    meta.warnings.insert(
        0,
        f"Lookback window {start.isoformat()} to {end.isoformat()} "
        f"({cfg.lookback_weeks} weeks, inclusive UTC dates)",
    )
    meta.warnings.insert(
        1,
        f"Quality: body >{cfg.min_word_count} words, English only, emojis stripped",
    )

    return IngestResult(reviews=deduped, metadata=meta)
