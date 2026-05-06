---

# PRD: Supply Chain Signal Extractor — Earnings Call Ingestion Pipeline

---

## Problem Statement

Public company earnings call transcripts contain rich, forward-looking intelligence about supply chain dynamics: price movements, supply disruptions, demand shifts, capacity changes, contract renegotiations, and outlook uncertainty. Currently, this information is either ignored or captured ad-hoc by human analysts reading transcripts one at a time. 

The existing Stage 1 Knowledge Graph ("Dependency Backbone") models static supply chain structure — who supplies whom, who produces what, what materials go into what products. It deliberately excludes transient state changes like price hikes or disruptions (per ADR-005). But those transient signals are exactly what downstream Event Impact projects need as input.

There is no automated pipeline that:
- Ingest earnings call transcripts at scale
- Extracts both **structural relationships** (which can enrich the graph) and **state signals** (which inform future event analysis)
- Keeps these two outputs cleanly separated so the graph model isn't polluted
- Preserves evidence, temporal scope, and confidence metadata for downstream consumers

---

## Solution

Build a **dual-stream LLM extraction pipeline** that processes earnings call transcripts in a single inference pass and outputs two independent, non-overlapping structured datasets:

1. **Relation Stream**: `[:PROVIDES]`, `[:SUPPLIES_TO]` (new/terminated), and candidate `[:USED_IN]` edges. These are validated against Stage 1 constraints and injected directly into the Neo4j knowledge graph.

2. **Signal Stream**: 10 types of supply chain state signals (price changes, disruptions, demand shifts, capacity events, contract modifications, uncertainty declarations). These are stored in an independent signal library (JSONL) for future consumption by the Event Impact project. Signals link to graph entities but do not write to the graph.

A single LLM call extracts both streams simultaneously, reducing inference cost and ensuring both streams share the same entity recognition context.

---

## User Stories

### Graph Curator / Data Steward

1. As a graph curator, I want new `[:SUPPLIES_TO]` relationships extracted from earnings calls to be suggested for my review, so I can expand the dependency backbone without manually reading every transcript.

2. As a graph curator, I want the extracted relationships to carry `confidence` scores and `source` attribution back to the exact transcript sentence, so I can audit and verify claims before they enter the graph.

3. As a graph curator, I want newly discovered companies or products that aren't yet in the graph to be flagged for manual review rather than silently dropped, so I can decide whether to expand the graph's scope.

4. As a graph curator, I want the pipeline to reject any relationship that violates Stage 1 constraints (self-loops, missing confidence, physical-composition confusion), so I don't have to clean up bad data later.

### Event Impact Analyst / Downstream Consumer

5. As an event analyst, I want all price-related statements (cost increases, price hikes to customers, market price shifts) extracted with direction and magnitude, so I can track cost pressure propagation through supply chains.

6. As an event analyst, I want supply disruption signals (production outages, supplier curtailments, logistics breakdowns) extracted as structured events with temporal scope, so I can model shock propagation scenarios.

7. As an event analyst, I want demand shift signals (increase or decrease for specific products) captured with the affected entities, so I can assess second-order effects on upstream suppliers.

8. As an event analyst, I want capacity expansion and contraction signals tracked over time, so I can anticipate supply-demand imbalances before they materialize in prices.

9. As an event analyst, I want contract modifications (strengthening, weakening, or neutral changes) captured separately from new or terminated relationships, so I can track relationship quality degradation that might precede full termination.

10. As an event analyst, I want management statements about outlook uncertainty captured even when no direction is given, so I can flag nodes in the supply chain where forecasting is unreliable.

### Pipeline Operator

11. As a pipeline operator, I want a single LLM call to produce both relations and signals, so I minimize API costs when processing thousands of transcripts.

12. As a pipeline operator, I want signals that are too vague to be useful to be automatically filtered out of the production library, so downstream consumers don't drown in noise.

13. As a pipeline operator, I want each signal and relation to carry a unique ID and traceable transcript source, so I can debug extraction quality issues.

### System Builder / Future Project Owner

14. As the Event Impact project owner, I want signals stored in a well-typed, versioned schema independent of the graph, so I can consume them without coupling to Neo4j or the Stage 1 data model.

15. As the Event Impact project owner, I want signals referencing entities that don't yet exist in the graph to be preserved with `match_status: unmatched`, so I can retroactively link them after the graph expands.

---

## Implementation Decisions

### Architecture: Dual-Stream, Single LLM Call

**Decision**: Use a single LLM API call that returns a JSON object with two top-level arrays: `"relations": [...]` and `"signals": [...]`. (Option A from design discussion.)

**Rationale**: Earnings call transcripts are thousands of tokens; reading them twice doubles cost. Entity recognition and supply-chain context understanding are shared workloads. A single well-designed system prompt with clear boundary rules achieves clean separation at lower cost.

### Boundary Rules Between Relation Stream and Signal Stream

Six hard rules govern what enters each stream:

| # | Rule | Stream |
|---|------|--------|
| 1 | Structural facts about who supplies whom, who produces what → stable relationships | Relations |
| 2 | Explicit relationship establishment ("we started supplying X") or termination ("lost Y as a customer") → with `valid_from`/`valid_until` | Relations |
| 3 | Physical material-to-product composition ("we use corn starch to produce ethanol") → `[:USED_IN]`, only when explicitly stated | Relations |
| 4 | State changes: prices, output status, supply status, logistics, demand, capacity → regardless of entities involved | Signals |
| 5 | A single source sentence must not appear in both streams; split if necessary | Both (non-overlapping) |
| 6 | Entity-anchored uncertainty about future direction → `outlook_uncertainty` signal | Signals |

### Signal Type Taxonomy (10 Types)

| Signal Type | Description | Allowed `direction` Values |
|-------------|-------------|---------------------------|
| `cost_change` | Company's own input/material cost change | `increase`, `decrease`, `volatile` |
| `price_adjustment` | Company adjusts prices charged to customers | `increase`, `decrease`, `volatile` |
| `market_price_shift` | Benchmark/index market price movement | `increase`, `decrease`, `volatile` |
| `production_status_change` | Company's own output or production status | `disruption`, `recovery`, `increase`, `decrease`, `volatile` |
| `supply_status_change` | External supplier delivery status | `disruption`, `recovery` |
| `logistics_status_change` | Transportation/logistics channel status | `disruption`, `recovery` |
| `capacity_expansion` | Production capacity change | `expansion`, `contraction` |
| `demand_shift` | Downstream demand change | `increase`, `decrease` |
| `contract_modification` | Contract terms change (not new/terminated) | `strengthen`, `weaken`, `modify` |
| `outlook_uncertainty` | Management expresses inability to forecast | `null` |

When `direction` is `volatile`, an optional `volatility_intensity` field is populated with `low`, `moderate`, or `high`.

### Evidence Quality (3 Tiers)

| Tier | Name | Criteria | Storage |
|------|------|----------|---------|
| `explicit` | Clear direction + specific dimension + (numeric value OR explicit entity). No inference needed. | Production signal library |
| `implicit` | Direction or object requires one logical step of inference, but inference reliability is high given context. | Production signal library (marked) |
| `vague` | Too generic to reliably determine direction or object, even with context. Multiple interpretations possible. | Discarded (or noise log) |

Exception: `outlook_uncertainty` signals are not subject to this filter — they are structural expressions of unpredictability, not vague sentiment.

### Temporal Structure

Each signal carries a `temporal` object:

| Field | Required | Description |
|-------|----------|-------------|
| `granularity` | Yes | Enum: `exact_date`, `quarter`, `half`, `year`, `relative`, `ongoing`, `forward_looking` |
| `start` | No | ISO date, normalized to period start when possible |
| `end` | No | ISO date, null if unknown or ongoing |
| `duration` | No | Object `{ value: number, unit: day/week/month/quarter/year }`, only when the source sentence explicitly states a duration |

LLM extracts explicit temporal expressions from the text. Post-processing fills defaults from transcript metadata (e.g., quarter boundaries).

### Entity Linking & Match Status

The same entity linking engine normalizes company/product names for both streams. Unmatched entities are **retained** in the signal stream with `match_status: unmatched` and the original name preserved. They are **flagged for review** in the relation stream (for potential new node creation).

| Field | Possible Values |
|-------|----------------|
| `match_status_subject` | `matched`, `unmatched` |
| `match_status_object` | `matched`, `unmatched`, `not_applicable` (when no object) |

### Relation Stream Confidence Mapping

Following Stage 1 ADR-003:
- LLM output `explicit` → graph `confidence: inferred` 
- LLM output `implicit` → graph `confidence: associated`
- LLM output `speculative` → discarded or routed to review queue
- `confirmed` is **never** auto-assigned by LLM; it requires human verification of exclusive/documented dependency

### Module Decomposition

1. **Transcript Preprocessing Module**: Chunking, speaker identification stripping, quarter metadata extraction.
2. **LLM Extraction Module**: Single-call dual-output extraction with structured JSON response. Encapsulates the full system prompt with boundary rules and few-shot examples.
3. **Entity Linking Module**: Name normalization, alias dictionary lookup, embedding-based fuzzy matching against existing graph nodes. Shared by both streams.
4. **Relation Validation & Injection Module**: Runs Stage 1 constraint checks (no self-loops, confidence required, provide-to-company linkage), deduplicates against existing edges, generates incremental CSV or direct Cypher MERGE statements.
5. **Signal Validation & Storage Module**: Enforces signal JSON schema, filters `vague` signals, writes validated signals to JSONL library partitioned by quarter.
6. **Review Queue Module**: Collects unmatched entities, candidate `[:USED_IN]` edges, and low-confidence relations for human curation.

### Schema: Signal Output Contract

Defined in JSON Schema (Draft-07). Required fields: `signal_id`, `transcript_id`, `signal_type`, `direction`, `subject_entity`, `subject_type`, `statement`, `evidence_quality`, `temporal`, `source`. Full schema provided in design discussion.

---

## Testing Decisions

### What Makes a Good Test

Tests should validate **external behavior** of each module, not internal prompt engineering details:
- Given a transcript with known supply chain statements, does the pipeline produce expected signal types with correct direction and entities?
- Given a relation output, does it pass all Stage 1 validation constraints?
- Given an unmatched entity, does it appear in the review queue with the original name preserved?
- Does the signal filter correctly discard `vague` signals while retaining `explicit` and `implicit` ones?

### Modules to Test

| Module | Test Focus |
|--------|-----------|
| Entity Linking | Fuzzy matching accuracy on known aliases; correct `match_status` assignment for novel entities |
| Relation Validation | Rejection of self-loops, missing confidence, provider-not-company errors |
| Signal Validation | Schema conformance, correct `vague` filtering, `volatility_intensity` only present when `direction=volatile` |
| Boundary Rules | Same source sentence not in both streams; contract establishment → relations, not `contract_modification` |

### Prior Art

The Stage 1 project includes `validation.cypher` queries and a `constraints.cypher` file. Relation stream validation reuses those same Cypher constraints. The 5 verification queries from Stage 1 serve as integration tests for the enriched graph.

### Test Data Strategy

Curate a small set of ~10 anonymized transcript excerpts with known ground-truth relations and signals. Use these as a golden test set for regression testing across prompt iterations.

---

## Out of Scope

- **Event Impact analysis and propagation logic**: This is owned by the downstream Event project. The signal library provides input; it does not perform impact computation.
- **Real-time streaming**: Initial implementation processes transcripts in batch (per quarter). Streaming ingestion is a future optimization.
- **Substitute product analysis and product categories**: Owned by the Process project (ADR-007).
- **Precise financial quantification**: The pipeline captures `magnitude` as a text snippet from the source. It does not normalize units, perform currency conversion, or disambiguate percentages.
- **Inventory level signals, regulatory risk signals, alternative sourcing strategy signals, weather/seasonal signals**: These were identified as potentially valuable but are **excluded from the initial signal taxonomy**. They may be added via a future ADR amendment.
- **Automated node creation in the graph**: Unmatched entities go to a review queue. The pipeline does not auto-create Company or Product nodes without human approval.
- **Modification of the Stage 1 data model**: No new relationship types or entity types are introduced. The graph schema remains unchanged.

---

## Further Notes

### Integration With Stage 1 Knowledge Graph

The pipeline **reads** from the graph for entity linking (node names, IDs, types). It **writes** validated relations via the same CSV format and LOAD CSV pipeline used in Stage 1. Signal output is stored independently in `data/signal_library/` as JSONL files partitioned by quarter (`signals_2025Q1.jsonl`).

### Architecture Decision Record

This PRD is accompanied by **ADR-008: Dual-Stream Extraction and Independent Signal Storage**, which captures the core architectural tradeoff: transient state signals must not pollute the static dependency backbone, but they are too valuable to discard. The signal library is the bridge to the Event project.

### Prompt Strategy

The LLM system prompt must include:
- Clear definitions of all 10 signal types with direction enumerations
- The 6 boundary rules
- Few-shot examples showing correct extraction and split decisions
- Explicit instruction to output valid JSON with both `relations` and `signals` arrays
- Instruction to never auto-assign `confirmed` confidence

### Glossary Alignment

All terms in the signal schema (`subject_entity`, `object_entity`, `direction`, `evidence_quality`, `temporal`, `match_status`) are defined in the project glossary and consistent with Stage 1 terminology where overlap exists (Company, Product, Commodity).

---
