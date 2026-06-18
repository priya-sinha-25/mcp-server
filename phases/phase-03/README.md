# Phase 03 — Google Docs via MCP

**Status:** Implemented

**Code:** `src/pulse/phase03/`

**Eval:** [docs/docs/phases/phase-03/eval.md](../../docs/docs/phases/phase-03/eval.md)

## Modules

| File | Responsibility |
|------|---------------|
| `mcp_client.py` | HTTP adapter for the MCP server (`/append_to_doc`). Retries on 5xx, fails fast on 4xx. |
| `formatter.py` | Renders `WeeklyPulse` into plain-text Doc content (title, themes, quotes, actions). |
| `publisher.py` | `publish_pulse_to_docs()` — validation guard + MCP call → `DeliveryResult`. |

## Usage

```python
from pulse.phase03 import publish_pulse_to_docs
from pulse.phase02.validator import validate_pulse

validation = validate_pulse(pulse, corpus)
delivery = publish_pulse_to_docs(pulse, validation=validation, doc_id="<DOC_ID>")
print(delivery.doc_url)
```

## Runner

```bash
# Publish the last Phase 2 output to Google Docs
python scripts/run_phase3.py

# Override the Doc ID
python scripts/run_phase3.py --doc-id <GOOGLE_DOC_ID>
```

## Configuration

Set in `.env` (see `.env.example`):

```
GOOGLE_DOC_ID=<your_google_doc_id>
MCP_SERVER_URL=https://saksham-mcp-server-production-6213.up.railway.app  # default
```

## Tests

```bash
pytest tests/phase03/ -v
```
