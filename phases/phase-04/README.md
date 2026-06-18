# Phase 04 -- Gmail draft via MCP

**Status:** Implemented

**Code:** `src/pulse/phase04/`

**Eval:** [docs/docs/phases/phase-04/eval.md](../../docs/docs/phases/phase-04/eval.md)

## Modules

| File | Responsibility |
|------|---------------|
| `email_formatter.py` | Builds subject line and email body from `WeeklyPulse` (link-first: Doc URL then full pulse). |
| `drafter.py` | `create_weekly_draft()` -- validation guard + MCP call -> `DeliveryResult` with `draft_id`. |

## Usage

```python
from pulse.phase04 import create_weekly_draft
from pulse.phase02.validator import validate_pulse

validation = validate_pulse(pulse, corpus)
delivery = create_weekly_draft(
    pulse,
    doc_url=delivery.doc_url,   # from Phase 3
    validation=validation,
    to="you@example.com",       # or set DRAFT_RECIPIENT in .env
)
print(delivery.draft_id)
```

## Runner

```bash
# Create Gmail draft from the last Phase 2 output
python scripts/run_phase4.py

# Specify recipient and Doc URL explicitly
python scripts/run_phase4.py --to you@example.com --doc-url https://docs.google.com/...
```

## Configuration

Set in `.env` (see `.env.example`):

```
DRAFT_RECIPIENT=you@example.com
```

The draft is created but **never auto-sent** (DEC-005). Review it in Gmail Drafts before sending.

## Tests

```bash
pytest tests/phase04/ -v
```
