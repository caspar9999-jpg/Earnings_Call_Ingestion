from datetime import date

from earnings_call_ingestion.pipeline import Pipeline, PipelineResult
from earnings_call_ingestion.schemas import (
    CostChange,
    DirectionCostChange,
    Entity,
    EntityType,
    EvidenceQuality,
    ExtractionResult,
    MatchStatus,
    Relation,
    RelationConfidence,
    RelationType,
    SourceReference,
    Temporal,
    TemporalGranularity,
    TranscriptInput,
)
from earnings_call_ingestion.review_collector import ReviewCollector


class MockLLMExtractor:
    def __init__(self, extraction: ExtractionResult | None = None) -> None:
        self._extraction = extraction or ExtractionResult()
        self.extract_calls: list[tuple] = []

    def extract(self, transcript, prompt: str) -> ExtractionResult:
        self.extract_calls.append((transcript, prompt))
        return self._extraction


class TestPipeline:
    def test_returns_pipeline_result_with_valid_extraction(self):
        llm = MockLLMExtractor(
            ExtractionResult(
                signals=[
                    CostChange(
                        signal_type="cost_change",
                        signal_id="TST--signal--0001",
                        transcript_id="TST-2025Q1",
                        direction=DirectionCostChange.INCREASE,
                        subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
                        match_status_subject=MatchStatus.UNMATCHED,
                        statement="Costs up.",
                        evidence_quality=EvidenceQuality.EXPLICIT,
                        temporal=Temporal(granularity=TemporalGranularity.QUARTER),
                        source=SourceReference(
                            section="prepared_remarks", excerpt="Costs up."
                        ),
                    )
                ],
                relations=[],
            )
        )
        pipeline = Pipeline(llm_extractor=llm)
        transcript = TranscriptInput(
            transcript_id="TST-2025Q1",
            company_name="Test",
            company_ticker="TST",
            quarter="2025Q1",
            call_date=date(2025, 1, 1),
            sections=[],
        )

        result = pipeline.run(transcript, "2025Q1")

        assert isinstance(result, PipelineResult)
        assert len(result.production_signals) == 1
        assert len(result.vague_signals) == 0
        assert len(result.review_entries) == 0

    def test_routes_vague_signal_correctly(self):
        llm = MockLLMExtractor(
            ExtractionResult(
                signals=[
                    CostChange(
                        signal_type="cost_change",
                        signal_id="TST--signal--0001",
                        transcript_id="TST-2025Q1",
                        direction=DirectionCostChange.INCREASE,
                        subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
                        match_status_subject=MatchStatus.UNMATCHED,
                        statement="Maybe costs.",
                        evidence_quality=EvidenceQuality.VAGUE,
                        temporal=Temporal(granularity=TemporalGranularity.QUARTER),
                        source=SourceReference(
                            section="prepared_remarks", excerpt="Maybe costs."
                        ),
                    )
                ],
                relations=[],
            )
        )
        pipeline = Pipeline(llm_extractor=llm)
        transcript = TranscriptInput(
            transcript_id="TST-2025Q1",
            company_name="Test",
            company_ticker="TST",
            quarter="2025Q1",
            call_date=date(2025, 1, 1),
            sections=[],
        )

        result = pipeline.run(transcript, "2025Q1")

        assert len(result.production_signals) == 0
        assert len(result.vague_signals) == 1

    def test_routes_relation_validation_failure_to_review(self):
        llm = MockLLMExtractor(
            ExtractionResult(
                signals=[],
                relations=[
                    Relation(
                        relation_id="TST--relation--0001",
                        transcript_id="TST-2025Q1",
                        relation_type=RelationType.SUPPLIES_TO,
                        subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
                        match_status_subject=MatchStatus.UNMATCHED,
                        object_entity=Entity(name="Acme", type=EntityType.COMPANY),
                        match_status_object=MatchStatus.UNMATCHED,
                        statement="Self loop.",
                        llm_confidence=RelationConfidence.EXPLICIT,
                        evidence_quality=EvidenceQuality.EXPLICIT,
                        temporal=Temporal(granularity=TemporalGranularity.ONGOING),
                        source=SourceReference(
                            section="prepared_remarks", excerpt="Self loop."
                        ),
                    )
                ],
            )
        )
        pipeline = Pipeline(llm_extractor=llm)
        transcript = TranscriptInput(
            transcript_id="TST-2025Q1",
            company_name="Test",
            company_ticker="TST",
            quarter="2025Q1",
            call_date=date(2025, 1, 1),
            sections=[],
        )

        result = pipeline.run(transcript, "2025Q1")

        assert len(result.review_entries) == 1
        assert result.review_entries[0].review_id.endswith("--validation_failure")

    def test_passes_quarter_to_result(self):
        llm = MockLLMExtractor(
            ExtractionResult(
                signals=[],
                relations=[],
            )
        )
        pipeline = Pipeline(llm_extractor=llm)
        transcript = TranscriptInput(
            transcript_id="TST-2025Q2",
            company_name="Test",
            company_ticker="TST",
            quarter="2025Q2",
            call_date=date(2025, 4, 1),
            sections=[],
        )

        result = pipeline.run(transcript, "2025Q2")

        assert isinstance(result, PipelineResult)
        assert result.extraction is not None

    def test_default_llm_extractor_is_created(self):
        pipeline = Pipeline()
        assert pipeline._llm is not None

    def test_embeds_transcript_text_in_llm_prompt(self):
        llm = MockLLMExtractor(ExtractionResult())
        pipeline = Pipeline(llm_extractor=llm)
        transcript = TranscriptInput(
            transcript_id="TST-2025Q1",
            company_name="Test",
            company_ticker="TST",
            quarter="2025Q1",
            call_date=date(2025, 1, 1),
            sections=[
                {
                    "section_type": "prepared_remarks",
                    "speakers": [],
                    "text": "Hello and welcome to the Q1 call.",
                },
                {
                    "section_type": "q_and_a",
                    "speakers": [],
                    "text": "First question from the analyst.",
                },
            ],
        )

        result = pipeline.run(transcript, "2025Q1")

        _, prompt = llm.extract_calls[0]
        assert "Hello and welcome to the Q1 call." in prompt, "prepared_remarks text should be in prompt"
        assert "First question from the analyst." in prompt, "q_and_a text should be in prompt"
