import json

import pytest

from earnings_call_ingestion.schemas import ExtractionResult, TranscriptInput
from earnings_call_ingestion.llm_extractor import LLMExtractor


def _make_valid_response() -> dict:
    return {
        "relations": [],
        "signals": [
            {
                "signal_type": "cost_change",
                "signal_id": "TST--signal--0001",
                "transcript_id": "TST-2025Q1",
                "direction": "increase",
                "subject_entity": {"name": "Acme", "type": "company"},
                "match_status_subject": "unmatched",
                "statement": "Costs went up.",
                "evidence_quality": "explicit",
                "temporal": {"granularity": "quarter"},
                "source": {
                    "section": "prepared_remarks",
                    "excerpt": "Costs went up.",
                },
            }
        ],
    }


class MockModel:
    def __init__(self, responses: list | None = None):
        self._responses = responses or []
        self._call_count = 0
        self._last_prompt = None

    def generate_content(self, prompt: str):
        self._call_count += 1
        self._last_prompt = prompt
        if self._responses:
            resp = self._responses.pop(0)
            if isinstance(resp, Exception):
                raise resp
            return resp
        return _make_valid_response()


class MockResponse:
    def __init__(self, text: str):
        self.text = text
        self.candidates = [type("obj", (), {"finish_reason": 1})()]


class TestLLMExtractor:
    def test_returns_extraction_result_on_success(self):
        model = MockModel(
            [MockResponse(json.dumps(_make_valid_response()))]
        )
        extractor = LLMExtractor(model=model)
        transcript = TranscriptInput(
            transcript_id="TST-2025Q1",
            company_name="Test",
            company_ticker="TST",
            quarter="2025Q1",
            call_date="2025-01-01",
            sections=[],
        )
        result = extractor.extract(transcript, "some prompt")
        assert isinstance(result, ExtractionResult)
        assert len(result.signals) == 1

    def test_retries_on_transient_error(self):
        class TransientError(Exception):
            pass

        model = MockModel(
            [
                TransientError("rate limit"),
                TransientError("timeout"),
                MockResponse(json.dumps(_make_valid_response())),
            ]
        )
        extractor = LLMExtractor(model=model, max_retries=3)
        transcript = TranscriptInput(
            transcript_id="TST-2025Q1",
            company_name="Test",
            company_ticker="TST",
            quarter="2025Q1",
            call_date="2025-01-01",
            sections=[],
        )
        result = extractor.extract(transcript, "prompt")
        assert model._call_count == 3
        assert isinstance(result, ExtractionResult)

    def test_repairs_malformed_json(self):
        bad_json = "{relations: [], signals: []}"
        model = MockModel(
            [
                MockResponse(bad_json),
                MockResponse(json.dumps(_make_valid_response())),
            ]
        )
        extractor = LLMExtractor(model=model)
        transcript = TranscriptInput(
            transcript_id="TST-2025Q1",
            company_name="Test",
            company_ticker="TST",
            quarter="2025Q1",
            call_date="2025-01-01",
            sections=[],
        )
        result = extractor.extract(transcript, "prompt")
        assert model._call_count == 2
        assert isinstance(result, ExtractionResult)

    def test_logs_failure_and_raises_on_exhausted_retries(self, tmp_path):
        class PersistentError(Exception):
            pass

        model = MockModel(
            [
                PersistentError("always fails"),
                PersistentError("always fails"),
                PersistentError("always fails"),
            ]
        )
        failures_dir = tmp_path / "failures"
        failures_dir.mkdir()
        extractor = LLMExtractor(model=model, max_retries=3, failures_dir=str(failures_dir))
        transcript = TranscriptInput(
            transcript_id="TST-2025Q1",
            company_name="Test",
            company_ticker="TST",
            quarter="2025Q1",
            call_date="2025-01-01",
            sections=[],
        )
        with pytest.raises(RuntimeError, match="Extraction failed after 3 retries"):
            extractor.extract(transcript, "prompt")
        log_file = failures_dir / "failed_extractions.jsonl"
        assert log_file.exists()
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 1
        assert "TST-2025Q1" in lines[0]
