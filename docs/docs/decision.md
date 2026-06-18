# Decision Log

Record **important** technical and business decisions here. Each entry should be immutable once accepted; if we reverse a decision, add a new entry that supersedes the old one.

**Format:** `DEC-NNN` | Date | Status (`proposed` | `accepted` | `superseded`)

---

## Template (copy for new decisions)

```markdown
### DEC-XXX: Title

- **Date:** YYYY-MM-DD
- **Status:** proposed
- **Context:** What problem or constraint forced a choice?
- **Decision:** What we chose.
- **Alternatives considered:** Brief list.
- **Consequences:** Tradeoffs, follow-up work.
```

---

## Decisions

### DEC-001: MCP-first for Google Docs and Gmail

- **Date:** 2026-06-02
- **Status:** accepted
- **Context:** Milestone requires Google Docs and Gmail integration without bespoke OAuth + REST as the primary path; course tooling exposes MCP servers.
- **Decision:** All Docs and Gmail operations go through MCP tool calls from the agent. No first-party Google API client as the default integration layer.
- **Alternatives considered:** Direct Google REST SDK; Zapier/Make; manual copy-paste only.
- **Consequences:** Agent runtime must support MCP (e.g. Cursor, MCP-capable SDK). Local dev depends on MCP server availability and auth setup documented per environment.

---

### DEC-002: Public review exports only (no authenticated scraping)

- **Date:** 2026-06-02
- **Status:** accepted
- **Context:** Store ToS and milestone constraints prohibit scraping behind logins or automation that violates terms.
- **Decision:** Ingest only from user-provided public exports (CSV/JSON) for App Store and Play Store, covering roughly 8–12 weeks.
- **Alternatives considered:** Third-party review APIs; Play Console / App Store Connect APIs with service accounts.
- **Consequences:** Import step is manual or scheduled export outside this agent; pipeline assumes stable column mapping documented in config.

---

### DEC-003: Theme cap and pulse shape

- **Date:** 2026-06-02
- **Status:** accepted
- **Context:** Problem statement fixes clustering and pulse structure for comparability across teams.
- **Decision:**
  - Cluster into **at most 5** themes for the dataset.
  - Weekly pulse highlights **top 3** themes, **3 verbatim quotes**, **3 action ideas**, **≤250 words**.
- **Alternatives considered:** Open-ended theme count; executive summary without quotes.
- **Consequences:** Clustering and composer modules must enforce caps in code, not only in prompts.

---

### DEC-004: PII stripping at ingest (fail closed on publish)

- **Date:** 2026-06-02
- **Status:** accepted
- **Context:** Reviews may contain usernames or identifiable strings; artifacts must not include PII.
- **Decision:** Strip/redact identifiers at normalization; run validator before any MCP write; block publish if high-confidence PII remains.
- **Alternatives considered:** Strip only in final LLM pass; trust model to omit PII.
- **Consequences:** May remove short quotes that are mostly username; document fallback behavior in eval criteria.

---

### DEC-005: Gmail draft to self (not auto-send)

- **Date:** 2026-06-02
- **Status:** accepted
- **Context:** Safer default for course milestone; user reviews content before send.
- **Decision:** Use MCP to create a **draft** to self or alias containing pulse text and/or Doc link. Do not auto-send unless explicitly changed in a future decision.
- **Alternatives considered:** Immediate send; Slack notification instead of email.
- **Consequences:** Exit criteria for final phase verify `draft` exists, not `SENT` label.

---

### DEC-007: Lookback window (Phase 1)

- **Date:** 2026-06-02
- **Status:** accepted
- **Context:** Milestone requires 8–12 weeks of reviews; ingestion must define inclusive bounds and timezone behavior.
- **Decision:**
  - Default **10 weeks** lookback (`config/product.yaml`), configurable between 8 and 12.
  - **Inclusive** calendar dates in **UTC** (local date of export used as-is; no timezone conversion when export lacks offset).
  - `reference_date` defaults to today; window is `[reference_date - (weeks×7 - 1), reference_date]`.
- **Alternatives considered:** Rolling 24×7 hour windows; store-timezone per country column.
- **Consequences:** Reviews on boundary dates are included; document `reference_date` when reproducing demos.

---

### DEC-010: Phase 1 text quality filters (English, word count, emojis)

- **Date:** 2026-06-02
- **Status:** accepted
- **Context:** Downstream pulse needs substantive English quotes; Play corpus includes emoji-only noise, short spam, and Hindi/regional-language reviews.
- **Decision:**
  - Keep reviews with **more than 6 words** in body (`min_word_count: 6` → at least 7 words).
  - **Strip all emojis** from title and body (do not drop solely for emoji if text remains valid).
  - **English only:** drop reviews with non-Latin scripts (Devanagari, Tamil, etc.) or `langdetect` ≠ `en` when enough text.
- **Alternatives considered:** Keep all languages; drop emoji-containing reviews entirely.
- **Consequences:** Smaller normalized set; better quote quality for Groq stages; re-run ingest after rule change.

---

### DEC-009: Groww Play public review download (Phase 1)

- **Date:** 2026-06-02
- **Status:** accepted
- **Context:** Operator needs 8–12 weeks of Groww Google Play reviews; Play Console export may not be immediately available; public listing exposes reviews via “See all reviews.”
- **Decision:** Use `scripts/download_groww_play_reviews.py` with `google-play-scraper` against package `com.nextbillion.groww` (public listing data, no login). Paginate newest-first until older than lookback window; write Play-compatible CSV; ingest via Phase 1.
- **Alternatives considered:** Play Console CSV only; scraping authenticated console.
- **Consequences:** Volume is large (~10k raw / ~5k normalized per 12-week run); respect rate limits (`pause_seconds`); prefer Play Console export if course requires official export only.

---

### DEC-008: Export formats, dedupe, and column maps (Phase 1)

- **Date:** 2026-06-02
- **Status:** accepted
- **Context:** OQ-2 resolved at Phase 1 implementation.
- **Decision:**
  - **Formats:** CSV with UTF-8 (BOM tolerated) for App Store Connect–style and Google Play Console–style exports.
  - **Column maps:** Configurable alias lists in `config/product.yaml` (see `platforms.app_store.columns` / `play_store.columns`).
  - **Platform detection:** Filename hints (`app_store`, `play`, `google`) or header signatures; optional force via API.
  - **Dedupe:** (1) Same platform + same `review_date` + normalized body → one row. (2) Cross-platform same body within **1 calendar day** → keep earliest date.
  - **Dropped at ingest:** Username/reviewer columns never stored; rows with body shorter than 3 chars after strip.
  - **PII:** Redact emails, phones, `@handles`, URLs in title/body to `[redacted]` token.
- **Alternatives considered:** JSON exports; fuzzy dedupe with edit distance.
- **Consequences:** Teams with non-standard CSV headers extend `product.yaml` rather than patching parsers.

---

### DEC-006: Agent orchestration pattern (placeholder—confirm in Phase 5)

- **Date:** 2026-06-02
- **Status:** proposed
- **Context:** Need a single control plane for tool use and validation.
- **Decision (proposed):** Thin **orchestrator** (script or SDK agent) with deterministic pipeline steps for ingest/cluster/validate, and LLM for theme labeling + pulse prose within schema constraints.
- **Alternatives considered:** Fully autonomous single-shot prompt; pure batch ETL with no LLM.
- **Consequences:** Update to `accepted` after Phase 0 spike confirms MCP + runtime choice.

---

### DEC-011: Groq as LLM provider and model selection for Phase 2

- **Date:** 2026-06-04
- **Status:** accepted
- **Context:** OQ-3 — LLM provider and model for clustering (Stage A) and composition (Stage B) must be resolved before Phase 2 implementation begins. The architecture already calls for Groq; this decision pins the model, context window usage, and prompt strategy.
- **Decision:**
  - **Provider:** Groq (OpenAI-compatible HTTP API, `api.groq.com`). Auth via `GROQ_API_KEY` environment variable — never in repo.
  - **Model (both stages):** `llama-3.3-70b-versatile`. 128k-token context window; fast inference. Same model used for Stage A and Stage B to minimize provider surface.
  - **Token budget:** Stage A input targets ≤9K tokens (~190 reviews × 32 tokens + 600 system prompt). Stage B input targets ≤3K tokens (themes + evidence + system prompt). Total per run: ~9,820 tokens (happy path), comfortably under 12K TPM.
  - **Response format:** `response_format: { type: "json_object" }` enforced on both stages to reduce parse failures.
  - **Temperature:** `0.2` for Stage A (consistent theme extraction); `0.5` for Stage B (slightly more narrative variation).
  - **Retry policy:** Stage A — up to 2 retries with a stricter system prompt on JSON parse failure. Stage B — up to 2 retries with corrective instruction pointing at the specific violated rule (count, word limit, or provenance).
- **Alternatives considered:** GPT-4o (higher cost, not Groq); `mixtral-8x7b` (lower quality on structured JSON); separate models per stage (added complexity).
- **Consequences:** `GROQ_API_KEY` must be set in the runtime environment. Model name pinned here; update this entry if the model is changed.

---

### DEC-012: Stratified sampling strategy for Phase 2 (informed by Phase 1 data and Groq rate limits)

- **Date:** 2026-06-04
- **Status:** accepted
- **Context:** The Groww Play Store normalized dataset has **~1,880 reviews** across 13 weeks. Groq free-tier limits for `llama-3.3-70b-versatile` are: TPM 12K, TPD 100K, RPM 30, RPD 1K. Sending all reviews would consume ~60K tokens in Stage A alone — that's more than half the daily token budget in one call. Additionally, we want to build Phase 2 against a manageable 1,000-review working set.
- **Decision:**
  - **Step 1 — Pre-sample to 1,000 reviews:** draw proportionally by rating tier from the full normalized corpus. Same `seed` → same 1,000 reviews. Hard cap regardless of corpus size.
  - **Step 2 — Stratified sample from the 1,000:** bucket by rating tier (≤2★, 3★, 4–5★) × ISO week. Per-tier per-week caps: **negative ≤7/week, neutral ≤3/week, positive ≤5/week**. Target: **~190 reviews (~6,700 review tokens)**.
  - **Stage A total input:** ~6,700 (reviews) + ~600 (system prompt) = **~7,300 tokens** — stays under the 12K TPM limit with ~4,700 tokens headroom.
  - **Stage B total input:** ~2,300 tokens (themes + evidence + system prompt).
  - **Per-run total (happy path):** ~9,820 tokens → ~**9 full runs per day** within the 100K TPD limit.
  - **Retry budget:** Stage A retry costs ~7K tokens; Stage B retry costs ~2.6K tokens. With 2 Stage B retries worst case: ~14.5K total — still feasible across 2 minutes. Retries are rate-limit-aware: abort if TPD headroom < 3K.
  - **Fields sent to Groq (Stage A):** `review_id`, `rating`, `review_date`, `body` only. Title omitted (mostly empty in Groww Play data).
- **Alternatives considered:** Single-step stratified sample without pre-cap (harder to control TPD); send all 1,880 reviews (blows Stage A token budget).
- **Consequences:** `n=1000` and sampling caps are configurable in `config/product.yaml` under `sampling`; document if changed. Unit tests must mock Groq — live Stage A call alone costs ~7.3K tokens.

---

## Open Questions

| ID | Question | Owner | Target phase |
|----|----------|-------|--------------|
| OQ-1 | Which MCP servers/connectors for Docs and Gmail in our environment? | Team | Phase 0 |
| OQ-2 | Exact export column mapping for App Store vs Play Store? | Team | ~~Phase 1~~ → DEC-008 |
| OQ-3 | LLM provider and model for clustering vs composition? | Team | ~~Phase 2~~ → DEC-011 |
