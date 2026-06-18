# Phase 01 — Ingestion & normalization

**Status:** Implemented

**Code:** `src/pulse/phase01/`

**Eval:** [docs/docs/phases/phase-01/eval.md](../../docs/docs/phases/phase-01/eval.md)

## Usage

```bash
pip install -e ".[dev]"
pulse-ingest tests/fixtures/app_store_sample.csv --output out/reviews.json
```

Or from Python:

```python
from pulse.phase01 import ingest_reviews

result = ingest_reviews(["data/app_store.csv", "data/play_store.csv"])
print(len(result.reviews), result.metadata.warnings)
```

## Tests

```bash
pytest tests/phase01 -v
```
