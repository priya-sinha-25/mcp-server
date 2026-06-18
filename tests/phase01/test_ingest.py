"""Phase 1 ingestion tests (phases/phase-01/eval.md)."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

from pulse.models import Platform
from pulse.phase01.ingest import ingest_reviews
from pulse.phase01.parsers import ParseError
from pulse.phase01.pii import EMAIL_RE, HANDLE_RE, PHONE_RE
from pulse.phase01.text_clean import word_count
from pulse.phase01.window import lookback_bounds

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
REF = date(2026, 4, 25)


def test_app_store_parses(reference_date):
    result = ingest_reviews(
        [FIXTURES / "app_store_sample.csv"],
        reference_date=reference_date,
    )
    platforms = {r.platform for r in result.reviews}
    assert Platform.APP_STORE in platforms
    assert result.metadata.after_dedupe >= 3


def test_play_store_parses(reference_date):
    result = ingest_reviews(
        [FIXTURES / "play_store_sample.csv"],
        reference_date=reference_date,
    )
    assert all(r.platform == Platform.PLAY_STORE for r in result.reviews)
    assert len(result.reviews) == 3


def test_combined_exports(reference_date):
    result = ingest_reviews(
        [
            FIXTURES / "app_store_sample.csv",
            FIXTURES / "play_store_sample.csv",
        ],
        reference_date=reference_date,
    )
    platforms = {r.platform for r in result.reviews}
    assert Platform.APP_STORE in platforms
    assert Platform.PLAY_STORE in platforms


def test_date_window_excludes_old_reviews(reference_date):
    result = ingest_reviews(
        [FIXTURES / "app_store_sample.csv"],
        reference_date=reference_date,
    )
    bodies = [r.body for r in result.reviews]
    assert not any("outside the lookback" in b for b in bodies)
    start, end = lookback_bounds(reference_date, 10)
    for r in result.reviews:
        assert start <= r.review_date <= end


def test_dedupe_same_platform_duplicate(reference_date):
    result = ingest_reviews(
        [FIXTURES / "app_store_sample.csv"],
        reference_date=reference_date,
    )
    kyc = [r for r in result.reviews if "verification" in r.body.lower()]
    assert len(kyc) == 1


def test_empty_body_dropped(reference_date):
    result = ingest_reviews(
        [FIXTURES / "app_store_sample.csv"],
        reference_date=reference_date,
    )
    assert all(r.body.strip() for r in result.reviews)


def test_quality_filters(reference_date):
    result = ingest_reviews(
        [FIXTURES / "quality_filter_sample.csv"],
        reference_date=reference_date,
    )
    bodies = " ".join(r.body for r in result.reviews).lower()
    assert "too few words" not in bodies
    assert "यह" not in bodies
    assert "👍" not in bodies
    assert result.metadata.dropped_too_few_words >= 1
    assert result.metadata.dropped_non_english >= 1
    assert len(result.reviews) == 3


def test_min_word_count_enforced(reference_date):
    result = ingest_reviews(
        [FIXTURES / "play_store_sample.csv"],
        reference_date=reference_date,
    )
    for r in result.reviews:
        assert word_count(r.body) > 6


def test_pii_redacted(reference_date):
    result = ingest_reviews(
        [FIXTURES / "pii_sample.csv"],
        reference_date=reference_date,
    )
    combined = " ".join(r.title + " " + r.body for r in result.reviews)
    assert not EMAIL_RE.search(combined)
    assert not PHONE_RE.search(combined)
    assert not HANDLE_RE.search(combined)
    assert "[redacted]" in combined
    assert result.metadata.pii_redactions > 0


def test_normalized_review_schema(reference_date):
    result = ingest_reviews(
        [FIXTURES / "app_store_sample.csv"],
        reference_date=reference_date,
    )
    r = result.reviews[0]
    d = r.to_dict()
    for key in (
        "review_id",
        "platform",
        "review_date",
        "rating",
        "title",
        "body",
        "source_row",
    ):
        assert key in d
    assert re.match(r"^[a-z_]+_[a-f0-9]{16}$", r.review_id)


def test_malformed_file_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("not,a,valid\ncsv\n", encoding="utf-8")
    with pytest.raises(ParseError):
        ingest_reviews([bad], reference_date=REF)


def test_missing_file_raises():
    with pytest.raises(ParseError):
        ingest_reviews([FIXTURES / "does_not_exist.csv"], reference_date=REF)


def test_ingest_metadata_warnings(reference_date):
    result = ingest_reviews(
        [FIXTURES / "app_store_sample.csv"],
        reference_date=reference_date,
    )
    assert any("Lookback window" in w for w in result.metadata.warnings)
