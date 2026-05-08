import argparse
import json
import os
import sys
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate synthetic earnings call transcripts with embedded ground truth"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=12,
        help="Number of synthetic transcripts to generate (default: 12)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/synthetic_transcripts",
        help="Output directory for generated transcripts (default: data/synthetic_transcripts)",
    )
    return parser.parse_args(argv)


def build_prompt(transcript_index: int, total: int) -> str:
    signal_types = [
        "cost_change (direction: increase/decrease/volatile)",
        "price_adjustment (direction: increase/decrease/volatile)",
        "market_price_shift (direction: increase/decrease/volatile)",
        "production_status_change (direction: disruption/recovery/increase/decrease/volatile)",
        "supply_status_change (direction: disruption/recovery)",
        "logistics_status_change (direction: disruption/recovery)",
        "capacity_expansion (direction: expansion/contraction)",
        "demand_shift (direction: increase/decrease)",
        "contract_modification (direction: strengthen/weaken/modify)",
        "outlook_uncertainty (direction: always null)",
    ]

    return f"""You are generating synthetic earnings call transcript #{transcript_index} of {total} for testing a supply chain signal extraction pipeline.

Generate a realistic earnings call transcript for a fictional public company. The transcript must:

1. Follow the exact JSON schema below (the `TranscriptInput` format).
2. Include a `_ground_truth` field (at the same level as the other fields) containing the known signals and relations embedded in the transcript text.

The `_ground_truth` field has two arrays: "signals" and "relations". Each entry in those arrays should follow the schema below MINUS signal_id/relation_id/transcript_id/match_status fields (those are assigned by the pipeline at runtime).

COVERAGE INSTRUCTIONS - ensure across all {total} transcripts:
- All 10 signal types appear: {', '.join(signal_types)}
- Include edge cases: direction=volatile with volatility_intensity (low/moderate/high), direction=null for outlook_uncertainty
- Include at least one clean transcript with no signals or relations
- Include ambiguous entity names (same name could refer to different things)
- Boundary rule edge cases: sentences that could be interpreted as both a signal and a relation (put only in the correct stream)
- At least one supply_status_change with disruption
- At least one logistics_status_change with disruption
- At least one :USED_IN relation
- At least one relation with is_termination=true

Format your response as EXACTLY this JSON structure (no extra text, no markdown):

{{
  "transcript_id": "SYNTH-2025Q1-{transcript_index:03d}",
  "company_name": "<fictional company name>",
  "company_ticker": "<3-4 letter ticker>",
  "quarter": "2025Q1",
  "call_date": "2025-01-15",
  "sections": [
    {{
      "section_type": "prepared_remarks",
      "speakers": [{{"name": "<name>", "role": "ceo"}}],
      "text": "<2-3 paragraphs of prepared remarks>"
    }},
    {{
      "section_type": "q_and_a",
      "speakers": [{{"name": "<analyst name>", "role": "analyst"}}, {{"name": "<exec name>", "role": "executive"}}],
      "text": "<1-2 Q&A exchanges>"
    }}
  ],
  "_ground_truth": {{
    "signals": [
      {{
        "signal_type": "<one of the 10 types>",
        "direction": "<valid direction for type, or null for outlook_uncertainty>",
        "subject_entity": {{"name": "<entity name>", "type": "company|product|commodity|service|division"}},
        "object_entity": {{"name": "<entity name or null>", "type": "company|product|commodity|service|division"}},
        "statement": "<the exact sentence from the transcript>",
        "evidence_quality": "explicit|implicit|vague",
        "temporal": {{"granularity": "quarter|year|ongoing|forward_looking"}},
        "source": {{"section": "prepared_remarks|q_and_a", "excerpt": "<verbatim sentence>"}}
      }}
    ],
    "relations": [
      {{
        "relation_type": ":PROVIDES|:SUPPLIES_TO|:USED_IN",
        "subject_entity": {{"name": "<entity>", "type": "company|product|commodity"}},
        "object_entity": {{"name": "<entity>", "type": "company|product|commodity"}},
        "statement": "<exact sentence>",
        "llm_confidence": "explicit|implicit|speculative",
        "evidence_quality": "explicit|implicit|vague",
        "is_termination": false,
        "temporal": {{"granularity": "ongoing|quarter"}},
        "source": {{"section": "prepared_remarks|q_and_a", "excerpt": "<verbatim sentence>"}}
      }}
    ]
  }}
}}

IMPORTANT: 
- The _ground_truth entries must EXACTLY match statements that appear verbatim in the transcript text.
- Do not include signal_id, relation_id, transcript_id, match_status_subject, or match_status_object in _ground_truth entries.
- Return ONLY valid JSON. No explanation, no markdown formatting."""


def _call_gemini(prompt: str) -> str:
    import google.genai as genai
    import os

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text


def _clean_response(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.strip().startswith("```"):
                lines[i] = ""
        text = "\n".join(lines).strip()
    return text


def generate_transcript(index: int, total: int, output_dir: str) -> dict:
    prompt = build_prompt(index, total)
    raw = _call_gemini(prompt)
    cleaned = _clean_response(raw)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"Failed to parse transcript {index}: {e}", file=sys.stderr)
        print(f"Raw response: {raw[:500]}", file=sys.stderr)
        raise

    output_path = Path(output_dir) / f"SYNTH-2025Q1-{index:03d}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Generated {output_path}")
    return data


def main() -> None:
    args = parse_args()

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    print(f"Generating {args.count} synthetic transcripts to {args.output_dir}...")
    for i in range(1, args.count + 1):
        generate_transcript(i, args.count, args.output_dir)

    print(f"\nDone! Generated {args.count} transcripts in {args.output_dir}")
    print("HITL: Please verify each transcript's _ground_truth field for correctness.")


if __name__ == "__main__":
    main()
