# Phase 0 Evaluation: Foundation & MCP Wiring

**Phase goal:** Repo scaffolded; Google Docs and Gmail MCP servers configured and callable from the agent runtime.

---

## Test Checklist

| # | Test | How to verify | Pass? |
|---|------|---------------|-------|
| 0.1 | Repo structure exists | `src/`, `config/`, `tests/`, `data/` gitignored | ☐ |
| 0.2 | MCP config documented | README or `mcp.json` lists Docs + Gmail servers | ☐ |
| 0.3 | Docs MCP reachable | Agent/tool call succeeds (e.g. create test doc or list capability) | ☐ |
| 0.4 | Gmail MCP reachable | Agent/tool call succeeds (e.g. create test draft or health check) | ☐ |
| 0.5 | No secrets in git | `git status` / secret scan: no tokens in tracked files | ☐ |
| 0.6 | DEC-006 resolved | [decision.md](../../decision.md) records accepted orchestration runtime | ☐ |

---

## Automated Checks (when code exists)

```bash
# Example placeholders — adjust to your test runner
pytest tests/test_mcp_smoke.py -v
```

Expected: smoke tests skip gracefully if MCP unavailable locally, or pass in CI with mocked MCP.

---

## Exit Criteria (must all pass)

1. **Both** MCP servers (Docs and Gmail) respond successfully to at least one tool invocation each in the target environment.
2. Team can run documented setup from a clean clone in under 30 minutes (excluding OAuth consent).
3. Orchestration choice (DEC-006) is **accepted** in `decision.md`.
4. No application code uses Google REST SDK as the primary Docs/Gmail path.

---

## Known Risks

| Risk | Mitigation |
|------|------------|
| MCP server not in course environment | Escalate early; document fallback connector name in decision log |
| OAuth consent blocked | Use shared test account; document redirect URI |

---

## Sign-off

| Role | Name | Date | Notes |
|------|------|------|-------|
| Implementer | | | |
| Reviewer | | | |

**Phase 0 complete:** ☐ Yes → proceed to [Phase 1](../phase-1/eval.md)
