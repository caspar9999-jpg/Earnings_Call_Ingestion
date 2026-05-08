import pytest

from earnings_call_ingestion.relation_validator import RelationValidator
from earnings_call_ingestion.review_collector import ReviewCollector
from earnings_call_ingestion.schemas import (
    Entity,
    EntityType,
    EvidenceQuality,
    MatchStatus,
    Relation,
    RelationConfidence,
    RelationType,
    ReviewReason,
    SourceReference,
    Temporal,
    TemporalGranularity,
)


def _make_relation(
    relation_id: str = "TST--relation--0001",
    relation_type: RelationType = RelationType.SUPPLIES_TO,
    subject_name: str = "Apple",
    object_name: str = "Foxconn",
    llm_confidence: RelationConfidence | None = RelationConfidence.EXPLICIT,
) -> Relation:
    return Relation(
        relation_id=relation_id,
        transcript_id="TST-2025Q1",
        relation_type=relation_type,
        subject_entity=Entity(name=subject_name, type=EntityType.COMPANY),
        match_status_subject=MatchStatus.UNMATCHED,
        object_entity=Entity(name=object_name, type=EntityType.COMPANY),
        match_status_object=MatchStatus.UNMATCHED,
        statement=f"{object_name} supplies {subject_name}.",
        llm_confidence=llm_confidence,
        evidence_quality=EvidenceQuality.EXPLICIT,
        temporal=Temporal(granularity=TemporalGranularity.ONGOING),
        source=SourceReference(section="prepared_remarks", excerpt="Test excerpt."),
    )


class TestRelationValidator:
    def test_rejects_self_loop(self):
        validator = RelationValidator()
        collector = ReviewCollector()
        rel = _make_relation(subject_name="Apple", object_name="Apple")
        valid = validator.validate([rel], collector)
        assert len(valid) == 0
        assert len(collector.entries) == 1
        assert collector.entries[0].review_reason == ReviewReason.VALIDATION_FAILURE

    def test_rejects_missing_confidence(self):
        validator = RelationValidator()
        collector = ReviewCollector()
        rel = _make_relation(llm_confidence=None)
        valid = validator.validate([rel], collector)
        assert len(valid) == 0
        assert len(collector.entries) == 1
        assert collector.entries[0].review_reason == ReviewReason.VALIDATION_FAILURE

    def test_passes_valid_relation(self):
        validator = RelationValidator()
        collector = ReviewCollector()
        rel = _make_relation()
        valid = validator.validate([rel], collector)
        assert len(valid) == 1
        assert len(collector.entries) == 1

    def test_flags_unmatched_entities(self):
        validator = RelationValidator()
        collector = ReviewCollector()
        rel = _make_relation()
        validator.validate([rel], collector)
        review_reasons = [e.review_reason for e in collector.entries]
        assert ReviewReason.UNMATCHED_ENTITY in review_reasons

    def test_flags_speculative_confidence(self):
        validator = RelationValidator()
        collector = ReviewCollector()
        rel = _make_relation(llm_confidence=RelationConfidence.SPECULATIVE)
        validator.validate([rel], collector)
        review_reasons = [e.review_reason for e in collector.entries]
        assert ReviewReason.LOW_CONFIDENCE in review_reasons

    def test_flags_candidate_used_in(self):
        validator = RelationValidator()
        collector = ReviewCollector()
        rel = _make_relation(relation_type=RelationType.USED_IN)
        validator.validate([rel], collector)
        review_reasons = [e.review_reason for e in collector.entries]
        assert ReviewReason.CANDIDATE_USED_IN in review_reasons

    def test_entry_type_is_relation(self):
        validator = RelationValidator()
        collector = ReviewCollector()
        rel = _make_relation()
        validator.validate([rel], collector)
        for entry in collector.entries:
            assert entry.entry_type == "relation"
