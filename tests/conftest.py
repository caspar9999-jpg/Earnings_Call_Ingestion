from datetime import date

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run integration tests that call the real Gemini API",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-integration"):
        return
    skip_integration = pytest.mark.skip(reason="use --run-integration to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)

from earnings_call_ingestion.schemas import (
    CapacityExpansion,
    ContractModification,
    CostChange,
    DemandShift,
    Entity,
    EntityType,
    EvidenceQuality,
    LogisticsStatusChange,
    MarketPriceShift,
    MatchStatus,
    OutlookUncertainty,
    PriceAdjustment,
    ProductionStatusChange,
    Relation,
    RelationConfidence,
    RelationType,
    SourceReference,
    SupplyStatusChange,
    Temporal,
    TemporalGranularity,
    TranscriptInput,
)


@pytest.fixture
def sample_entity() -> Entity:
    return Entity(name="Acme Corp", type=EntityType.COMPANY)


@pytest.fixture
def sample_source() -> SourceReference:
    return SourceReference(
        section="prepared_remarks",
        speaker="John CEO",
        excerpt="Our input costs increased significantly this quarter.",
    )


@pytest.fixture
def sample_temporal() -> Temporal:
    return Temporal(granularity=TemporalGranularity.QUARTER)


@pytest.fixture
def sample_transcript_input() -> TranscriptInput:
    return TranscriptInput(
        transcript_id="AAPL-2025Q1",
        company_name="Apple Inc.",
        company_ticker="AAPL",
        quarter="2025Q1",
        call_date=date(2025, 1, 30),
        sections=[
            {
                "section_type": "prepared_remarks",
                "speakers": [{"name": "Tim Cook", "role": "ceo"}],
                "text": "This quarter was strong...",
            }
        ],
    )


@pytest.fixture
def sample_extraction_result_data() -> dict:
    return {
        "relations": [
            {
                "relation_id": "AAPL-2025Q1--relation--0001",
                "transcript_id": "AAPL-2025Q1",
                "relation_type": ":SUPPLIES_TO",
                "subject_entity": {"name": "Apple Inc.", "type": "company"},
                "match_status_subject": "unmatched",
                "object_entity": {"name": "Foxconn", "type": "company"},
                "match_status_object": "unmatched",
                "statement": "Foxconn supplies components to Apple.",
                "llm_confidence": "explicit",
                "evidence_quality": "explicit",
                "temporal": {"granularity": "ongoing"},
                "source": {
                    "section": "q_and_a",
                    "speaker": "Analyst",
                    "excerpt": "Foxconn supplies components to Apple.",
                },
            }
        ],
        "signals": [
            {
                "signal_type": "cost_change",
                "signal_id": "AAPL-2025Q1--signal--0001",
                "transcript_id": "AAPL-2025Q1",
                "direction": "increase",
                "subject_entity": {"name": "Apple Inc.", "type": "company"},
                "match_status_subject": "unmatched",
                "statement": "Our input costs increased significantly this quarter.",
                "evidence_quality": "explicit",
                "temporal": {"granularity": "quarter"},
                "source": {
                    "section": "prepared_remarks",
                    "speaker": "Tim Cook",
                    "excerpt": "Our input costs increased significantly this quarter.",
                },
            }
        ],
    }
