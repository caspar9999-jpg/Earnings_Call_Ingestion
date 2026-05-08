from datetime import date

import pytest
from pydantic import ValidationError

from earnings_call_ingestion.schemas import (
    CapacityExpansion,
    ContractModification,
    CostChange,
    DemandShift,
    DirectionCapacityExpansion,
    DirectionContractModification,
    DirectionCostChange,
    DirectionDemandShift,
    DirectionLogisticsStatusChange,
    DirectionMarketPriceShift,
    DirectionPriceAdjustment,
    DirectionProductionStatusChange,
    DirectionSupplyStatusChange,
    Entity,
    EntityType,
    EvidenceQuality,
    ExtractionResult,
    LogisticsStatusChange,
    MarketPriceShift,
    MatchStatus,
    OutlookUncertainty,
    PriceAdjustment,
    ProductionStatusChange,
    Relation,
    RelationConfidence,
    RelationType,
    Signal,
    SourceReference,
    SupplyStatusChange,
    Temporal,
    TemporalGranularity,
    TranscriptInput,
)


class TestEntity:
    def test_constructs(self):
        e = Entity(name="Apple Inc.", type=EntityType.COMPANY)
        assert e.name == "Apple Inc."
        assert e.type == EntityType.COMPANY

    def test_serializes(self):
        e = Entity(name="Widget", type=EntityType.PRODUCT)
        data = e.model_dump()
        assert data == {"name": "Widget", "type": "product"}


class TestTranscriptInput:
    def test_valid_input(self):
        t = TranscriptInput(
            transcript_id="AAPL-2025Q1",
            company_name="Apple Inc.",
            company_ticker="AAPL",
            quarter="2025Q1",
            call_date=date(2025, 1, 30),
            sections=[
                {
                    "section_type": "prepared_remarks",
                    "speakers": [{"name": "Tim Cook", "role": "ceo"}],
                    "text": "This quarter was strong.",
                }
            ],
        )
        assert t.transcript_id == "AAPL-2025Q1"

    def test_rejects_invalid_quarter(self):
        with pytest.raises(ValidationError):
            TranscriptInput(
                transcript_id="TEST",
                company_name="Test",
                company_ticker="TST",
                quarter="2025-Q1",
                call_date=date(2025, 1, 30),
                sections=[],
            )

    def test_rejects_invalid_section_type(self):
        with pytest.raises(ValidationError):
            TranscriptInput(
                transcript_id="TEST",
                company_name="Test",
                company_ticker="TST",
                quarter="2025Q1",
                call_date=date(2025, 1, 30),
                sections=[{"section_type": "summary", "text": "blah"}],
            )


class TestCostChange:
    def test_increase(self):
        s = CostChange(
            signal_id="TST--signal--0001",
            transcript_id="TST-2025Q1",
            direction=DirectionCostChange.INCREASE,
            subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
            match_status_subject=MatchStatus.UNMATCHED,
            statement="Costs went up.",
            evidence_quality=EvidenceQuality.EXPLICIT,
            temporal=Temporal(granularity=TemporalGranularity.QUARTER),
            source=SourceReference(section="prepared_remarks", excerpt="Costs went up."),
        )
        assert s.signal_type == "cost_change"
        assert s.direction == DirectionCostChange.INCREASE

    def test_volatile_populates_intensity(self):
        s = CostChange(
            signal_id="TST--signal--0002",
            transcript_id="TST-2025Q1",
            direction=DirectionCostChange.VOLATILE,
            volatility_intensity="high",
            subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
            match_status_subject=MatchStatus.UNMATCHED,
            statement="Costs are volatile.",
            evidence_quality=EvidenceQuality.IMPLICIT,
            temporal=Temporal(granularity=TemporalGranularity.QUARTER),
            source=SourceReference(section="prepared_remarks", excerpt="Costs are volatile."),
        )
        assert s.volatility_intensity == "high"


class TestPriceAdjustment:
    def test_decrease(self):
        s = PriceAdjustment(
            signal_id="TST--signal--0003",
            transcript_id="TST-2025Q1",
            direction=DirectionPriceAdjustment.DECREASE,
            subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
            match_status_subject=MatchStatus.UNMATCHED,
            statement="We lowered prices.",
            evidence_quality=EvidenceQuality.EXPLICIT,
            temporal=Temporal(granularity=TemporalGranularity.QUARTER),
            source=SourceReference(section="prepared_remarks", excerpt="We lowered prices."),
        )
        assert s.direction == DirectionPriceAdjustment.DECREASE


class TestMarketPriceShift:
    def test_increase(self):
        s = MarketPriceShift(
            signal_id="TST--signal--0004",
            transcript_id="TST-2025Q1",
            direction=DirectionMarketPriceShift.INCREASE,
            subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
            match_status_subject=MatchStatus.UNMATCHED,
            object_entity=Entity(name="Steel", type=EntityType.COMMODITY),
            match_status_object=MatchStatus.UNMATCHED,
            statement="Steel prices rose.",
            evidence_quality=EvidenceQuality.EXPLICIT,
            temporal=Temporal(granularity=TemporalGranularity.QUARTER),
            source=SourceReference(section="prepared_remarks", excerpt="Steel prices rose."),
        )
        assert s.signal_type == "market_price_shift"


class TestProductionStatusChange:
    def test_disruption(self):
        s = ProductionStatusChange(
            signal_id="TST--signal--0005",
            transcript_id="TST-2025Q1",
            direction=DirectionProductionStatusChange.DISRUPTION,
            subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
            match_status_subject=MatchStatus.UNMATCHED,
            statement="Production halted.",
            evidence_quality=EvidenceQuality.EXPLICIT,
            temporal=Temporal(granularity=TemporalGranularity.QUARTER),
            source=SourceReference(section="prepared_remarks", excerpt="Production halted."),
        )
        assert s.signal_type == "production_status_change"


class TestSupplyStatusChange:
    def test_disruption(self):
        s = SupplyStatusChange(
            signal_id="TST--signal--0006",
            transcript_id="TST-2025Q1",
            direction=DirectionSupplyStatusChange.DISRUPTION,
            subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
            match_status_subject=MatchStatus.UNMATCHED,
            statement="Supplier deliveries stopped.",
            evidence_quality=EvidenceQuality.EXPLICIT,
            temporal=Temporal(granularity=TemporalGranularity.QUARTER),
            source=SourceReference(section="prepared_remarks", excerpt="Supplier deliveries stopped."),
        )
        assert s.signal_type == "supply_status_change"

    def test_rejects_invalid_direction(self):
        with pytest.raises(ValidationError):
            SupplyStatusChange(
                signal_id="TST--signal--0007",
                transcript_id="TST-2025Q1",
                direction="increase",
                subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
                match_status_subject=MatchStatus.UNMATCHED,
                statement="Nope.",
                evidence_quality=EvidenceQuality.EXPLICIT,
                temporal=Temporal(granularity=TemporalGranularity.QUARTER),
                source=SourceReference(section="prepared_remarks", excerpt="Nope."),
            )


class TestLogisticsStatusChange:
    def test_recovery(self):
        s = LogisticsStatusChange(
            signal_id="TST--signal--0008",
            transcript_id="TST-2025Q1",
            direction=DirectionLogisticsStatusChange.RECOVERY,
            subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
            match_status_subject=MatchStatus.UNMATCHED,
            statement="Shipping resumed.",
            evidence_quality=EvidenceQuality.EXPLICIT,
            temporal=Temporal(granularity=TemporalGranularity.QUARTER),
            source=SourceReference(section="prepared_remarks", excerpt="Shipping resumed."),
        )
        assert s.signal_type == "logistics_status_change"


class TestCapacityExpansion:
    def test_expansion(self):
        s = CapacityExpansion(
            signal_id="TST--signal--0009",
            transcript_id="TST-2025Q1",
            direction=DirectionCapacityExpansion.EXPANSION,
            subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
            match_status_subject=MatchStatus.UNMATCHED,
            statement="We expanded capacity.",
            evidence_quality=EvidenceQuality.EXPLICIT,
            temporal=Temporal(granularity=TemporalGranularity.QUARTER),
            source=SourceReference(section="prepared_remarks", excerpt="We expanded capacity."),
        )
        assert s.signal_type == "capacity_expansion"


class TestDemandShift:
    def test_decrease(self):
        s = DemandShift(
            signal_id="TST--signal--0010",
            transcript_id="TST-2025Q1",
            direction=DirectionDemandShift.DECREASE,
            subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
            match_status_subject=MatchStatus.UNMATCHED,
            statement="Demand fell.",
            evidence_quality=EvidenceQuality.EXPLICIT,
            temporal=Temporal(granularity=TemporalGranularity.QUARTER),
            source=SourceReference(section="prepared_remarks", excerpt="Demand fell."),
        )
        assert s.signal_type == "demand_shift"


class TestContractModification:
    def test_strengthen(self):
        s = ContractModification(
            signal_id="TST--signal--0011",
            transcript_id="TST-2025Q1",
            direction=DirectionContractModification.STRENGTHEN,
            subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
            match_status_subject=MatchStatus.UNMATCHED,
            statement="We extended our contract.",
            evidence_quality=EvidenceQuality.EXPLICIT,
            temporal=Temporal(granularity=TemporalGranularity.QUARTER),
            source=SourceReference(section="prepared_remarks", excerpt="We extended our contract."),
        )
        assert s.signal_type == "contract_modification"


class TestOutlookUncertainty:
    def test_direction_is_none(self):
        s = OutlookUncertainty(
            signal_id="TST--signal--0012",
            transcript_id="TST-2025Q1",
            subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
            match_status_subject=MatchStatus.UNMATCHED,
            statement="Outlook is uncertain.",
            evidence_quality=EvidenceQuality.EXPLICIT,
            temporal=Temporal(granularity=TemporalGranularity.FORWARD_LOOKING),
            source=SourceReference(
                section="prepared_remarks", excerpt="We cannot predict future demand."
            ),
        )
        assert s.direction is None

    def test_serializes_direction_as_null(self):
        s = OutlookUncertainty(
            signal_id="TST--signal--0013",
            transcript_id="TST-2025Q1",
            subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
            match_status_subject=MatchStatus.UNMATCHED,
            statement="Uncertain.",
            evidence_quality=EvidenceQuality.EXPLICIT,
            temporal=Temporal(granularity=TemporalGranularity.FORWARD_LOOKING),
            source=SourceReference(section="prepared_remarks", excerpt="Uncertain."),
        )
        data = s.model_dump(by_alias=True)
        assert data["direction"] is None


class TestSignalDiscriminatedUnion:
    def test_cost_change_dispatch(self):
        signal: Signal = CostChange(
            signal_id="TST--signal--0001",
            transcript_id="TST-2025Q1",
            direction=DirectionCostChange.INCREASE,
            subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
            match_status_subject=MatchStatus.UNMATCHED,
            statement="Costs up.",
            evidence_quality=EvidenceQuality.EXPLICIT,
            temporal=Temporal(granularity=TemporalGranularity.QUARTER),
            source=SourceReference(section="prepared_remarks", excerpt="Costs up."),
        )
        assert signal.signal_type == "cost_change"

    def test_outlook_uncertainty_dispatch(self):
        signal: Signal = OutlookUncertainty(
            signal_id="TST--signal--0012",
            transcript_id="TST-2025Q1",
            subject_entity=Entity(name="Acme", type=EntityType.COMPANY),
            match_status_subject=MatchStatus.UNMATCHED,
            statement="Uncertain.",
            evidence_quality=EvidenceQuality.EXPLICIT,
            temporal=Temporal(granularity=TemporalGranularity.FORWARD_LOOKING),
            source=SourceReference(section="prepared_remarks", excerpt="Uncertain."),
        )
        assert signal.signal_type == "outlook_uncertainty"


class TestRelation:
    def test_constructs(self):
        r = Relation(
            relation_id="TST--relation--0001",
            transcript_id="TST-2025Q1",
            relation_type=RelationType.SUPPLIES_TO,
            subject_entity=Entity(name="Apple", type=EntityType.COMPANY),
            match_status_subject=MatchStatus.UNMATCHED,
            object_entity=Entity(name="Foxconn", type=EntityType.COMPANY),
            match_status_object=MatchStatus.UNMATCHED,
            statement="Foxconn supplies Apple.",
            llm_confidence=RelationConfidence.EXPLICIT,
            evidence_quality=EvidenceQuality.EXPLICIT,
            temporal=Temporal(granularity=TemporalGranularity.ONGOING),
            source=SourceReference(
                section="prepared_remarks",
                speaker="Tim Cook",
                excerpt="Foxconn supplies Apple.",
            ),
        )
        assert r.relation_type == RelationType.SUPPLIES_TO

    def test_serializes(self):
        r = Relation(
            relation_id="TST--relation--0001",
            transcript_id="TST-2025Q1",
            relation_type=RelationType.PROVIDES,
            subject_entity=Entity(name="Apple", type=EntityType.COMPANY),
            match_status_subject=MatchStatus.UNMATCHED,
            object_entity=Entity(name="iPhones", type=EntityType.PRODUCT),
            match_status_object=MatchStatus.UNMATCHED,
            statement="Apple provides iPhones.",
            llm_confidence=RelationConfidence.EXPLICIT,
            evidence_quality=EvidenceQuality.EXPLICIT,
            temporal=Temporal(granularity=TemporalGranularity.ONGOING),
            source=SourceReference(section="prepared_remarks", excerpt="Apple provides iPhones."),
        )
        data = r.model_dump()
        assert data["relation_type"] == ":PROVIDES"

    def test_termination_flag_defaults_to_false(self):
        r = Relation(
            relation_id="TST--relation--0002",
            transcript_id="TST-2025Q1",
            relation_type=RelationType.SUPPLIES_TO,
            subject_entity=Entity(name="Apple", type=EntityType.COMPANY),
            match_status_subject=MatchStatus.UNMATCHED,
            object_entity=Entity(name="Foxconn", type=EntityType.COMPANY),
            match_status_object=MatchStatus.UNMATCHED,
            statement="Foxconn supplies Apple.",
            llm_confidence=RelationConfidence.EXPLICIT,
            evidence_quality=EvidenceQuality.EXPLICIT,
            temporal=Temporal(granularity=TemporalGranularity.ONGOING),
            source=SourceReference(section="prepared_remarks", excerpt="Foxconn supplies Apple."),
        )
        assert r.is_termination is False


class TestExtractionResult:
    def test_empty_result(self):
        result = ExtractionResult()
        assert result.relations == []
        assert result.signals == []

    def test_with_relations_and_signals(self, sample_extraction_result_data):
        result = ExtractionResult(**sample_extraction_result_data)
        assert len(result.relations) == 1
        assert len(result.signals) == 1
        assert result.relations[0].relation_type == RelationType.SUPPLIES_TO

    def test_serialization_roundtrip(self, sample_extraction_result_data):
        result = ExtractionResult(**sample_extraction_result_data)
        data = result.model_dump()
        restored = ExtractionResult(**data)
        assert len(restored.relations) == 1
        assert restored.relations[0].relation_id == "AAPL-2025Q1--relation--0001"
        assert restored.signals[0].signal_type == "cost_change"
