# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root, or
- **`CONTEXT-MAP.md`** at the repo root if it exists — it points at one `CONTEXT.md` per context. Read each one relevant to the topic.
- **`PRD.md`** — contains ADRs (architecture decision records) for this repo.
- **`CONTEXT.md`** — domain glossary.

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The producer skill (`/grill-with-docs`) creates them lazily when terms or decisions actually get resolved.

## File structure

```
/
├── README.md              # Usage guide
├── PRD.md                 # Product requirements + ADRs
├── CONTEXT.md             # Domain glossary
├── AGENTS.md              # Agent skills
├── src/earnings_call_ingestion/
│   ├── schemas.py
│   ├── pipeline.py
│   └── ...
├── data/
│   ├── transcripts/
│   ├── relations_library/
│   ├── signal_library/
│   └── review_queue/
├── process_response.py
└── run_pipeline.py
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/grill-with-docs`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders) — but worth reopening because…_
