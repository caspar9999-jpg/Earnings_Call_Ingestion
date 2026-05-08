import pytest

from earnings_call_ingestion.schemas import (
    CostChange,
    DirectionCostChange,
    Entity,
    EntityType,
    EvidenceQuality,
    MatchStatus,
    OutlookUncertainty,
    SourceReference,
    Temporal,
    TemporalGranularity,
)
from earnings_call_ingestion.signal_validator import SignalValidator


def _make_cost_change(
    evidence: EvidenceQuality,
    signal_id: str = "TST--signal--0001",
) -> CostChange:
    return CostChange(
        signal_id=signal_id,
        transcript_id="TST-2025Q1",
        direction=DirectionCostChange.INCREASE,
        subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
        match_status_subject=MatchStatus.UNMATCHED,
        statement="Costs went up.",
        evidence_quality=evidence,
        temporal=Temporal(granularity=TemporalGranularity.QUARTER),
        source=SourceReference(section="prepared_remarks", excerpt="Costs went up."),
    )


def _make_outlook_uncertainty(
    evidence: EvidenceQuality,
    signal_id: str = "TST--signal--0002",
) -> OutlookUncertainty:
    return OutlookUncertainty(
        signal_id=signal_id,
        transcript_id="TST-2025Q1",
        subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
        match_status_subject=MatchStatus.UNMATCHED,
        statement="Outlook is uncertain.",
        evidence_quality=evidence,
        temporal=Temporal(granularity=TemporalGranularity.FORWARD_LOOKING),
        source=SourceReference(section="prepared_remarks", excerpt="Outlook is uncertain."),
    )


class TestSignalValidator:
    def test_routes_explicit_to_production(self):
        validator = SignalValidator()
        signal = _make_cost_change(EvidenceQuality.EXPLICIT)
        result = validator.validate([signal])
        assert len(result.production_signals) == 1
        assert len(result.vague_signals) == 0

    def test_routes_implicit_to_production(self):
        validator = SignalValidator()
        signal = _make_cost_change(EvidenceQuality.IMPLICIT)
        result = validator.validate([signal])
        assert len(result.production_signals) == 1
        assert len(result.vague_signals) == 0

    def test_routes_vague_to_vague_log(self):
        validator = SignalValidator()
        signal = _make_cost_change(EvidenceQuality.VAGUE)
        result = validator.validate([signal])
        assert len(result.production_signals) == 0
        assert len(result.vague_signals) == 1

    def test_outlook_uncertainty_bypasses_filter(self):
        validator = SignalValidator()
        signal = _make_outlook_uncertainty(EvidenceQuality.VAGUE)
        result = validator.validate([signal])
        assert len(result.production_signals) == 1
        assert len(result.vague_signals) == 0

    def test_mixed_signals_routed_correctly(self):
        validator = SignalValidator()
        signals = [
            _make_cost_change(EvidenceQuality.EXPLICIT, "s1"),
            _make_cost_change(EvidenceQuality.VAGUE, "s2"),
            _make_outlook_uncertainty(EvidenceQuality.VAGUE, "s3"),
            _make_cost_change(EvidenceQuality.IMPLICIT, "s4"),
        ]
        result = validator.validate(signals)
        assert len(result.production_signals) == 3  # explicit + outlook_uncertainty + implicit
        assert len(result.vague_signals) == 1
