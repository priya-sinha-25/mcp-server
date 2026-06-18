# Phase 3 Evaluation: Pulse Composition

**Phase goal:** Generate a valid weekly pulse (top 3 themes, 3 verbatim quotes, 3 action ideas, ≤250 words) without Google writes.

---

## Test Checklist

| # | Test | How to verify | Pass? |
|---|------|---------------|-------|
| 3.1 | Top 3 themes present | Pulse lists exactly 3 theme sections (subset of ≤5) | ☐ |
| 3.2 | Three quotes | Exactly 3 quoted snippets | ☐ |
| 3.3 | Verbatim integrity | Each quote matches source review `text` (substring match after normalization) | ☐ |
| 3.4 | No invented quotes | Random spot-check: quote not in corpus → fail | ☐ |
| 3.5 | Three action ideas | Exactly 3 actionable items, tied to themes | ☐ |
| 3.6 | Word limit | Total word count ≤250 | ☐ |
| 3.7 | No PII | Validator passes on pulse text | ☐ |
| 3.8 | Scannable format | Headings/bullets; readable in &lt;2 minutes | ☐ |

---

## Content Rubric (manual)

| Criterion | 1 (poor) | 3 (good) | Pass? |
|-----------|----------|----------|-------|
| Action ideas | Vague (“improve app”) | Specific, tied to theme evidence | ☐ |
| Theme insights | Restates theme name only | Adds “so what” in one line | ☐ |
| Quotes | Out of context | Illustrate the theme | ☐ |

---

## Automated Checks

```bash
pytest tests/test_compose.py tests/test_validators.py -v
```

Validator must **fail** pipeline on:

- Word count &gt;250  
- Quote without `review_id` provenance  
- Detected PII patterns  

---

## Exit Criteria

1. `compose_pulse` produces `pulse.draft.md` passing all automated validators.
2. Manual rubric score ≥2/3 average on action ideas and theme insights (reviewer sign-off).
3. No Google Docs or Gmail calls in this phase (composition only).
4. Sample pulse committed as `tests/fixtures/expected_pulse_structure.md` (synthetic quotes).

---

## Sample Output Structure

```markdown
# Weekly Pulse – {Product} – {Week}

## Top themes
1. ...
2. ...
3. ...

## What users said
> "..."
> "..."
> "..." 

## Recommended actions
1. ...
2. ...
3. ...
```

---

## Sign-off

| Role | Name | Date | Notes |
|------|------|------|-------|
| Implementer | | | |
| Reviewer | | | |

**Phase 3 complete:** ☐ Yes → proceed to [Phase 4](../phase-4/eval.md)
