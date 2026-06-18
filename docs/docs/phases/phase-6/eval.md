# Phase 6 Evaluation: End-to-End Orchestration

**Phase goal:** Single agent/CLI run completes the full milestone: **export → pulse → Google Doc → Gmail draft**.

---

## Test Checklist

| # | Test | How to verify | Pass? |
|---|------|---------------|-------|
| 6.1 | Single entrypoint | One documented command runs full pipeline | ☐ |
| 6.2 | Real export E2E | 8–12 week public export → final draft (staging account) | ☐ |
| 6.3 | Theme cap E2E | ≤5 themes in run artifacts; pulse shows top 3 | ☐ |
| 6.4 | Pulse content E2E | 3 quotes, 3 actions, ≤250 words in Doc | ☐ |
| 6.5 | MCP-only Google | No primary REST path for Docs/Gmail | ☐ |
| 6.6 | Dry-run mode | Optional flag stops before MCP writes; still validates pulse | ☐ |
| 6.7 | Logging | Run log has counts, doc URL, draft id—no PII blobs | ☐ |
| 6.8 | README complete | Setup, export instructions, weekly run, troubleshooting | ☐ |

---

## Milestone Acceptance Matrix

Maps to [problemstatement.md](../../problemstatement.md):

| Requirement | Evidence | Pass? |
|-------------|----------|-------|
| Import 8–12 weeks reviews | Run log + normalized count | ☐ |
| ≤5 themes, pulse top 3 | `themes.json` + Doc | ☐ |
| 3 verbatim quotes | Provenance check + Doc | ☐ |
| 3 action ideas | Doc / pulse | ☐ |
| ≤250 words | Validator output | ☐ |
| Google Docs delivery | Doc URL | ☐ |
| Gmail draft to self | Draft screenshot or id | ☐ |
| MCP-first integrations | Code review + DEC-001 | ☐ |
| No PII in artifacts | Validator + manual spot-check | ☐ |
| Public exports only | Process doc / README | ☐ |

---

## End-to-End Test Script

```bash
# Adjust paths and CLI name to your implementation
python -m src.agent run_weekly_pulse \
  --export data/reviews.csv \
  --week 2026-W22 \
  --config config/product.yaml

# Optional dry-run
python -m src.agent run_weekly_pulse --dry-run ...
```

**Expected artifacts after successful run:**

| Artifact | Present? |
|----------|----------|
| `themes.json` (or equivalent) | ☐ |
| `pulse.draft.md` | ☐ |
| Google Doc URL | ☐ |
| Gmail draft id | ☐ |

---

## Performance & Reliability (guidance)

| Metric | Target |
|--------|--------|
| E2E runtime (typical corpus &lt;5k reviews) | &lt;10 min incl. LLM |
| Recoverable failure | Re-run idempotent doc update if configured |

---

## Exit Criteria (milestone done)

1. **All** Phase 0–5 eval exit criteria still pass (regression).
2. E2E run completed once on real (non-commit) export data by implementer.
3. Reviewer sign-off on milestone acceptance matrix (100% Pass).
4. Demo assets listed in README (Doc link + draft confirmation steps).

---

## Final Sign-off

| Role | Name | Date | Notes |
|------|------|------|-------|
| Implementer | | | |
| Reviewer | | | |
| Milestone submitted | | | |

**Project complete:** ☐ Yes
