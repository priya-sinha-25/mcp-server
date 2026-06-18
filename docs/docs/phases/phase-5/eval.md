# Phase 5 Evaluation: Gmail Draft via MCP

**Phase goal:** Create a **draft** email (not sent) to self or alias with pulse summary and Doc link via MCP.

---

## Test Checklist

| # | Test | How to verify | Pass? |
|---|------|---------------|-------|
| 5.1 | MCP-only path | No direct Gmail REST client in draft path | ☐ |
| 5.2 | Draft created | MCP returns `draft_id`; visible in Gmail Drafts | ☐ |
| 5.3 | Not sent | Message has `DRAFT` label only; not in Sent | ☐ |
| 5.4 | Correct recipient | To-address matches config (self or alias) | ☐ |
| 5.5 | Subject line | Includes product name and week identifier | ☐ |
| 5.6 | Body content | Summary + working link to Phase 4 Doc | ☐ |
| 5.7 | Partial failure | If Doc URL missing, draft step fails clearly (no empty link silently) | ☐ |

---

## Manual Verification Steps

1. Run `create_weekly_draft` after successful Phase 4 publish.
2. Open Gmail → Drafts.
3. Click Doc link in draft body → opens correct document.
4. Do **not** send (unless explicitly testing send in a separate decision).

---

## Automated Checks

```bash
pytest tests/test_gmail_mcp.py -v
```

---

## Exit Criteria

1. Draft exists in Gmail UI for configured account.
2. DEC-005 satisfied: draft-only, no auto-send in default workflow.
3. Body contains pointer to Doc **or** full pulse if under length policy (document choice in decision log).
4. MCP integration test (mock or live) covers `create_draft` parameters.

---

## Email Template Checklist

| Field | Required content | Pass? |
|-------|------------------|-------|
| Subject | `Weekly Pulse – {product} – {week}` | ☐ |
| Body | Short intro + Doc URL | ☐ |
| Body | No PII | ☐ |

---

## Sign-off

| Role | Name | Date | Notes |
|------|------|------|-------|
| Implementer | | | |
| Reviewer | | | |

**Phase 5 complete:** ☐ Yes → proceed to [Phase 6](../phase-6/eval.md)
