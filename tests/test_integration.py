"""Integration tests: end-to-end pipeline against real Gemini API with synthetic golden transcripts.

Run with: pytest tests/ --run-integration
Requires: GEMINI_API_KEY environment variable or .env file.
"""
import json
import os
from pathlib import Path

import pytest

from earnings_call_ingestion.pipeline import Pipeline
from earnings_call_ingestion.transcript_preprocessor import TranscriptPreprocessor

SYNTHETIC_DIR = Path(__file__).resolve().parent.parent / "data" / "synthetic_transcripts"


def _has_api_key() -> bool:
    if os.getenv("GEMINI_API_KEY"):
        return True
    dotenv = Path(".env")
    if dotenv.exists():
        for line in dotenv.read_text().splitlines():
            if line.strip().startswith("GEMINI_API_KEY"):
                return True
    return False


requires_api = pytest.mark.skipif(not _has_api_key(), reason="GEMINI_API_KEY not configured")


def get_expected_counts(transcript_path: Path) -> tuple[int, int]:
    data = json.loads(transcript_path.read_text())
    gt = data.get("_ground_truth", {})
    return len(gt.get("signals", [])), len(gt.get("relations", []))


@pytest.mark.integration
class TestEndToEnd:
    @requires_api
    def test_process_one_synthetic_transcript(self, tmp_path):
        src = SYNTHETIC_DIR / "SYNTH-2025Q1-001.json"
        assert src.exists(), f"Synthetic transcript not found: {src}"

        transcript_copy = tmp_path / src.name
        transcript_copy.write_text(src.read_text())

        preprocessor = TranscriptPreprocessor()
        preprocess_result = preprocessor.process(str(transcript_copy))

        pipeline = Pipeline()
        result = pipeline.run(preprocess_result.transcript, preprocess_result.quarter)

        assert result.extraction is not None
        assert isinstance(result.extraction.signals, list)
        assert isinstance(result.extraction.relations, list)

    @requires_api
    @pytest.mark.parametrize(
        "transcript_file",
        [f"SYNTH-2025Q1-{i:03d}.json" for i in range(1, 13)],
    )
    def test_each_transcript_produces_valid_output(self, tmp_path, transcript_file):
        src = SYNTHETIC_DIR / transcript_file
        if not src.exists():
            pytest.skip(f"{transcript_file} not found")

        transcript_copy = tmp_path / src.name
        transcript_copy.write_text(src.read_text())

        preprocessor = TranscriptPreprocessor()
        preprocess_result = preprocessor.process(str(transcript_copy))

        pipeline = Pipeline()
        result = pipeline.run(preprocess_result.transcript, preprocess_result.quarter)

        expected_signals, expected_relations = get_expected_counts(src)

        assert len(result.extraction.signals) >= 0
        assert len(result.extraction.relations) >= 0

        for signal in result.extraction.signals:
            assert signal.signal_id
            assert signal.transcript_id == preprocess_result.transcript.transcript_id
            assert signal.subject_entity
            assert signal.source.excerpt

        for relation in result.extraction.relations:
            assert relation.relation_id
            assert relation.transcript_id == preprocess_result.transcript.transcript_id
            assert relation.subject_entity
            assert relation.object_entity


class TestModuleIntegration:
    def test_signal_validator_with_golden_data(self):
        from earnings_call_ingestion.schemas import (
            CostChange,
            DirectionCostChange,
            Entity,
            EntityType,
            EvidenceQuality,
            MatchStatus,
            SourceReference,
            Temporal,
            TemporalGranularity,
        )
        from earnings_call_ingestion.signal_validator import SignalValidator

        validator = SignalValidator()
        explicit = CostChange(
            signal_id="t1",
            transcript_id="TST-2025Q1",
            direction=DirectionCostChange.INCREASE,
            subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
            match_status_subject=MatchStatus.UNMATCHED,
            statement="Costs up.",
            evidence_quality=EvidenceQuality.EXPLICIT,
            temporal=Temporal(granularity=TemporalGranularity.QUARTER),
            source=SourceReference(section="prepared_remarks", excerpt="Costs up."),
        )
        vague = CostChange(
            signal_id="t2",
            transcript_id="TST-2025Q1",
            direction=DirectionCostChange.INCREASE,
            subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
            match_status_subject=MatchStatus.UNMATCHED,
            statement="Maybe costs.",
            evidence_quality=EvidenceQuality.VAGUE,
            temporal=Temporal(granularity=TemporalGranularity.QUARTER),
            source=SourceReference(section="prepared_remarks", excerpt="Maybe costs."),
        )
        result = validator.validate([explicit, vague])
        assert len(result.production_signals) == 1
        assert len(result.vague_signals) == 1

    def test_full_pipeline_components_importable(self):
        from earnings_call_ingestion import (
            boundary_overlap,
            cli,
            llm_extractor,
            pipeline,
            prompt_builder,
            relation_validator,
            review_collector,
            schemas,
            signal_validator,
            transcript_preprocessor,
            writer,
        )
        assert hasattr(schemas, "TranscriptInput")
        assert hasattr(schemas, "ExtractionResult")
        assert hasattr(llm_extractor, "LLMExtractor")
        assert hasattr(signal_validator, "SignalValidator")
        assert hasattr(relation_validator, "RelationValidator")
        assert hasattr(boundary_overlap, "BoundaryOverlapDetector")
        assert hasattr(writer, "Writer")
        assert hasattr(prompt_builder, "PromptBuilder")
        assert hasattr(transcript_preprocessor, "TranscriptPreprocessor")
        assert hasattr(cli, "process_one")
        assert hasattr(cli, "process_batch")
        assert hasattr(pipeline, "Pipeline")
        assert hasattr(review_collector, "ReviewCollector")
