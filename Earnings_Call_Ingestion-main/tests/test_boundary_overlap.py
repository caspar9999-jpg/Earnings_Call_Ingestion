from earnings_call_ingestion.boundary_overlap import BoundaryOverlapDetector
from earnings_call_ingestion.review_collector import ReviewCollector
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
    ReviewReason,
    SourceReference,
    Temporal,
    TemporalGranularity,
)


def _make_signal(excerpt: str, signal_id: str = "s1") -> CostChange:
    return CostChange(
        signal_id=signal_id,
        transcript_id="TST-2025Q1",
        direction=DirectionCostChange.INCREASE,
        subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
        match_status_subject=MatchStatus.UNMATCHED,
        statement="Statement.",
        evidence_quality=EvidenceQuality.EXPLICIT,
        temporal=Temporal(granularity=TemporalGranularity.QUARTER),
        source=SourceReference(
            section="prepared_remarks",
            excerpt=excerpt,
        ),
    )


def _make_relation(excerpt: str, relation_id: str = "r1") -> Relation:
    return Relation(
        relation_id=relation_id,
        transcript_id="TST-2025Q1",
        relation_type=RelationType.SUPPLIES_TO,
        subject_entity=Entity(name="Apple", type=EntityType.COMPANY),
        match_status_subject=MatchStatus.UNMATCHED,
        object_entity=Entity(name="Foxconn", type=EntityType.COMPANY),
        match_status_object=MatchStatus.UNMATCHED,
        statement="Statement.",
        llm_confidence=RelationConfidence.EXPLICIT,
        evidence_quality=EvidenceQuality.EXPLICIT,
        temporal=Temporal(granularity=TemporalGranularity.ONGOING),
        source=SourceReference(
            section="prepared_remarks",
            excerpt=excerpt,
        ),
    )


class TestBoundaryOverlapDetector:
    def test_detects_overlap_between_signal_and_relation(self):
        detector = BoundaryOverlapDetector()
        collector = ReviewCollector()
        signal = _make_signal("Costs rose 10% this quarter.")
        relation = _make_relation("Costs rose 10% this quarter.")
        result = ExtractionResult(relations=[relation], signals=[signal])
        detector.detect(result, collector)
        assert len(collector.entries) == 2
        for entry in collector.entries:
            assert entry.review_reason == ReviewReason.BOUNDARY_OVERLAP

    def test_no_overlap_when_excerpts_differ(self):
        detector = BoundaryOverlapDetector()
        collector = ReviewCollector()
        signal = _make_signal("Costs rose 10% this quarter.")
        relation = _make_relation("Foxconn supplies Apple.")
        result = ExtractionResult(relations=[relation], signals=[signal])
        detector.detect(result, collector)
        assert len(collector.entries) == 0

    def test_multiple_signals_same_excerpt(self):
        detector = BoundaryOverlapDetector()
        collector = ReviewCollector()
        signal1 = _make_signal("The same excerpt.", "s1")
        signal2 = _make_signal("The same excerpt.", "s2")
        relation = _make_relation("The same excerpt.", "r1")
        result = ExtractionResult(relations=[relation], signals=[signal1, signal2])
        detector.detect(result, collector)
        assert len(collector.entries) == 3
