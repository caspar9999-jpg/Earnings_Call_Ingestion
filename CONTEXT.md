# Domain Context — Earnings Call Ingestion

## Transcript

- **Transcript** — Canonical JSON input representing one earnings call. Fields: `transcript_id`, `company_name`, `company_ticker`, `quarter`, `call_date`, `sections`. Defined as `TranscriptInput` (Pydantic model). Acquisition and format normalization are handled upstream.
- **Section** — A portion of a transcript: either `prepared_remarks` (management script) or `q_and_a` (analyst exchange). Contains `speakers` and `text`.
- **Speaker** — A person speaking in a section, with `name` and `role` (ceo, cfo, coo, analyst, executive, operator, other).

## Entity

- **Entity** — A company, product, commodity, service, or division referenced in a transcript. Has `name` and `type` (EntityType). All entities are assigned `match_status: unmatched` in MVP (entity linking against the knowledge graph is deferred).

## Extraction

- **Extraction** — The LLM's raw output from a single transcript: an `ExtractionResult` containing `relations` and `signals` arrays. One LLM call produces both streams (dual-stream architecture).
- **LLM Extractor** — Adapter wrapping the Gemini API call. Handles exponential backoff retry (3 attempts), malformed JSON repair (1 repair prompt), and extraction failure logging.

## Relation Stream

- **Relation** — A structural supply chain link between two entities. Three types: `:PROVIDES` (produces/makes), `:SUPPLIES_TO` (sells to), `:USED_IN` (material-to-product composition). Carries `llm_confidence`, `evidence_quality`, `temporal` scope, `source` attribution, and optional `valid_from`/`valid_until` dates.
- **Relation Confidence** — LLM-assigned certainty: `explicit`, `implicit`, `speculative`. `confirmed` requires human review and is never auto-assigned.
- **Self-loop** — A relation where subject and object are the same entity. Always invalid.
- **Relation Validator** — Enforces self-loop rejection and confidence presence. Flags unmatched entities, speculative confidence, and `:USED_IN` candidates for review. Full validation awaits entity linking and the downstream knowledge graph.

## Signal Stream

- **Signal** — A transient supply chain state change. Ten types, discriminated union keyed on `signal_type`. Each has its own `direction` enum.
- **Signal Type Taxonomy**:

  | Type | Direction Values |
  |------|-----------------|
  | `cost_change` | increase, decrease, volatile |
  | `price_adjustment` | increase, decrease, volatile |
  | `market_price_shift` | increase, decrease, volatile |
  | `production_status_change` | disruption, recovery, increase, decrease, volatile |
  | `supply_status_change` | disruption, recovery |
  | `logistics_status_change` | disruption, recovery |
  | `capacity_expansion` | expansion, contraction |
  | `demand_shift` | increase, decrease |
  | `contract_modification` | strengthen, weaken, modify |
  | `outlook_uncertainty` | null (always) |

- **Direction** — The direction of change, narrowed per signal type. When `volatile`, an optional `volatility_intensity` (low, moderate, high) is populated.
- **Signal Validator** — Routes signals by evidence quality: explicit + implicit → production library; vague → audit log. `outlook_uncertainty` is exempt and always goes to production.

## Evidence & Quality

- **Evidence Quality** — Three tiers: `explicit` (clear direction, no inference needed), `implicit` (one logical step of inference), `vague` (too generic, multiple interpretations).
- **Match Status** — Whether an entity exists in the downstream knowledge graph: `matched`, `unmatched`, `not_applicable`. Always `unmatched` in MVP.
- **Source Reference** — Attribution to the exact transcript section, speaker, and verbatim excerpt that produced a signal or relation.

## Boundary Rules

Six rules separating the relation stream from the signal stream:

1. Structural facts (who supplies whom, who produces what) → Relations
2. Relationship establishment/termination → Relations with `valid_from`/`valid_until`
3. Physical material-to-product composition → Relations (`:USED_IN`), only when explicit
4. State changes (prices, output, supply, logistics, demand, capacity) → Signals
5. One source sentence must not appear in both streams; split if necessary
6. Entity-anchored uncertainty about future direction → `outlook_uncertainty` signal

Rule 5 is enforced at the prompt level (preventative) and post-hoc by the **Boundary Overlap Detector**.

## Review Queue

- **Review Entry** — A flagged item requiring human review. Reasons: `unmatched_entity`, `low_confidence`, `boundary_overlap`, `candidate_used_in`, `validation_failure`. Statuses: `pending`, `approved`, `rejected`. Standardized envelope with `review_id`, `transcript_id`, `payload`, and `flagged_at`.
- **Review Collector** — Module that accepts flagged items from validators and produces standardized `ReviewEntry` envelopes. Owns the `review_id` format and construct logic.

## Pipeline

- **Pipeline** — The end-to-end processing module. Encapsulates the full flow: build prompt → LLM extract → ID validation → signal validate → relation validate → boundary overlap detect → collect review entries. Exposes a single `run(transcript, quarter)` interface. Accepts an injectable LLM adapter for testing.
- **Pipeline Result** — Structured output from one Pipeline run: `extraction` (raw `ExtractionResult`), `production_signals`, `vague_signals`, `review_entries`.
- **ID Validation** — After extraction, the Pipeline validates every `signal_id` and `relation_id` against the composite key format. Malformatted IDs are logged as warnings (non-fatal) so operators can detect LLM drift without rejecting valid data.

## Writer

- **Writer** — Quarter-partitioned JSONL storage. Outputs three file types per quarter: `signal_library/signals_{Q}.jsonl` (explicit + implicit), `signal_library/vague_{Q}.jsonl` (vague), `review_queue/review_{Q}.jsonl` (review entries). Manages file handles across a batch.

## Temporal

- **Temporal** — Time scope of a signal or relation. Fields: `granularity` (exact_date, quarter, half, year, relative, ongoing, forward_looking), optional `start`/`end` ISO dates, optional `duration` (value + unit).

## IDs

- **IDs module** — Owns the composite key format contract. Provides `is_valid_signal_id()`, `is_valid_relation_id()` (regex validation against `{transcript_id}--{stream}--{index:04d}`), and `make_review_id()` (centralized `{parent_id}--{reason}` construction). Used by the Pipeline for validation and by the Review Collector for generation.
- **Composite Key Format** — `{transcript_id}--{stream}--{index:04d}`. Assigned by the LLM for signals and relations. Examples: `AAPL-2025Q1--signal--0001`, `AAPL-2025Q1--relation--0003`.
- **Review ID Format** — `{parent_id}--{reason}`. Built by `ids.make_review_id()`. Examples: `AAPL-2025Q1--relation--0001--validation_failure`, `AAPL-2025Q1--signal--0002--boundary_overlap`.
