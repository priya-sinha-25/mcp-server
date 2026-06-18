
# Phase 01 Evaluation: Ingestion & normalization

**Phase goal:** Public store exports (8–12 weeks) parse into `NormalizedReview[]`—deduped, PII-minimized, trustworthy for downstream Groq stages.

---

## Test Checklist

| # | Test | How to verify | Pass? |
|---|------|---------------|-------|
| 1.1 | App Store export parses | Run ingest on sample; expected row count ± dedupe rules | ☐ |
| 1.2 | Play Store export parses | Same for Play format | ☐ |
| 1.3 | Date window 8–12 weeks | Out-of-window reviews excluded; bounds documented in [decision.md](../../decision.md) | ☐ |
| 1.4 | Dedupe | Duplicates per decision log collapsed | ☐ |
| 1.5 | Empty reviews dropped | Rows with no substantive body removed | ☐ |
| 1.6 | PII posture | Fixture with fake email/username absent from output | ☐ |
| 1.7 | `NormalizedReview` schema | Stable fields per [architecture.md](../../architecture.md) §7 | ☐ |

---

## Exit Criteria

1. `ingest_reviews` works for **both** supported store formats.
2. **100%** of retained reviews fall within configured 8–12 week window.
3. No high-confidence PII in fixture outputs.
4. Malformed export → readable error (partial ingest only if documented).

---

## Sign-off

**Phase 01 complete:** ☐ Yes → proceed to [Phase 02](../phase-02/eval.md)
