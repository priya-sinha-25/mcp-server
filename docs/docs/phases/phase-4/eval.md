# Phase 4 Evaluation: Google Docs via MCP

**Phase goal:** Publish the validated pulse to Google Docs using **MCP tools only**.

---

## Test Checklist

| # | Test | How to verify | Pass? |
|---|------|---------------|-------|
| 4.1 | MCP-only path | Grep/code review: no direct Google Docs REST client in publish path | ☐ |
| 4.2 | Document created/updated | MCP tool returns `doc_id` / URL | ☐ |
| 4.3 | Content matches pulse | Doc contains top 3 themes, 3 quotes, 3 actions | ☐ |
| 4.4 | Formatting readable | Headings and lists render correctly in Docs UI | ☐ |
| 4.5 | Link shareable | URL opens for intended account (course test account) | ☐ |
| 4.6 | Error handling | Simulated MCP failure → no false success; local `pulse.draft.md` retained | ☐ |
| 4.7 | Idempotency (if implemented) | Second run updates same doc per config | ☐ |

---

## Manual Verification Steps

1. Run `publish_pulse_to_docs` with Phase 3 golden `pulse.draft.md`.
2. Open document URL in browser.
3. Confirm word count in Doc ≤250 (or document states summary if split).
4. Confirm no PII visible in Doc body.

---

## Automated Checks

```bash
pytest tests/test_docs_mcp.py -v
# Use MCP mock in CI; live MCP optional in integration job
```

---

## Exit Criteria

1. Successful MCP publish returns **document URL** stored in run metadata.
2. Independent reviewer confirms Doc content matches validated pulse (diff or checklist).
3. Architecture and decision log still state MCP-first (DEC-001 unchanged).
4. At least one integration test (mocked or live) asserts tool name and argument shape.

---

## Artifacts to Capture (milestone evidence)

| Artifact | Location |
|----------|----------|
| Doc URL | Run log / README demo section |
| Screenshot | Optional: Doc first screen (redact account if needed) |

---

## Sign-off

| Role | Name | Date | Notes |
|------|------|------|-------|
| Implementer | | | |
| Reviewer | | | |

**Phase 4 complete:** ☐ Yes → proceed to [Phase 5](../phase-5/eval.md)
