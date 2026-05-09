import json

import pytest

from earnings_call_ingestion.schemas import (
    CostChange,
    DirectionCostChange,
    Entity,
    EntityType,
    EvidenceQuality,
    MatchStatus,
    Relation,
    RelationConfidence,
    RelationType,
    SourceReference,
    Temporal,
    TemporalGranularity,
)
from earnings_call_ingestion.writer import Writer


def _make_signal(signal_id: str, quarter: str = "2025Q1") -> CostChange:
    return CostChange(
        signal_id=signal_id,
        transcript_id=f"TST-{quarter}",
        direction=DirectionCostChange.INCREASE,
        subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
        match_status_subject=MatchStatus.UNMATCHED,
        statement="Costs went up.",
        evidence_quality=EvidenceQuality.EXPLICIT,
        temporal=Temporal(granularity=TemporalGranularity.QUARTER),
        source=SourceReference(section="prepared_remarks", excerpt="Costs went up."),
    )


class TestWriter:
    def test_writes_signals_to_quarter_partitioned_file(self, tmp_path):
        writer = Writer(output_dir=str(tmp_path))
        signal = _make_signal("s1")
        writer.write_signals("2025Q1", [signal])
        file_path = tmp_path / "signal_library" / "signals_2025Q1.jsonl"
        assert file_path.exists()
        lines = file_path.read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["signal_id"] == "s1"

    def test_writes_vague_to_audit_log(self, tmp_path):
        writer = Writer(output_dir=str(tmp_path))
        signal = _make_signal("s2")
        writer.write_vague_signals("2025Q1", [signal])
        file_path = tmp_path / "signal_library" / "vague_2025Q1.jsonl"
        assert file_path.exists()

    def test_creates_output_directories(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c"
        writer = Writer(output_dir=str(nested))
        signal = _make_signal("s3")
        writer.write_signals("2025Q1", [signal])
        assert (nested / "signal_library" / "signals_2025Q1.jsonl").exists()

    def test_writes_relations_to_quarter_partitioned_file(self, tmp_path):
        writer = Writer(output_dir=str(tmp_path))
        relation = Relation(
            relation_id="TST--relation--0001",
            transcript_id="TST-2025Q1",
            relation_type=RelationType.SUPPLIES_TO,
            subject_entity=Entity(name="Nutrien", type=EntityType.COMPANY),
            match_status_subject=MatchStatus.UNMATCHED,
            object_entity=Entity(name="Cargill", type=EntityType.COMPANY),
            match_status_object=MatchStatus.UNMATCHED,
            statement="Nutrien supplies to Cargill.",
            llm_confidence=RelationConfidence.IMPLICIT,
            evidence_quality=EvidenceQuality.EXPLICIT,
            temporal=Temporal(granularity=TemporalGranularity.ONGOING),
            source=SourceReference(section="prepared_remarks", excerpt="Nutrien supplies to Cargill."),
        )
        writer.write_relations("2025Q1", [relation])
        file_path = tmp_path / "relations_library" / "relations_2025Q1.jsonl"
        assert file_path.exists()
        lines = file_path.read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["relation_id"] == "TST--relation--0001"

    def test_multiple_quarters_routed_to_separate_files(self, tmp_path):
        writer = Writer(output_dir=str(tmp_path))
        q1_signal = _make_signal("s1", "2025Q1")
        q2_signal = _make_signal("s2", "2025Q2")
        writer.write_signals("2025Q1", [q1_signal])
        writer.write_signals("2025Q2", [q2_signal])
        assert (tmp_path / "signal_library" / "signals_2025Q1.jsonl").exists()
        assert (tmp_path / "signal_library" / "signals_2025Q2.jsonl").exists()
