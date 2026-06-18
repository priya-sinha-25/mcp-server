# Implementation Plan: Weekly Review Pulse Agent (MCP)

Phased delivery plan for the system in [architecture.md](./architecture.md) and [problemstatement.md](./problemstatement.md).

**Pipeline (do not reorder):** Ingest → Stratified sample → Stage A (Groq) → Stage B (Groq) → Validate → Docs MCP → Gmail MCP

---

## Guiding principles

1. **Architecture is the contract** — Component boundaries, data contracts (`NormalizedReview`, `ThemeCluster`, `WeeklyPulse`, `DeliveryResult`), and ordering rules live in [architecture.md](./architecture.md); this plan only schedules *when* each piece is built.
2. **Validate before side effects** — No MCP calls with pulse content until deterministic validation passes ([architecture.md](./architecture.md) §5.3).
3. **Public data only** — Ingestion honors export-only, ToS-safe sourcing; scope creep into scraping is out of bounds.
4. **Decisions are explicit** — Integration choices, counting rules, and artifact strategies are recorded in [decision.md](./decision.md), not left implicit.

Do not start a phase until its eval checklist passes.

---

## Phase overview

| Phase | Focus | Evaluation |
|-------|--------|------------|
| 1 | Ingestion & normalization | [phases/phase-01/eval.md](./phases/phase-01/eval.md) |
| 2 | Theming & pulse generation + validation | [phases/phase-02/eval.md](./phases/phase-02/eval.md) |
| 3 | Google Docs via MCP | [phases/phase-03/eval.md](./phases/phase-03/eval.md) |
| 4 | Gmail draft via MCP | [phases/phase-04/eval.md](./phases/phase-04/eval.md) |
| 5 | End-to-end orchestration & hardening | [phases/phase-05/eval.md](./phases/phase-05/eval.md) |

| Phase | Architecture sections |
|-------|----------------------|
| 1 | §5.1 |
| 2 | §5.2, §5.3 |
| 3 | §5.4 |
| 4 | §5.5 |
| 5 | §3, §5.6, §8–§10 |

---

## Phase 1 — Ingestion & normalization

### Intent

Establish a **trustworthy factual base**: every downstream theme, quote, and action will ultimately be justified against normalized review records. If ingestion is sloppy, the LLM will confidently summarize garbage.

### In scope

- Selecting **which export formats** you will support for App Store and Play Store (may differ per platform).
- Defining the **canonical review model** (`NormalizedReview`): what fields exist, optional vs required, how missing values are represented.
- Specifying the **lookback window (8–12 weeks)** in calendar terms: inclusive/exclusive bounds, timezone handling.
- **Deduping rules** for near-identical reviews and cross-platform duplicates if the same user narrative appears twice.
- **PII posture at ingestion**: which columns are dropped, hashed, or never stored; alignment with “no PII in artifacts.”
- Parsing tolerance: header variants, missing optional fields, benign encoding issues.
- Failure behavior: unreadable files → actionable error; partial files → ingest valid rows and surface warnings.

### Out of scope

- Groq calls, theme discovery, pulse drafting, validation, MCP.
- Sending any data to Google.

### Deliverables

- `ingest_reviews(paths) → NormalizedReview[]`
- Column maps and dedupe rules documented in [decision.md](./decision.md)
- Synthetic fixtures under `tests/fixtures/`; real exports in gitignored `data/`
- Run metadata: ingest counts, warnings

### Exit criteria

See [phases/phase-01/eval.md](./phases/phase-01/eval.md).

---

## Phase 2 — Theming & pulse generation + validation

### Intent

Turn normalized reviews into a **milestone-shaped, validator-clean pulse** before any Google write. Sampling keeps Groq inputs bounded; staged LLM calls keep themes and narrative separable; deterministic validation is the gate to Phases 3–4.

### Groq rate limits and token budget

Model: `llama-3.3-70b-versatile` (free tier)

| Limit | Value |
|-------|-------|
| Requests per minute (RPM) | 30 |
| Requests per day (RPD) | 1,000 |
| Tokens per minute (TPM) | **12,000** ← binding within a run |
| Tokens per day (TPD) | **100,000** ← binding across the day |

**Per-run token breakdown:**

| Call | Tokens |
|------|--------|
| Stage A input (system prompt ~600 + ~190 reviews × 32 tokens) | ~6,680 |
| Stage A response (≤5 themes × ~100 tokens) | ~500 |
| Stage B input (themes + evidence + system prompt ~800) | ~2,300 |
| Stage B response (WeeklyPulse ≤250 words) | ~340 |
| **Total per run (happy path)** | **~9,820** |
| Worst case with 2 Stage B retries | ~14,500 (spread across minutes — retries happen after validation roundtrip) |

- **TPM:** ~9,820 tokens/run fits within the 12K window for the happy path. Retries add tokens but occur in a subsequent minute after validation roundtrip.
- **TPD:** ~9,820 tokens/run → ~**9 full runs per day** before hitting the 100K cap. Unit tests must mock the Groq client — live calls are for integration smoke tests only.
- **RPD:** 2 calls/run → 500 runs/day max — not a practical constraint.

### LLM: Groq

- **Provider:** Groq (`api.groq.com`, OpenAI-compatible). Auth via `GROQ_API_KEY` env var — never in repo.
- **Model:** `llama-3.3-70b-versatile` for both Stage A and Stage B. Pinned in [decision.md](./decision.md) DEC-011.
- **Stage A temperature:** `0.2` — deterministic theme extraction.
- **Stage B temperature:** `0.5` — enough narrative variation while staying structured.
- **Response format:** `response_format: { type: "json_object" }` on both calls to reduce parse failures before the validator runs.

### Phase 1 data — what we're working with

The Groww Play Store normalized dataset (Phase 1 output) has **~1,880 reviews** across 13 weeks. Key facts:

| Fact | Detail |
|------|--------|
| Total normalized reviews | ~1,880 |
| Working set (pre-sample cap) | **1,000** |
| Rating distribution (full set) | 1★: 758, 2★: 108, 3★: 124, 4★: 178, 5★: 712 |
| Avg tokens per review body | ~32 tokens |
| Titles | Mostly empty in Groww Play data — omit from prompt |
| Platform | Play Store only — no App Store data yet |

### In scope

- **Step 1 — Pre-sample to 1,000 reviews:**
  - Draw proportionally by tier from the full normalized corpus before stratified sampling.
  - Same `seed` → same 1,000 reviews. Stored in `SampleMetadata`.
  - This is the hard working-set cap regardless of corpus size.

- **Step 2 — Stratified sample from the 1,000 (architecture §5.2, DEC-012):**
  - Bucket by rating tier (≤2★, 3★, 4–5★) × ISO week.
  - Per-tier per-week caps: **negative ≤7/week, neutral ≤3/week, positive ≤5/week**.
  - Target: **~190 reviews (~6,700 tokens)** for Stage A input — stays inside the 12K TPM limit with headroom for the system prompt.
  - Reproducible via `seed` + caps in `SampleMetadata`. **Never** send the full corpus to Groq.

- **Stage A — Theme discovery (Groq):** send `(review_id, rating, review_date, body)` for sampled reviews → JSON ≤5 themes (label, one-line description, `review_ids`) → `ThemeCluster[]`.

- **Stage B — Pulse drafting (Groq):** themes + supporting evidence bodies → `WeeklyPulse` (top 3 themes, 3 verbatim quotes, 3 action ideas, executive framing, ≤250 words).

- **Bounded retries:**
  - Stage A — up to 2 retries with stricter system prompt on JSON parse failure. Each retry costs ~7K tokens; abort and surface error if still invalid.
  - Stage B — up to 2 retries with corrective instruction pointing at the specific violated rule. Each retry costs ~2.6K tokens. Retries are rate-limit-aware: if TPD headroom is <3K tokens remaining, skip retry and surface the validation error instead.

- **Validation layer (architecture §5.3):** structural counts; word count ≤250 under fixed policy; quote provenance ⊆ normalized corpus (substring match); PII pattern blocklist.

- Groq client wiring; model + prompt version pinned in [decision.md](./decision.md) DEC-011.
- Output `pulse.draft.md` / structured `WeeklyPulse` on accept.

### Out of scope

- Google Docs or Gmail MCP calls.
- End-to-end orchestrator (Phase 5).

### Deliverables

- `pre_sample(reviews, n=1000, seed) → list[NormalizedReview]` — proportional tier draw
- `stratified_sample(reviews, config) → SampleResult` (reviews + `SampleMetadata`)
- `discover_themes(sample) → ThemeCluster[]` (max 5) — Stage A Groq call
- `draft_pulse(clusters, evidence) → WeeklyPulse` — Stage B Groq call
- `validate_pulse(pulse, corpus) → Accept | Reject(reasons)`
- Unit tests with mocked Groq client (no live calls); one optional integration smoke test

### Exit criteria

See [phases/phase-02/eval.md](./phases/phase-02/eval.md).

---

## Phase 3 — Google Docs via MCP

### Intent

Persist the **validated** weekly pulse where stakeholders read narrative reports—using MCP only, not application-layer Google REST clients.

### In scope

- MCP tool flow: create or update document per [decision.md](./decision.md) (new doc per week vs append-only master log).
- Doc structure: title, date range, sections for themes / evidence / actions.
- Pass **only validated** `WeeklyPulse` content into MCP arguments.
- Capture `document_id`, URL → `DeliveryResult` (doc fields).
- Transient errors: backoff retry; idempotency via naming or `doc_id` config.

### Out of scope

- Gmail draft (Phase 4).
- Re-running ingest or LLM stages inside this phase.

### Deliverables

- `publish_pulse_to_docs(pulse) → { doc_id, url }`
- Manual verification steps in phase eval

### Exit criteria

See [phases/phase-03/eval.md](./phases/phase-03/eval.md).

---

## Phase 4 — Gmail draft via MCP

### Intent

Prepare **distribution without forcing send**: operator gets a draft with product/week subject and body policy from [decision.md](./decision.md) (link-first to Doc + summary, or inline pulse if allowed).

### In scope

- MCP `create_draft` to operator or alias from config.
- Subject reflects product and week.
- Default: **draft**, not send.
- **Partial success:** if Phase 3 succeeded and Gmail fails, preserve Doc reference and surface retry.

### Out of scope

- Auto-send (unless explicitly changed in decision log).
- Direct Gmail REST in application layer.

### Deliverables

- `create_weekly_draft(pulse, doc_url) → draft_id`
- Complete `DeliveryResult` (doc + draft locators)

### Exit criteria

See [phases/phase-04/eval.md](./phases/phase-04/eval.md).

---

## Phase 5 — End-to-end orchestration & hardening

### Intent

Wire the full [happy path](./architecture.md#8-sequence-happy-path) in one operator run; prove Groq + MCP host integration; make failures visible and recoverable; document interactive and batch deployment.

### In scope

- **External wiring (architecture §3):** Groq API; MCP host + Docs + Gmail servers—smoke-tested if not already done in Phase 2–4.
- **Orchestrator (architecture §5.6):** `ingest → sample → Stage A → Stage B → validate → Docs MCP → Gmail MCP`
- Entrypoint, e.g. `run_weekly_pulse --export … --week YYYY-Www`
- **Dry-run / debug mode:** stop before MCP writes; still run validators.
- **Observability:** run id, ingest counts, sample size, model + prompt version, validation outcome, Doc + draft refs—no PII blobs in logs.
- **Failure matrix (architecture §9):** malformed export, Groq JSON, validation, Docs retry, Gmail partial success, auth expiry.
- README: export sources, weekly run, [deployment shapes](./architecture.md#10-deployment-shapes), draft review before send.
- Repo scaffold, config, tests, `data/` gitignored (if not done earlier).
- Milestone demo evidence: Doc URL + draft id from one real run.

### Out of scope

- New pulse format or theme cap changes without decision log + schema version bump.
- Scraping or non-export review sources.

### Deliverables

- Single documented entrypoint
- E2E test or scripted demo path
- [phases/phase-05/eval.md](./phases/phase-05/eval.md) including milestone acceptance matrix

### Exit criteria

See [phases/phase-05/eval.md](./phases/phase-05/eval.md).

---

## Milestone traceability

| [problemstatement.md](./problemstatement.md) requirement | Phase |
|--------------------------------------------------------|-------|
| Import 8–12 weeks of public reviews | 1 |
| ≤5 themes; pulse shows top 3 | 2 |
| 3 verbatim quotes, 3 action ideas, ≤250 words | 2 |
| Google Docs via MCP | 3 |
| Gmail draft to self/alias | 4 |
| MCP-first (no primary REST Google client) | 3, 4, 5 |
| No PII in artifacts | 1, 2 |
| End-to-end weekly pulse | 5 |

---

## Related documents

| Document | Role |
|----------|------|
| [architecture.md](./architecture.md) | System design source of truth |
| [decision.md](./decision.md) | Export formats, Groq model, sampling caps, word-count policy, Doc/Gmail strategy |
| [phases/phase-NN/eval.md](./phases/phase-01/eval.md) | Per-phase testing and exit criteria |

---

## Suggested timeline

| Week | Phases |
|------|--------|
| 1 | 1 |
| 2 | 2 |
| 3 | 3, 4 |
| 4 | 5 + buffer |
