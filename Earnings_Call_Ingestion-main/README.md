# Supply Chain Signal Extractor — Earnings Call Ingestion Pipeline

Automated pipeline that processes earnings call transcripts via Gemini to extract supply chain intelligence. Produces two independent streams: **relations** (structural supply chain links for human review) and **signals** (10 types of transient state changes).

## Quick Start

```bash
pip install -r requirements.txt
```

Create `.env` in the project root:
```
GEMINI_API_KEY=your-key
```

Process a single transcript:
```bash
python run_pipeline.py process-one path/to/transcript.json --dry-run
```

Remove `--dry-run` to write results to `data/signal_library/` and `data/review_queue/`.

Batch process a folder of transcripts:
```bash
python run_pipeline.py process path/to/folder/
```

Run tests:
```bash
pytest tests/
pytest tests/ --run-integration    # needs API key
```

## Input Format

Transcripts must be canonical JSON:

```json
{
  "transcript_id": "AAPL-2025Q1",
  "company_name": "Apple Inc.",
  "company_ticker": "AAPL",
  "quarter": "2025Q1",
  "call_date": "2025-01-30",
  "sections": [
    {
      "section_type": "prepared_remarks",
      "speakers": [{"name": "Tim Cook", "role": "ceo"}],
      "text": "This quarter was strong..."
    }
  ]
}
```

- `quarter`: pattern `\d{4}Q[1-4]` (e.g. `2025Q1`)
- `section_type`: `"prepared_remarks"` or `"q_and_a"`
- `speaker.role`: `ceo`, `cfo`, `coo`, `analyst`, `executive`, `operator`, `other`

## Output Layout

```
data/
├── signal_library/
│   ├── signals_2025Q1.jsonl      # explicit + implicit signals
│   └── vague_2025Q1.jsonl        # vague signals (audit log)
├── review_queue/
│   └── review_2025Q1.jsonl       # flagged items for human curation
├── failures/
│   └── failed_extractions.jsonl  # transcripts that failed processing
└── synthetic_transcripts/        # 12 golden test transcripts
```

## Signal Types (10)

| Type | Directions |
|------|-----------|
| `cost_change` | increase, decrease, volatile |
| `price_adjustment` | increase, decrease, volatile |
| `market_price_shift` | increase, decrease, volatile |
| `production_status_change` | disruption, recovery, increase, decrease, volatile |
| `supply_status_change` | disruption, recovery |
| `logistics_status_change` | disruption, recovery |
| `capacity_expansion` | expansion, contraction |
| `demand_shift` | increase, decrease |
| `contract_modification` | strengthen, weaken, modify |
| `outlook_uncertainty` | null |

## Evidence Quality Tiers

| Tier | Criteria | Storage |
|------|----------|---------|
| `explicit` | Clear direction + specific dimension + numeric value OR explicit entity | signals_{Q}.jsonl |
| `implicit` | One logical inference step, high reliability | signals_{Q}.jsonl |
| `vague` | Multiple interpretations possible | vague_{Q}.jsonl |

`outlook_uncertainty` signals bypass this filter entirely.

## Architecture

```
Transcript JSON → Preprocessor → LLM Extractor (Gemini 2.5 Flash)
                                      │
                              ExtractionResult
                             /                \
                    Signal Validator     Relation Validator
                    /         \                │
          signals_{Q}   vague_{Q}      Review Entries
                                           │
                                    Boundary Overlap Detector
                                           │
                                    review_{Q}.jsonl
```

- **Single LLM call** returns both relations and signals in one JSON response
- **No chunking** — Gemini's 1M token window handles full transcripts
- **Entity linking skipped for MVP** — all entities marked `match_status: unmatched`
- **Graph injection deferred** — relations routed to human review queue

## Module Reference

| Module | File | Purpose |
|--------|------|---------|
| Schemas | `src/earnings_call_ingestion/schemas.py` | All Pydantic data models |
| Preprocessor | `transcript_preprocessor.py` | Validate input, strip `_ground_truth` |
| Prompt Builder | `prompt_builder.py` | Composable prompt factory |
| LLM Extractor | `llm_extractor.py` | Gemini API wrapper + retry + JSON repair |
| Signal Validator | `signal_validator.py` | Evidence quality routing |
| Relation Validator | `relation_validator.py` | Self-loop/confidence checks + review triggers |
| Boundary Overlap | `boundary_overlap.py` | Detect same excerpt in both streams |
| Writer | `writer.py` | Quarter-partitioned JSONL writer |
| CLI | `cli.py` | `process-one` and `process` commands |

## Tests

- **71 unit tests** — run with `pytest tests/` (no external dependencies)
- **13 integration tests** — run with `pytest tests/ --run-integration` (needs API key)
- **12 synthetic transcripts** — golden data with ground truth in `data/synthetic_transcripts/`

## Issue Tracker

[GitHub Issues](https://github.com/caspar9999-jpg/Earnings_Call_Ingestion/issues) — 8 issues published covering the full build.

## Configuration

Environment variables (via `.env` or system env):
- `GEMINI_API_KEY` — required, your Google AI Studio API key
- `GOOGLE_API_KEY` — alternative name (falls back if `GEMINI_API_KEY` not set)

## Key Decisions

- **Dual-stream, single LLM call** — reduces cost and ensures shared entity context
- **Google Gemini 2.5 Flash** — free tier, 1,500 req/day, 1M token context
- **JSONL quarter-partitioned storage** — simple, versionable, no database needed
- **Sequential processing** — no concurrency for MVP
- **No entity linking** — all entities `unmatched` until graph access available

## Glossary

- **Signal**: A transient supply chain state change (price, disruption, demand, etc.)
- **Relation**: A structural supply chain link (who supplies whom, what goes into what)
- **Evidence quality**: How directly the source sentence supports the extracted fact
- **Review entry**: A flagged item pending human review (unmatched entity, low confidence, boundary overlap, etc.)
