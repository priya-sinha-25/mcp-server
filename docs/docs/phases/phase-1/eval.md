# Phase 1 Evaluation: Review Ingest & Normalization

**Phase goal:** Public store exports (8–12 weeks) parse into normalized, deduped, PII-stripped reviews.

---

## Test Checklist

| # | Test | How to verify | Pass? |
|---|------|---------------|-------|
| 1.1 | App Store export parses | Run ingest on sample; expected row count ± dedupe rules | ☐ |
| 1.2 | Play Store export parses | Same as 1.1 for Play format | ☐ |
| 1.3 | Date window 8–12 weeks | Reviews outside window excluded; boundary dates documented | ☐ |
| 1.4 | Dedupe | Duplicate `text`+`date` (or defined key) collapsed | ☐ |
| 1.5 | Empty reviews dropped | Rows with no substantive `text` removed | ☐ |
| 1.6 | PII stripping | Fixture with fake email/username redacted in output | ☐ |
| 1.7 | Schema stable | Output JSON matches documented fields | ☐ |

---

## Sample Acceptance Data

Use **synthetic** fixtures in repo only. Real exports stay in gitignored `data/`.

| Fixture | Expected behavior |
|---------|-------------------|
| `tests/fixtures/app_store_sample.csv` | ≥1 normalized review per valid row |
| `tests/fixtures/play_store_sample.csv` | Same |
| `tests/fixtures/pii_sample.csv` | No email/username patterns in output |

---

## Automated Checks

```bash
pytest tests/test_ingest.py -v
```

---

## Exit Criteria

1. `ingest_reviews` returns normalized array for **both** store formats used by the product.
2. **100%** of published-bound reviews fall within configured 8–12 week window.
3. PII validator passes on all fixture outputs (zero high-confidence PII fields).
4. Unit test coverage for parsers ≥80% lines (or team-agreed minimum documented in decision log).

---

## Metrics to Record

| Metric | Value |
|--------|-------|
| Input rows | |
| Output reviews | |
| Deduped count | |
| PII redactions | |

---

## Sign-off

| Role | Name | Date | Notes |
|------|------|------|-------|
| Implementer | | | |
| Reviewer | | | |

**Phase 1 complete:** ☐ Yes → proceed to [Phase 2](../phase-2/eval.md)
