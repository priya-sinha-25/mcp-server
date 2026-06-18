# Phase 02 Evaluation: Theming & pulse generation + validation

**Phase goal:** Stratified sample → Groq Stage A (≤5 themes) → Groq Stage B (`WeeklyPulse`) → deterministic validators pass. **No MCP calls.**

---

## Test Checklist

| # | Test | How to verify | Pass? |
|---|------|---------------|-------|
| 2.1 | Sample cap | Full normalized corpus never sent to Groq | ☐ |
| 2.2 | Sample reproducibility | Same seed + caps → same sample | ☐ |
| 2.3 | Theme count | ≤5 `ThemeCluster` always | ☐ |
| 2.4 | Stage A JSON | Valid schema; bounded retry on invalid JSON | ☐ |
| 2.5 | Pulse shape | Top 3 themes, 3 quotes, 3 actions, ≤250 words | ☐ |
| 2.6 | Quote provenance | Quotes ⊆ normalized corpus | ☐ |
| 2.7 | Validators gate | Failing pulse blocked; Stage B repair retry only | ☐ |
| 2.8 | No MCP | No Docs/Gmail tool calls in this phase | ☐ |

---

## Automated Checks

```bash
pytest tests/test_sample.py tests/test_groq_stages.py tests/test_validators.py -v
```

---

## Exit Criteria

1. `stratified_sample`, `discover_themes`, `draft_pulse`, `validate_pulse` implemented.
2. Groq model + prompt version pinned in [decision.md](../../decision.md).
3. Accepted `WeeklyPulse` / `pulse.draft.md` on synthetic + one local real sample run.

---

## Sign-off

**Phase 02 complete:** ☐ Yes → proceed to [Phase 03](../phase-03/eval.md)
