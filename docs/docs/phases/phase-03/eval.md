# Phase 03 Evaluation: Google Docs via MCP

**Phase goal:** Publish **validated** pulse to Google Docs using MCP only (no application-layer Docs REST).

---

## Test Checklist

| # | Test | How to verify | Pass? |
|---|------|---------------|-------|
| 3.1 | MCP-only | No direct Google Docs REST in publish path — all Docs writes go through `McpClient.append_to_doc` → MCP server | ✅ |
| 3.2 | Validated input only | `publish_pulse_to_docs(validation=rejected)` raises `UnvalidatedPulseError` before any MCP call | ✅ |
| 3.3 | Doc created/updated | `DeliveryResult.doc_id` and `doc_url` returned on success | ✅ |
| 3.4 | Content match | Formatted content contains themes, quotes, actions, week label, headline | ✅ |
| 3.5 | Idempotency | MCP server uses `append` (not create) — re-running appends a new timestamped entry; no duplicate-doc risk | ✅ |

---

## Exit Criteria

1. ✅ `publish_pulse_to_docs` returns `DeliveryResult` with `doc_url` populated.
2. ✅ `UnvalidatedPulseError` raised if `validation.accepted` is `False` — MCP not called.
3. ✅ DEC-001 (MCP-first) satisfied — `McpClient` is the only Docs write path.
4. ⬜ Manual: run `python scripts/run_phase3.py`, confirm entry appears in the target Google Doc.

---

## Manual Verification Steps

1. Set `GOOGLE_DOC_ID` in `.env` to an existing Google Doc you own.
2. Run `python scripts/run_phase2.py --output out/pulse.json` (or use existing output).
3. Run `python scripts/run_phase3.py`.
4. Open the Doc — confirm a new timestamped entry with the pulse content is appended.

---

## Sign-off

**Phase 03 complete:** ✅ Yes → proceed to [Phase 04](../phase-04/eval.md)
