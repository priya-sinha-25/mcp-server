"""Tests for Stage A theme discovery (mocked Groq client)."""

from __future__ import annotations

import json

import pytest

from pulse.models import ThemeCluster
from pulse.phase02.groq_client import GroqAPIError
from pulse.phase02.themer import ThemeDiscoveryError, _parse_themes, discover_themes

from tests.phase02.conftest import make_mock_client, stage_a_response


# ---------------------------------------------------------------------------
# _parse_themes unit tests
# ---------------------------------------------------------------------------

class TestParseThemes:
    def test_valid_response(self, small_corpus):
        valid_ids = {r.review_id for r in small_corpus}
        content = stage_a_response([
            {
                "theme_id": "theme_1",
                "label": "Withdrawal Issues",
                "description": "Users cannot withdraw funds",
                "review_ids": ["neg_w0_0", "neg_w0_1"],
            }
        ])
        clusters = _parse_themes(content, valid_ids)
        assert len(clusters) == 1
        assert clusters[0].label == "Withdrawal Issues"
        assert "neg_w0_0" in clusters[0].review_ids

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="not valid JSON"):
            _parse_themes("not json at all", set())

    def test_missing_themes_key_raises(self):
        with pytest.raises(ValueError, match='"themes" key'):
            _parse_themes(json.dumps({"other": []}), set())

    def test_themes_not_list_raises(self):
        with pytest.raises(ValueError, match='"themes" must be a list'):
            _parse_themes(json.dumps({"themes": "string"}), set())

    def test_missing_required_key_raises(self):
        content = json.dumps({"themes": [{"theme_id": "t1", "label": "X"}]})
        with pytest.raises(ValueError, match="missing required key"):
            _parse_themes(content, set())

    def test_unknown_review_ids_raises(self):
        content = stage_a_response([{
            "theme_id": "t1",
            "label": "X",
            "description": "Y",
            "review_ids": ["nonexistent_id"],
        }])
        with pytest.raises(ValueError, match="unknown review_ids"):
            _parse_themes(content, {"known_id"})

    def test_empty_review_ids_ok(self):
        content = stage_a_response([{
            "theme_id": "t1",
            "label": "X",
            "description": "Y",
            "review_ids": [],
        }])
        clusters = _parse_themes(content, set())
        assert len(clusters) == 1
        assert clusters[0].review_ids == []


# ---------------------------------------------------------------------------
# discover_themes integration (mocked)
# ---------------------------------------------------------------------------

class TestDiscoverThemes:
    def test_happy_path(self, small_corpus, default_cfg):
        content = stage_a_response([
            {"theme_id": "theme_1", "label": "Withdrawals", "description": "Funds stuck",
             "review_ids": ["neg_w0_0"]},
            {"theme_id": "theme_2", "label": "Crashes", "description": "App unstable",
             "review_ids": ["neg_w0_1"]},
        ])
        client = make_mock_client(content)
        clusters = discover_themes(small_corpus, default_cfg, client)
        assert len(clusters) == 2
        assert clusters[0].label == "Withdrawals"
        client.chat_completion.assert_called_once()

    def test_caps_to_max_themes(self, small_corpus, default_cfg):
        # Return 7 themes — should be capped to 5.
        themes = [
            {"theme_id": f"theme_{i}", "label": f"Theme {i}",
             "description": "desc", "review_ids": []}
            for i in range(7)
        ]
        client = make_mock_client(stage_a_response(themes))
        clusters = discover_themes(small_corpus, default_cfg, client)
        assert len(clusters) == default_cfg.groq.max_themes

    def test_retries_on_bad_json(self, small_corpus, default_cfg):
        valid_response = stage_a_response([
            {"theme_id": "t1", "label": "L", "description": "D", "review_ids": []}
        ])
        # First call returns garbage, second returns valid JSON.
        client = make_mock_client("not json")
        client.chat_completion.side_effect = ["not json", valid_response]
        clusters = discover_themes(small_corpus, default_cfg, client)
        assert len(clusters) == 1
        assert client.chat_completion.call_count == 2

    def test_raises_after_all_retries(self, small_corpus, default_cfg):
        client = make_mock_client("always bad json")
        with pytest.raises(ThemeDiscoveryError, match="Stage A failed"):
            discover_themes(small_corpus, default_cfg, client)
        # max_retries=2 → 3 total attempts
        assert client.chat_completion.call_count == default_cfg.groq.max_retries + 1

    def test_api_error_triggers_retry(self, small_corpus, default_cfg):
        valid_response = stage_a_response([
            {"theme_id": "t1", "label": "L", "description": "D", "review_ids": []}
        ])
        client = make_mock_client(GroqAPIError("timeout"))
        client.chat_completion.side_effect = [
            GroqAPIError("timeout"),
            valid_response,
        ]
        clusters = discover_themes(small_corpus, default_cfg, client)
        assert len(clusters) == 1

    def test_empty_sample_raises(self, default_cfg):
        client = make_mock_client("{}")
        with pytest.raises(ThemeDiscoveryError, match="empty"):
            discover_themes([], default_cfg, client)

    def test_groq_called_with_correct_model(self, small_corpus, default_cfg):
        content = stage_a_response([
            {"theme_id": "t1", "label": "L", "description": "D", "review_ids": []}
        ])
        client = make_mock_client(content)
        discover_themes(small_corpus, default_cfg, client)
        call_kwargs = client.chat_completion.call_args.kwargs
        assert call_kwargs["model"] == default_cfg.groq.model
        assert call_kwargs["temperature"] == default_cfg.groq.stage_a_temperature
        assert call_kwargs["response_format"] == {"type": "json_object"}

    def test_all_returned_review_ids_from_sample(self, small_corpus, default_cfg):
        sample_ids = [r.review_id for r in small_corpus[:3]]
        content = stage_a_response([{
            "theme_id": "t1", "label": "L", "description": "D",
            "review_ids": sample_ids,
        }])
        client = make_mock_client(content)
        clusters = discover_themes(small_corpus, default_cfg, client)
        for rid in clusters[0].review_ids:
            assert rid in {r.review_id for r in small_corpus}
