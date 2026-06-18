# Phase 2 Evaluation: Theme Clustering (≤5 themes)

**Phase goal:** Reviews assigned to at most five themes; top three themes identifiable by rank.

---

## Test Checklist

| # | Test | How to verify | Pass? |
|---|------|---------------|-------|
| 2.1 | Theme count cap | `len(themes) <= 5` always | ☐ |
| 2.2 | Full assignment | Every ingested review has exactly one primary theme | ☐ |
| 2.3 | Top 3 computable | Rank by count (or documented rule) yields ordered top 3 | ☐ |
| 2.4 | Labels human-readable | No raw UUID-only theme names in user-facing output | ☐ |
| 2.5 | Reproducibility | Same input + seed → same assignments (or document intentional variance) | ☐ |
| 2.6 | Small corpus edge case | &lt;10 reviews: still ≤5 themes, no crash | ☐ |
| 2.7 | Theme seeds respected | Config seeds appear in final labels or mapping doc | ☐ |

---

## Quality Rubric (manual spot-check)

Review `themes.json` for one real run (local only):

| Criterion | Pass? |
|-----------|-------|
| Themes are product-meaningful (not generic “positive/negative” only) | ☐ |
| No single theme is &gt;60% of reviews unless corpus &lt;15 reviews | ☐ |
| Largest theme is plausibly “what users talk about most” | ☐ |

---

## Automated Checks

```bash
pytest tests/test_clustering.py -v
```

---

## Exit Criteria

1. Hard cap of **5 themes** enforced in code (not prompt-only).
2. **Top 3** theme list exported with counts and optional one-line summary each.
3. `themes.json` includes `review_ids` per theme for traceability to quotes in Phase 3.
4. Clustering module documented in architecture or README (algorithm choice in decision log if changed).

---

## Metrics to Record

| Theme | Review count | % of total |
|-------|--------------|------------|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |

---

## Sign-off

| Role | Name | Date | Notes |
|------|------|------|-------|
| Implementer | | | |
| Reviewer | | | |

**Phase 2 complete:** ☐ Yes → proceed to [Phase 3](../phase-3/eval.md)
