# PRD: Supply Chain Signal Extractor — Earnings Call Ingestion Pipeline

## Problem Statement

Public company earnings call transcripts contain rich, forward-looking intelligence about supply chain dynamics: price movements, supply disruptions, demand shifts, capacity changes, contract renegotiations, and outlook uncertainty. Currently, this information is either ignored or captured ad-hoc by human analysts reading transcripts one at a time.

The existing Stage 1 Knowledge Graph ("Dependency Backbone") models static supply chain structure — who supplies whom, who produces what, what materials go into what products. It deliberately excludes transient state changes like price hikes or disruptions (per ADR-005). But those transient signals are exactly what downstream Event Impact projects need as input.

There is no automated pipeline that:
- Ingests earnings call transcripts and extracts both structural relationships (which can enrich the graph) and state signals (which inform future event analysis)
- Keeps these two outputs cleanly separated so the graph model is not polluted
- Preserves evidence, temporal scope, and confidence metadata for downstream consumers

Additionally, the current design document references processing "thousands" of transcripts at scale, which is aspirational. The initial scope is processing batches of 10s to 100s of transcripts per quarter, with transcript acquisition and format normalization handled outside the pipeline.

---

## Solution

Build a **dual-stream LLM extraction pipeline** that processes earnings call transcripts in a single inference pass and outputs two independent, non-overlapping structured datasets:

1. **Relation Stream**: `[:PROVIDES]`, `[:SUPPLIES_TO]` (new/terminated), and candidate `[:USED_IN]` edges. These are validated against Stage 1 constraints where possible and routed to a human review queue for curation. Graph injection is deferred until entity linking and the Stage 1 Knowledge Graph are available.

2. **Signal Stream**: 10 types of supply chain state signals (price changes, disruptions, demand shifts, capacity events, contract modifications, uncertainty declarations). These are stored in a partitioned JSONL signal library. Evidence quality tiers (`explicit`, `implicit`, `vague`) are enforced: explicit and implicit signals enter the production library; vague signals are stored in a separate audit log.

A single LLM call extracts both streams simultaneously, reducing inference cost and ensuring both streams share the same entity recognition context.

---

## User Stories

### Graph Curator / Data Steward

1. As a graph curator, I want new `[:SUPPLIES_TO]` relationships extracted from earnings calls to be suggested for my review, so I can expand the dependency backbone without manually reading every transcript.

2. As a graph curator, I want the extracted relationships to carry `confidence` scores and `source` attribution back to the exact transcript sentence, so I can audit and verify claims before they enter the graph.

3. As a graph curator, I want newly discovered companies or products that aren't yet in the graph to be flagged for manual review rather than silently dropped, so I can decide whether to expand the graph's scope.

4. As a graph curator, I want the pipeline to reject any relationship that violates Stage 1 constraints (self-loops, missing confidence, physical-composition confusion), so I do not have to clean up bad data later.

### Event Impact Analyst / Downstream Consumer

5. As an event analyst, I want all price-related statements (cost increases, price hikes to customers, market price shifts) extracted with direction and magnitude, so I can track cost pressure propagation through supply chains.

6. As an event analyst, I want supply disruption signals (production outages, supplier curtailments, logistics breakdowns) extracted as structured events with temporal scope, so I can model shock propagation scenarios.

7. As an event analyst, I want demand shift signals (increase or decrease for specific products) captured with the affected entities, so I can assess second-order effects on upstream suppliers.

8. As an event analyst, I want capacity expansion and contraction signals tracked over time, so I can anticipate supply-demand imbalances before they materialize in prices.

9. As an event analyst, I want contract modifications (strengthening, weakening, or neutral changes) captured separately from new or terminated relationships, so I can track relationship quality degradation that might precede full termination.

10. As an event analyst, I want management statements about outlook uncertainty captured even when no direction is given, so I can flag nodes in the supply chain where forecasting is unreliable.

11. As an event analyst, I want explicit and implicit signals stored in the production library while vague signals are isolated, so I can trust that production data has passed a quality threshold.

### Pipeline Operator

12. As a pipeline operator, I want a single LLM call to produce both relations and signals, so I minimize API costs when processing batches of transcripts.

13. As a pipeline operator, I want signals that are too vague to be useful to be isolated in a separate audit log rather than silently discarded, so I can monitor extraction quality patterns over time.

14. As a pipeline operator, I want each signal and relation to carry a unique, traceable ID and source attribution, so I can debug extraction quality issues.

15. As a pipeline operator, I want malformed LLM responses to be retried with a repair prompt and logged if all retries fail, so no transcript is silently dropped.

16. As a pipeline operator, I want the pipeline to accept structured canonical JSON input, so transcript format normalization can be performed upstream by a separate system.

17. As a pipeline operator, I want the pipeline to process transcripts sequentially with clear logging, so I can monitor progress and diagnose failures without concurrency overhead.

18. As a pipeline operator, I want a `--dry-run` mode that shows extraction results without writing to storage, so I can validate changes quickly.

### System Builder / Future Project Owner

19. As the Event Impact project owner, I want signals stored in a well-typed, versioned schema independent of the graph, so I can consume them without coupling to Neo4j or the Stage 1 data model.

20. As the Event Impact project owner, I want signals referencing entities that do not yet exist in the graph to be preserved with `match_status: unmatched`, so I can retroactively link them after the graph expands.

21. As a developer, I want a standalone synthetic transcript generator with embedded ground truth, so I can validate extraction accuracy even without access to real transcripts.

---

## Implementation Decisions

### Architecture: Dual-Stream, Single LLM Call

Use a single LLM API call that returns a JSON object with two top-level arrays: `"relations": [...]` and `"signals": [...]`. Earnings call transcripts are thousands of tokens; reading them twice doubles cost. Entity recognition and supply-chain context understanding are shared workloads. A single well-designed system prompt with clear boundary rules achieves clean separation at lower cost.

### Language and Framework

Python. Dependencies managed via `requirements.txt` (google-generativeai, pydantic>=2.0, pytest, python-dotenv). The sibling `knowledge_graph` project uses an identical pattern.

### LLM Provider

Google Gemini 2.5 Flash (free tier, 1,500 requests/day, 1M token context window). Uses the `google.genai` SDK. A JSON repair loop handles non-conforming responses by re-prompting with a repair instruction. Hardcoded defaults: temperature=0, max_retries=3.

### Transcript Input Contract

Transcript acquisition and format normalization are out of scope. The pipeline accepts a canonical JSON format with `transcript_id`, `company_name`, `company_ticker`, `quarter`, `call_date`, and `sections` (each with `section_type`, `speakers`, `text`). This defines a clear contract that upstream providers must satisfy.

### Chunking

No chunking for individual transcripts. Gemini 2.5 Flash's 1M token context window accommodates even the longest earnings call, and the entire transcript plus system prompt fits well within the model's effective "smart zone." Room is left in the architecture for future chunking if needed.

### Entity Linking

Skipped entirely for the initial MVP. All entities are assigned `match_status: unmatched`. Entity linking will be implemented as a future module that resolves names against the Stage 1 Knowledge Graph.

### Relation Validation (No Graph)

Without the Stage 1 Knowledge Graph, relation validation performs only two checks: self-loop rejection (subject_entity == object_entity) and confidence presence (confidence field is not null). All other validation (entity type constraints, dedup against existing edges) is deferred. All relations are routed to the review queue.

### Module Decomposition

**Deep modules** (encapsulating significant logic behind simple, stable interfaces):

1. **Pipeline** — End-to-end processing module. Encapsulates the full flow: build prompt → extract → validate IDs → signal validate → relation validate → boundary overlap detect → collect review entries. Exposes a single `run(transcript, quarter)` interface. Accepts an injectable LLM adapter, making the orchestration logic testable without real API calls. Returns a `PipelineResult` with extraction, production signals, vague signals, and review entries. The CLI, upstream transcript project, and downstream knowledge graph project all reuse this interface.

2. **Prompt Builder** — Composable prompt factory. Takes individual components (system role, signal type definitions, boundary rules, few-shot examples, output format instructions) and assembles them into the final system prompt. Each component is independently testable and maintainable. Also provides a `default_pipeline_prompt()` that the Pipeline uses.

3. **Signal Validator** — Enforces the 10-type discriminated union schema and evidence quality tiers. Routes `explicit` and `implicit` signals to the production JSONL (`signals_{Q}.jsonl`) and `vague` signals to the audit log (`vague_{Q}.jsonl`).

4. **Review Collector** — Accepts flagged items from validators and produces standardized `ReviewEntry` envelopes. Delegates `review_id` construction to the IDs module. Validators flag; the collector wraps.

5. **IDs** — Owns the composite key format contract. Provides `is_valid_signal_id()`, `is_valid_relation_id()` (regex validation against `{transcript_id}--{stream}--{index:04d}`), and `make_review_id()`. Used by the Pipeline for post-extraction ID validation (warns on malformatted IDs without rejecting) and by the Review Collector for review ID generation.

6. **Writer** — Quarter-partitioned JSONL writer. Manages file handles per quarter, handles multi-quarter batches seamlessly by routing each transcript's output to the correct file.

**Seam modules** (intentionally thin — they define contracts with upstream/downstream projects):

7. **Transcript Preprocessor** — Validates canonical JSON input against the `TranscriptInput` schema, strips `_ground_truth` metadata if present, extracts quarter for partitioning. This is the input seam with the upstream transcript acquisition project.

8. **Relation Validator** — Self-loop rejection, confidence presence, review trigger checks. Thin because full graph validation awaits entity linking in the downstream knowledge graph project. Delegates review entry construction to the Review Collector.

**Cross-cutting:**

9. **LLM Extractor** — Wraps the Gemini API call with composable prompt, exponential backoff retry (3 attempts), malformed JSON repair (1 attempt with repair prompt), and failure logging to `failed_extractions.jsonl`. Serves as the injectable adapter behind the Pipeline's LLM seam.

10. **Boundary Overlap Detector** — Post-hoc excerpt comparison between the relation and signal streams. Flags violations of boundary rule 5 as review entries (via the Review Collector).

11. **CLI** — Entry point (`run_pipeline.py` delegates to `cli.main`) with subcommands: `process` (batch directory), `process-one` (single transcript with optional `--dry-run`). Delegates processing to the Pipeline module, handling only argument parsing, output writing, and progress reporting.

### Boundary Rules Between Relation Stream and Signal Stream

Six hard rules govern what enters each stream:

| # | Rule | Stream |
|---|------|--------|
| 1 | Structural facts about who supplies whom, who produces what -> stable relationships | Relations |
| 2 | Explicit relationship establishment ("we started supplying X") or termination ("lost Y as a customer") -> with valid_from/valid_until | Relations |
| 3 | Physical material-to-product composition ("we use corn starch to produce ethanol") -> [:USED_IN], only when explicitly stated | Relations |
| 4 | State changes: prices, output status, supply status, logistics, demand, capacity -> regardless of entities involved | Signals |
| 5 | A single source sentence must not appear in both streams; split if necessary | Both (non-overlapping) |
| 6 | Entity-anchored uncertainty about future direction -> outlook_uncertainty signal | Signals |

Rule 5 is enforced at two levels: prompt instruction (preventative) and post-hoc excerpt comparison (detective). Violations are routed to the review queue with `review_reason: boundary_overlap`.

### Signal Type Taxonomy (10 Types)

Defined as a Pydantic discriminated union (`Annotated[Union[...], Field(discriminator="signal_type")]`). Each type has its own `direction` enum narrowed to valid values:

| Signal Type | Allowed `direction` Values |
|-------------|---------------------------|
| `cost_change` | `increase`, `decrease`, `volatile` |
| `price_adjustment` | `increase`, `decrease`, `volatile` |
| `market_price_shift` | `increase`, `decrease`, `volatile` |
| `production_status_change` | `disruption`, `recovery`, `increase`, `decrease`, `volatile` |
| `supply_status_change` | `disruption`, `recovery` |
| `logistics_status_change` | `disruption`, `recovery` |
| `capacity_expansion` | `expansion`, `contraction` |
| `demand_shift` | `increase`, `decrease` |
| `contract_modification` | `strengthen`, `weaken`, `modify` |
| `outlook_uncertainty` | `null` (Literal[None]) |

When `direction` is `volatile`, an optional `volatility_intensity` field (`low`, `moderate`, `high`) is populated.

### Evidence Quality (3 Tiers)

| Tier | Criteria | Storage |
|------|----------|---------|
| `explicit` | Clear direction + specific dimension + (numeric value OR explicit entity). No inference needed. | Production signal library |
| `implicit` | Direction or object requires one logical step of inference, but inference reliability is high given context. | Production signal library |
| `vague` | Too generic to reliably determine direction or object, even with context. Multiple interpretations possible. | Vague audit log (`vague_{Q}.jsonl`) |

Exception: `outlook_uncertainty` signals are not subject to this filter.

### Temporal Structure

Each signal carries a `temporal` object with `granularity` (enum: `exact_date`, `quarter`, `half`, `year`, `relative`, `ongoing`, `forward_looking`), optional `start`/`end` ISO dates, and optional `duration` (value + unit).

### ID Generation

Composite key format: `{transcript_id}--{stream}--{index:04d}`. Examples: `AAPL-2025Q1--signal--0001`, `AAPL-2025Q1--relation--0003`. Indices are assigned sequentially per transcript.

### Output Storage Structure

```
data/
  signal_library/
    signals_2025Q1.jsonl        # explicit + implicit signals
    vague_2025Q1.jsonl          # vague signals (audit trail)
  review_queue/
    review_2025Q1.jsonl         # flagged items for human curation
  failures/
    failed_extractions.jsonl    # transcripts that could not be processed (append-only)
```

### Configuration

Gemini API key loaded from `.env` file via `python-dotenv`. Hardcoded defaults for `model="gemini-2.5-flash"`, `temperature=0`, `max_retries=3`. CLI flags override defaults for experimentation.

### Error Handling

Single `extract_with_retry()` function wraps the Gemini API call:
- Transient/rate-limit errors: exponential backoff, 3 attempts max
- Malformed JSON: one retry with repair prompt appended  
- Content filter blocks: log and skip (rare for financial text)
- Final failures: write to `failed_extractions.jsonl` with transcript_id and error detail

### Review Queue Entry Format

Standardized `ReviewEntry` envelope with fields: `review_id`, `transcript_id`, `review_reason` (unmatched_entity, low_confidence, boundary_overlap, candidate_used_in, validation_failure), `entry_type` (signal or relation), `payload` (the original extracted item), `review_status` (pending/approved/rejected), `reviewer_notes`, and `flagged_at`.

---

## Testing Decisions

### What Makes a Good Test

Tests should validate external behavior of each module, not internal prompt engineering details:
- Given a transcript with known supply chain statements, does the pipeline produce expected signal types with correct direction and entities?
- Given a relation output, does it pass validation constraints?
- Given an unmatched entity, does it appear in the review queue with the original name preserved?
- Does the signal filter correctly route vague signals to the audit log while retaining explicit and implicit signals?

### Modules to Test

| Module | Test Focus |
|--------|-----------|
| Schemas | Pydantic model construction, serialization, enum constraints, discriminated union dispatch, OutlookUncertainty null direction |
| LLM Extractor | Given transcript -> produces valid ExtractionResult, signal types match ground truth |
| Signal Validator | Schema conformance, vague vs explicit routing, volatility_intensity conditional rule |
| Relation Validator | Self-loop rejection, confidence presence, boundary rule 5 overlap detection |
| Integration (real API) | End-to-end extraction against synthetic golden transcripts, guarded by pytest marker (`--run-integration`) |

### Test Data Strategy

A set of 12 synthetic transcripts with embedded `_ground_truth` fields. Generated via Gemini 2.5 Flash and manually verified to ensure correctness. Coverage includes all 10 signal types, all 6 boundary rules, edge cases (direction: volatile with intensity, direction: null, clean transcript with no signals, ambiguous entity names). Generated by a standalone `generate_synthetic.py` script.

### Prior Art

The schemas.py file already defines the Pydantic models. The `database` sibling project demonstrates the test layout pattern (`tests/conftest.py` with shared fixtures, `test_*.py` files per module).

---

## Out of Scope

- **Real transcript acquisition and format normalization**: These are handled upstream. The pipeline accepts a canonical JSON input format.
- **Event Impact analysis and propagation logic**: Owned by the downstream Event project. The signal library provides input; it does not perform impact computation.
- **Real-time streaming**: Initial implementation processes transcripts in batch mode (sequential, per quarter). Streaming ingestion is a future optimization.
- **Entity linking against the Stage 1 Knowledge Graph**: Skipped for MVP. All entities are unmatched.
- **Graph injection (Neo4j writes)**: Deferred until entity linking and graph access are available. Relations are routed to human review.
- **Substitute product analysis and product categories**: Owned by the Process project (ADR-007).
- **Precise financial quantification**: The pipeline captures `magnitude` as a text snippet from the source. It does not normalize units, perform currency conversion, or disambiguate percentages.
- **Inventory level signals, regulatory risk signals, alternative sourcing strategy signals, weather/seasonal signals**: Excluded from the initial signal taxonomy. May be added via a future ADR amendment.
- **Automated node creation in the graph**: Unmatched entities go to the review queue. The pipeline does not auto-create Company or Product nodes without human approval.
- **Modification of the Stage 1 data model**: No new relationship types or entity types are introduced. The graph schema remains unchanged.
- **Concurrent processing**: Sequential processing only. Concurrent processing can be added when the paid tier is used.
- **Resumable batch processing**: Not implemented in MVP. Re-running a batch overwrites output files.
- **Web UI or database-backed review interface**: The review queue is JSONL, curated manually in a text editor or spreadsheet.

---

## Further Notes

### Integration With Stage 1 Knowledge Graph

The pipeline reads from the graph only through the entity linking module (which is skipped for MVP). It writes validated relations via the same CSV format and LOAD CSV pipeline used in Stage 1 (deferred until linking is available). Signal output is stored independently and does not interact with Neo4j.

### Architecture Decision Record

This PRD is accompanied by ADR-008: Dual-Stream Extraction and Independent Signal Storage, which captures the core architectural tradeoff: transient state signals must not pollute the static dependency backbone, but they are too valuable to discard. The signal library is the bridge to the Event project.

### Synthetic Transcript Generator

A standalone script (`generate_synthetic.py`) that uses Gemini 2.5 Flash to create synthetic earnings call transcripts with known ground-truth signals and relations embedded. Populates `data/synthetic_transcripts/` with one file per transcript. The `_ground_truth` field is stripped by the pipeline before processing and used by tests for accuracy comparison.

### Prompt Strategy

The LLM system prompt is built composeably from:
- System role definition
- Clear definitions of all 10 signal types with direction enumerations
- The 6 boundary rules
- 3-5 few-shot examples covering the trickiest cases (boundary splitting, volatile with intensity, outlook uncertainty with null direction)
- Explicit instruction to output valid JSON with both `relations` and `signals` arrays
- Instruction to never auto-assign `confirmed` confidence

Few-shot examples are drawn from the synthetic test set. Simpler signal types (demand_shift, cost_change) work zero-shot.

### Glossary Alignment

All terms in the signal schema (`subject_entity`, `object_entity`, `direction`, `evidence_quality`, `temporal`, `match_status`) are defined in the project glossary and consistent with Stage 1 terminology where overlap exists (Company, Product, Commodity).
