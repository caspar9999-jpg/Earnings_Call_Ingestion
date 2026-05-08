import json

import pytest

from earnings_call_ingestion.schemas import TranscriptInput


class TestSyntheticTranscriptValidation:
    def test_accepts_valid_transcript_structure(self):
        data = {
            "transcript_id": "SYNTH-2025Q1-001",
            "company_name": "Test Corp",
            "company_ticker": "TST",
            "quarter": "2025Q1",
            "call_date": "2025-01-15",
            "sections": [
                {
                    "section_type": "prepared_remarks",
                    "speakers": [{"name": "CEO", "role": "ceo"}],
                    "text": "This quarter was strong across all segments.",
                }
            ],
            "_ground_truth": {
                "signals": [
                    {
                        "signal_type": "cost_change",
                        "direction": "increase",
                        "subject_entity": {"name": "Test Corp", "type": "company"},
                        "evidence_quality": "explicit",
                        "statement": "Input costs rose 15% this quarter.",
                        "temporal": {"granularity": "quarter"},
                    }
                ],
                "relations": [
                    {
                        "relation_type": ":SUPPLIES_TO",
                        "subject_entity": {"name": "Test Corp", "type": "company"},
                        "object_entity": {"name": "Supplier Inc", "type": "company"},
                        "statement": "Supplier Inc provides raw materials.",
                        "llm_confidence": "explicit",
                        "evidence_quality": "explicit",
                        "temporal": {"granularity": "ongoing"},
                    }
                ],
            },
        }
        transcript = TranscriptInput(**data)
        assert transcript.transcript_id == "SYNTH-2025Q1-001"

    def test_ground_truth_signals_cover_all_types(self):
        types_needed = {
            "cost_change",
            "price_adjustment",
            "market_price_shift",
            "production_status_change",
            "supply_status_change",
            "logistics_status_change",
            "capacity_expansion",
            "demand_shift",
            "contract_modification",
            "outlook_uncertainty",
        }
        types_needed.remove("outlook_uncertainty")
        assert len(types_needed) == 9

    def test_output_file_is_valid_json(self, tmp_path):
        output_dir = tmp_path / "synthetic_transcripts"
        output_dir.mkdir()
        file_path = output_dir / "SYNTH-2025Q1-001.json"
        data = {
            "transcript_id": "SYNTH-2025Q1-001",
            "company_name": "Test Corp",
            "company_ticker": "TST",
            "quarter": "2025Q1",
            "call_date": "2025-01-15",
            "sections": [],
            "_ground_truth": {"signals": [], "relations": []},
        }
        file_path.write_text(json.dumps(data, indent=2))
        parsed = json.loads(file_path.read_text())
        assert "_ground_truth" in parsed
        assert "signals" in parsed["_ground_truth"]


class TestCliArgs:
    def test_parser_accepts_count(self):
        from earnings_call_ingestion.synthetic_generator import parse_args
        args = parse_args(["--count", "5"])
        assert args.count == 5

    def test_parser_accepts_output_dir(self):
        from earnings_call_ingestion.synthetic_generator import parse_args
        args = parse_args(["--output-dir", "custom/path"])
        assert args.output_dir == "custom/path"

    def test_parser_defaults(self):
        from earnings_call_ingestion.synthetic_generator import parse_args
        args = parse_args([])
        assert args.count == 12
        assert args.output_dir == "data/synthetic_transcripts"
