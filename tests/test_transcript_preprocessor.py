import json
from datetime import date
from pathlib import Path

import pytest

from earnings_call_ingestion.schemas import TranscriptInput
from earnings_call_ingestion.transcript_preprocessor import TranscriptPreprocessor


@pytest.fixture
def valid_transcript_data() -> dict:
    return {
        "transcript_id": "AAPL-2025Q1",
        "company_name": "Apple Inc.",
        "company_ticker": "AAPL",
        "quarter": "2025Q1",
        "call_date": "2025-01-30",
        "sections": [
            {
                "section_type": "prepared_remarks",
                "speakers": [{"name": "Tim Cook", "role": "ceo"}],
                "text": "This quarter was strong.",
            }
        ],
    }


@pytest.fixture
def valid_transcript_with_ground_truth(valid_transcript_data) -> dict:
    data = dict(valid_transcript_data)
    data["_ground_truth"] = {"signals": [], "relations": []}
    return data


class TestTranscriptPreprocessor:
    def test_validates_canonical_input(self, tmp_path, valid_transcript_data):
        path = tmp_path / "transcript.json"
        path.write_text(json.dumps(valid_transcript_data))
        preprocessor = TranscriptPreprocessor()
        result = preprocessor.process(str(path))
        assert isinstance(result.transcript, TranscriptInput)
        assert result.transcript.transcript_id == "AAPL-2025Q1"

    def test_extracts_quarter_from_input(self, tmp_path, valid_transcript_data):
        path = tmp_path / "transcript.json"
        path.write_text(json.dumps(valid_transcript_data))
        preprocessor = TranscriptPreprocessor()
        result = preprocessor.process(str(path))
        assert result.quarter == "2025Q1"

    def test_strips_ground_truth(self, tmp_path, valid_transcript_with_ground_truth):
        path = tmp_path / "transcript.json"
        path.write_text(json.dumps(valid_transcript_with_ground_truth))
        preprocessor = TranscriptPreprocessor()
        result = preprocessor.process(str(path))
        file_data = json.loads(path.read_text())
        assert "_ground_truth" in file_data
        assert result.transcript.transcript_id == "AAPL-2025Q1"

    def test_rejects_invalid_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not json")
        preprocessor = TranscriptPreprocessor()
        with pytest.raises(ValueError, match="Invalid JSON"):
            preprocessor.process(str(path))

    def test_rejects_missing_required_fields(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"transcript_id": "TEST"}))
        preprocessor = TranscriptPreprocessor()
        with pytest.raises(ValueError, match="Invalid transcript"):
            preprocessor.process(str(path))
