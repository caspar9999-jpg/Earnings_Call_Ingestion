import logging

from earnings_call_ingestion.boundary_overlap import BoundaryOverlapDetector
from earnings_call_ingestion.ids import is_valid_relation_id, is_valid_signal_id
from earnings_call_ingestion.llm_extractor import LLMExtractor
from earnings_call_ingestion.prompt_builder import PromptBuilder
from earnings_call_ingestion.relation_validator import RelationValidator
from earnings_call_ingestion.review_collector import ReviewCollector
from earnings_call_ingestion.schemas import ExtractionResult, Relation, ReviewEntry, Signal, TranscriptInput
from earnings_call_ingestion.signal_validator import SignalValidator

_logger = logging.getLogger(__name__)


class PipelineResult:
    def __init__(
        self,
        extraction: ExtractionResult,
        valid_relations: list[Relation],
        production_signals: list[Signal],
        vague_signals: list[Signal],
        review_entries: list[ReviewEntry],
    ) -> None:
        self.extraction = extraction
        self.valid_relations = valid_relations
        self.production_signals = production_signals
        self.vague_signals = vague_signals
        self.review_entries = review_entries


class Pipeline:
    def __init__(self, llm_extractor: LLMExtractor | None = None) -> None:
        self._llm = llm_extractor or LLMExtractor()

    def run(self, transcript: TranscriptInput, quarter: str) -> PipelineResult:
        prompt = PromptBuilder.default_pipeline_prompt()
        extraction = self._llm.extract(transcript, prompt)

        self._validate_ids(extraction, transcript.transcript_id)

        signal_result = SignalValidator().validate(extraction.signals)

        collector = ReviewCollector()
        valid_relations = RelationValidator().validate(extraction.relations, collector)
        BoundaryOverlapDetector().detect(extraction, collector)

        return PipelineResult(
            extraction=extraction,
            valid_relations=valid_relations,
            production_signals=signal_result.production_signals,
            vague_signals=signal_result.vague_signals,
            review_entries=collector.entries,
        )

    def _validate_ids(
        self, extraction: ExtractionResult, transcript_id: str
    ) -> None:
        for sig in extraction.signals:
            if not is_valid_signal_id(sig.signal_id, transcript_id):
                _logger.warning(
                    "Signal ID %r does not match expected format for transcript %r",
                    sig.signal_id,
                    transcript_id,
                )

        for rel in extraction.relations:
            if not is_valid_relation_id(rel.relation_id, transcript_id):
                _logger.warning(
                    "Relation ID %r does not match expected format for transcript %r",
                    rel.relation_id,
                    transcript_id,
                )
