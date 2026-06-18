"""Tests for Phase 2 stratified sampling (DEC-012)."""

from __future__ import annotations

from pulse.phase02.config import SamplingConfig
from pulse.phase02.sampler import _rating_tier, pre_sample, stratified_sample


# ---------------------------------------------------------------------------
# pre_sample
# ---------------------------------------------------------------------------

class TestPreSample:
    def test_returns_all_when_under_cap(self, small_corpus):
        result = pre_sample(small_corpus, n=1000, seed=42)
        assert len(result) == len(small_corpus)

    def test_caps_to_n_when_over(self, large_corpus):
        result = pre_sample(large_corpus, n=1000, seed=42)
        assert len(result) == 1000

    def test_reproducible_with_same_seed(self, large_corpus):
        r1 = pre_sample(large_corpus, n=1000, seed=42)
        r2 = pre_sample(large_corpus, n=1000, seed=42)
        assert [r.review_id for r in r1] == [r.review_id for r in r2]

    def test_different_seeds_give_different_results(self, large_corpus):
        r1 = pre_sample(large_corpus, n=1000, seed=42)
        r2 = pre_sample(large_corpus, n=1000, seed=99)
        assert [r.review_id for r in r1] != [r.review_id for r in r2]

    def test_preserves_tier_proportions(self, large_corpus):
        result = pre_sample(large_corpus, n=1000, seed=42)
        neg = sum(1 for r in result if _rating_tier(r.rating) == "neg")
        pos = sum(1 for r in result if _rating_tier(r.rating) == "pos")
        neu = sum(1 for r in result if _rating_tier(r.rating) == "neu")
        # Original has 800 neg (53%), 200 neu (13%), 500 pos (33%)
        # Proportional draw should give roughly: neg ~530, neu ~130, pos ~330
        assert 450 <= neg <= 600, f"neg count {neg} out of expected range"
        assert 80 <= neu <= 180, f"neu count {neu} out of expected range"
        assert 270 <= pos <= 400, f"pos count {pos} out of expected range"
        assert neg + neu + pos == 1000


# ---------------------------------------------------------------------------
# stratified_sample
# ---------------------------------------------------------------------------

class TestStratifiedSample:
    def test_basic_output_shape(self, small_corpus, default_cfg):
        result = stratified_sample(small_corpus, default_cfg.sampling)
        assert isinstance(result.reviews, list)
        assert len(result.reviews) > 0
        assert result.metadata.final_sample_size == len(result.reviews)

    def test_caps_respected_per_week(self, small_corpus, default_cfg):
        result = stratified_sample(small_corpus, default_cfg.sampling)
        from collections import defaultdict
        from pulse.phase02.sampler import _rating_tier

        week_tier_counts: dict[tuple[int, str], int] = defaultdict(int)
        for r in result.reviews:
            week = r.review_date.isocalendar()[1]
            tier = _rating_tier(r.rating)
            week_tier_counts[(week, tier)] += 1

        for (week, tier), count in week_tier_counts.items():
            cap = {"neg": default_cfg.sampling.neg_cap, "neu": default_cfg.sampling.neu_cap, "pos": default_cfg.sampling.pos_cap}[tier]
            assert count <= cap, f"Week {week} tier {tier}: {count} > cap {cap}"

    def test_reproducible_same_seed(self, small_corpus, default_cfg):
        r1 = stratified_sample(small_corpus, default_cfg.sampling)
        r2 = stratified_sample(small_corpus, default_cfg.sampling)
        assert [r.review_id for r in r1.reviews] == [r.review_id for r in r2.reviews]

    def test_different_seeds_differ(self, small_corpus):
        cfg_a = SamplingConfig(seed=42)
        cfg_b = SamplingConfig(seed=99)
        r1 = stratified_sample(small_corpus, cfg_a)
        r2 = stratified_sample(small_corpus, cfg_b)
        # With enough data, different seeds should produce different orderings.
        assert [r.review_id for r in r1.reviews] != [r.review_id for r in r2.reviews]

    def test_metadata_populated(self, small_corpus, default_cfg):
        result = stratified_sample(small_corpus, default_cfg.sampling)
        meta = result.metadata
        assert meta.seed == default_cfg.sampling.seed
        assert meta.neg_cap == default_cfg.sampling.neg_cap
        assert meta.neu_cap == default_cfg.sampling.neu_cap
        assert meta.pos_cap == default_cfg.sampling.pos_cap
        assert len(meta.weeks_covered) > 0
        assert meta.pre_sample_size <= default_cfg.sampling.pre_sample_n
        assert meta.final_sample_size == len(result.reviews)

    def test_all_reviews_in_original_corpus(self, small_corpus, default_cfg):
        result = stratified_sample(small_corpus, default_cfg.sampling)
        original_ids = {r.review_id for r in small_corpus}
        for r in result.reviews:
            assert r.review_id in original_ids

    def test_no_duplicate_review_ids(self, small_corpus, default_cfg):
        result = stratified_sample(small_corpus, default_cfg.sampling)
        ids = [r.review_id for r in result.reviews]
        assert len(ids) == len(set(ids))

    def test_large_corpus_token_budget(self, large_corpus, default_cfg):
        """Sample from 1500 reviews should stay under ~9K tokens (DEC-012)."""
        result = stratified_sample(large_corpus, default_cfg.sampling)
        avg_tokens_per_review = 32
        estimated_tokens = result.metadata.final_sample_size * avg_tokens_per_review
        assert estimated_tokens <= 9_000, (
            f"Sample produces ~{estimated_tokens} tokens, exceeds Stage A budget"
        )

    def test_weeks_covered_in_metadata(self, small_corpus, default_cfg):
        result = stratified_sample(small_corpus, default_cfg.sampling)
        # small_corpus spans 3 weeks
        assert len(result.metadata.weeks_covered) == 3

    def test_empty_corpus_returns_empty(self, default_cfg):
        result = stratified_sample([], default_cfg.sampling)
        assert result.reviews == []
        assert result.metadata.final_sample_size == 0


# ---------------------------------------------------------------------------
# Rating tier helper
# ---------------------------------------------------------------------------

class TestRatingTier:
    def test_one_star_is_neg(self):
        assert _rating_tier(1) == "neg"

    def test_two_star_is_neg(self):
        assert _rating_tier(2) == "neg"

    def test_three_star_is_neu(self):
        assert _rating_tier(3) == "neu"

    def test_four_star_is_pos(self):
        assert _rating_tier(4) == "pos"

    def test_five_star_is_pos(self):
        assert _rating_tier(5) == "pos"
