"""Tests for Stage B pulse drafting (mocked Groq client)."""

from __future__ import annotations

import json

import pytest

from pulse.phase02.drafter import PulseDraftError, _collect_evidence, draft_pulse
from pulse.phase02.groq_client import GroqAPIError

from tests.phase02.conftest import make_mock_client, stage_b_response


# ---------------------------------------------------------------------------
# _collect_evidence
# ---------------------------------------------------------------------------

class TestCollectEvidence:
    def test_returns_reviews_referenced_by_clusters(self, small_corpus, mock_themes):
        evidence = _collect_evidence(mock_themes, small_corpus)
        evidence_ids = {r.review_id for r in evidence}
        # All review_ids across all mock themes should be present.
        for cluster in mock_themes:
            for rid in cluster.review_ids:
                assert rid in evidence_ids

    def test_no_duplicates(self, small_corpus, mock_themes):
        evidence = _collect_evidence(mock_themes, small_corpus)
        ids = [r.review_id for r in evidence]
        assert len(ids) == len(set(ids))

    def test_empty_clusters_returns_empty(self, small_corpus):
        assert _collect_evidence([], small_corpus) == []


# ---------------------------------------------------------------------------
# draft_pulse (mocked Groq)
# ---------------------------------------------------------------------------

class TestDraftPulse:
    def test_happy_path(self, small_corpus, mock_themes, default_cfg):
        resp = stage_b_response(
            quotes=[
                small_corpus[0].body,
                small_corpus[1].body,
                small_corpus[9].body,
            ]
        )
        client = make_mock_client(resp)
        pulse = draft_pulse(mock_themes, small_corpus, "2026-W18", default_cfg, client)
        assert pulse.week_label == "2026-W18"
        assert len(pulse.top_themes) == 3
        assert len(pulse.quotes) == 3
        assert len(pulse.actions) == 3
        assert pulse.headline

    def test_groq_called_with_correct_params(self, small_corpus, mock_themes, default_cfg):
        resp = stage_b_response(
            quotes=[
                small_corpus[0].body,
                small_corpus[1].body,
                small_corpus[9].body,
            ]
        )
        client = make_mock_client(resp)
        draft_pulse(mock_themes, small_corpus, "2026-W18", default_cfg, client)
        call_kwargs = client.chat_completion.call_args.kwargs
        assert call_kwargs["model"] == default_cfg.groq.model
        assert call_kwargs["temperature"] == default_cfg.groq.stage_b_temperature
        assert call_kwargs["response_format"] == {"type": "json_object"}

    def test_retries_on_structural_error(self, small_corpus, mock_themes, default_cfg):
        bad_resp = json.dumps({
            "week_label": "2026-W18",
            "headline": "Issues this week.",
            "top_themes": [],       # wrong count — should trigger retry
            "quotes": [],
            "actions": [],
        })
        good_resp = stage_b_response(
            quotes=[
                small_corpus[0].body,
                small_corpus[1].body,
                small_corpus[9].body,
            ]
        )
        client = make_mock_client(bad_resp)
        client.chat_completion.side_effect = [bad_resp, good_resp]
        pulse = draft_pulse(mock_themes, small_corpus, "2026-W18", default_cfg, client)
        assert len(pulse.top_themes) == 3
        assert client.chat_completion.call_count == 2

    def test_raises_after_all_retries(self, small_corpus, mock_themes, default_cfg):
        bad_resp = json.dumps({
            "week_label": "2026-W18", "headline": "x",
            "top_themes": [], "quotes": [], "actions": [],
        })
        client = make_mock_client(bad_resp)
        with pytest.raises(PulseDraftError, match="Stage B failed"):
            draft_pulse(mock_themes, small_corpus, "2026-W18", default_cfg, client)
        assert client.chat_completion.call_count == default_cfg.groq.max_retries + 1

    def test_api_error_triggers_retry(self, small_corpus, mock_themes, default_cfg):
        good_resp = stage_b_response(
            quotes=[
                small_corpus[0].body,
                small_corpus[1].body,
                small_corpus[9].body,
            ]
        )
        client = make_mock_client(good_resp)
        client.chat_completion.side_effect = [GroqAPIError("timeout"), good_resp]
        pulse = draft_pulse(mock_themes, small_corpus, "2026-W18", default_cfg, client)
        assert len(pulse.top_themes) == 3

    def test_empty_clusters_raises(self, small_corpus, default_cfg):
        client = make_mock_client("{}")
        with pytest.raises(PulseDraftError, match="no theme clusters"):
            draft_pulse([], small_corpus, "2026-W18", default_cfg, client)

    def test_tpd_guard_skips_retry(self, small_corpus, mock_themes, default_cfg):
        """If TPD headroom is too low, retry is skipped and error is surfaced."""
        bad_resp = json.dumps({
            "week_label": "2026-W18", "headline": "x",
            "top_themes": [], "quotes": [], "actions": [],
        })
        client = make_mock_client(bad_resp)
        # Simulate nearly exhausted daily budget (98K of 100K used).
        with pytest.raises(PulseDraftError, match="TPD headroom"):
            draft_pulse(
                mock_themes, small_corpus, "2026-W18", default_cfg, client,
                tpd_used=98_000,
            )
        # Only 1 attempt made — retry blocked by TPD guard.
        assert client.chat_completion.call_count == 1

    def test_word_count_computed(self, small_corpus, mock_themes, default_cfg):
        resp = stage_b_response(
            quotes=[
                small_corpus[0].body,
                small_corpus[1].body,
                small_corpus[9].body,
            ]
        )
        client = make_mock_client(resp)
        pulse = draft_pulse(mock_themes, small_corpus, "2026-W18", default_cfg, client)
        assert pulse.word_count > 0
