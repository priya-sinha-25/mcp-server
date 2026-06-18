# Phase 05 Evaluation: End-to-end orchestration & hardening

**Phase goal:** One run completes [architecture.md](../../architecture.md) §8 happy path; Groq + MCP wired; observability and failure matrix in place.

---

## Test Checklist

| # | Test | How to verify | Pass? |
|---|------|---------------|-------|
| 5.1 | Single entrypoint | Documented command runs full pipeline | ☐ |
| 5.2 | Groq + MCP smoke | Both external systems reachable | ☐ |
| 5.3 | E2E real export | 8–12 week export → Doc + draft | ☐ |
| 5.4 | Dry-run | Stops before MCP; still validates | ☐ |
| 5.5 | Logging | Run id, counts, refs—no PII blobs | ☐ |
| 5.6 | Regression | Phase 01–04 eval criteria still pass | ☐ |

---

## Milestone Acceptance Matrix

| Requirement | Evidence | Pass? |
|-------------|----------|-------|
| Import 8–12 weeks reviews | Run log | ☐ |
| ≤5 themes; pulse top 3 | Artifacts + Doc | ☐ |
| 3 verbatim quotes, 3 actions, ≤250 words | Validator + Doc | ☐ |
| Google Docs via MCP | Doc URL | ☐ |
| Gmail draft | Draft id | ☐ |
| MCP-first | Code review + DEC-001 | ☐ |
| No PII in artifacts | Validators + spot-check | ☐ |
| Public exports only | README | ☐ |

---

## Exit Criteria

1. E2E run on real (non-commit) export data.
2. Reviewer sign-off on milestone matrix.
3. README covers setup, weekly run, deployment shapes (§10).

---

## Sign-off

**Project complete:** ☐ Yes
