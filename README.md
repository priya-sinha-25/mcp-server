# Weekly Review Pulse Agent

Turn public App Store and Play Store review exports into a weekly one-page pulse, delivered via Google Docs and Gmail (MCP).

## Documentation

| Doc | Path |
|-----|------|
| Problem statement | [docs/docs/problemstatement.md](docs/docs/problemstatement.md) |
| Architecture | [docs/docs/architecture.md](docs/docs/architecture.md) |
| Implementation plan | [docs/docs/implementationplan.md](docs/docs/implementationplan.md) |
| Decisions | [docs/docs/decision.md](docs/docs/decision.md) |

## Project layout

```
config/           # product.yaml (lookback, column maps)
data/             # gitignored real exports
data/groww/       # Groww export drop-folder + instructions
phases/           # phase-01 … phase-05 README + status
src/pulse/
  models.py       # NormalizedReview, IngestResult, …
  phase01/        # ingestion (implemented)
  phase02/ …      # placeholders
tests/
  fixtures/       # synthetic CSV samples
  phase01/        # Phase 1 tests
```

## Phase 1 — Ingestion (current)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"
pytest tests/phase01 -v
```

### Groww reviews (Google Play only)

Download from the public [Groww Play listing](https://play.google.com/store/apps/details?id=com.nextbillion.groww&hl=en_IN) (8–12 weeks):

```bash
python scripts/download_groww_play_reviews.py --weeks 12
pulse-ingest data/groww/groww_play_store_reviews.csv --output data/groww/normalized_reviews.json
```

Files (gitignored under `data/`):

- `data/groww/groww_play_store_reviews.csv` — raw download
- `data/groww/normalized_reviews.json` — Phase 1 output

## License

Course / milestone project.
"# mcp-server" 
