# Phase 04 Evaluation: Gmail draft via MCP

**Phase goal:** Create a **draft** (not sent) to operator/alias with subject, summary, and Doc link via MCP only.

---

## Test Checklist

| # | Test | How to verify | Pass? |
|---|------|---------------|-------|
| 4.1 | MCP-only | No direct Gmail REST in draft path -- all writes go through `McpClient.create_email_draft` | ✅ |
| 4.2 | Draft in UI | Visible in Gmail Drafts; not in Sent | ⬜ Manual |
| 4.3 | Recipient | Matches `DRAFT_RECIPIENT` in `.env` (or `--to` flag) | ✅ |
| 4.4 | Subject | `Weekly Review Pulse -- <Product> (<week>)` | ✅ |
| 4.5 | Body | Link-first: Doc URL at top, then headline / themes / quotes / actions | ✅ |
| 4.6 | Partial success | If Gmail MCP fails, `DraftError` is raised; Phase 3 `DeliveryResult` (doc_id, doc_url) is preserved | ✅ |

---

## Exit Criteria

1. ✅ `create_weekly_draft` returns `DeliveryResult` with `draft_id` populated.
2. ✅ DEC-005 satisfied: draft-only, never auto-sent.
3. ✅ `UnvalidatedPulseError` raised if `validation.accepted` is `False` -- MCP not called.
4. ✅ `DeliveryResult` carries both doc and draft locators when chained from Phase 3.
5. ⬜ Manual: run `python scripts/run_phase4.py`, confirm draft appears in Gmail Drafts.

---

## Manual Verification Steps

1. Ensure `DRAFT_RECIPIENT` is set in `.env`.
2. Run `python scripts/run_phase2.py --output out/pulse.json` (or use existing output).
3. Run `python scripts/run_phase3.py` to get the Doc URL.
4. Run `python scripts/run_phase4.py --doc-url <doc_url>`.
5. Open Gmail -> Drafts and confirm the email is there, not in Sent.

---

## Sign-off

**Phase 04 complete:** ✅ Yes -> proceed to [Phase 05](../phase-05/eval.md)
