from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────────

class EntityType(str, Enum):
    COMPANY = "company"
    PRODUCT = "product"
    COMMODITY = "commodity"
    SERVICE = "service"
    DIVISION = "division"


class EvidenceQuality(str, Enum):
    EXPLICIT = "explicit"
    IMPLICIT = "implicit"
    VAGUE = "vague"


class MatchStatus(str, Enum):
    MATCHED = "matched"
    UNMATCHED = "unmatched"
    NOT_APPLICABLE = "not_applicable"


class TemporalGranularity(str, Enum):
    EXACT_DATE = "exact_date"
    QUARTER = "quarter"
    HALF = "half"
    YEAR = "year"
    RELATIVE = "relative"
    ONGOING = "ongoing"
    FORWARD_LOOKING = "forward_looking"


class VolatilityIntensity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class DurationUnit(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class DirectionCostChange(str, Enum):
    INCREASE = "increase"
    DECREASE = "decrease"
    VOLATILE = "volatile"


class DirectionPriceAdjustment(str, Enum):
    INCREASE = "increase"
    DECREASE = "decrease"
    VOLATILE = "volatile"


class DirectionMarketPriceShift(str, Enum):
    INCREASE = "increase"
    DECREASE = "decrease"
    VOLATILE = "volatile"


class DirectionProductionStatusChange(str, Enum):
    DISRUPTION = "disruption"
    RECOVERY = "recovery"
    INCREASE = "increase"
    DECREASE = "decrease"
    VOLATILE = "volatile"


class DirectionSupplyStatusChange(str, Enum):
    DISRUPTION = "disruption"
    RECOVERY = "recovery"


class DirectionLogisticsStatusChange(str, Enum):
    DISRUPTION = "disruption"
    RECOVERY = "recovery"


class DirectionCapacityExpansion(str, Enum):
    EXPANSION = "expansion"
    CONTRACTION = "contraction"


class DirectionDemandShift(str, Enum):
    INCREASE = "increase"
    DECREASE = "decrease"


class DirectionContractModification(str, Enum):
    STRENGTHEN = "strengthen"
    WEAKEN = "weaken"
    MODIFY = "modify"


# ── Shared Sub-Models ────────────────────────────────────────────────────────

class Entity(BaseModel):
    name: str = Field(description="Entity name as it appears in the transcript")
    type: EntityType


class SourceReference(BaseModel):
    section: Literal["prepared_remarks", "q_and_a"]
    speaker: Optional[str] = None
    excerpt: str = Field(description="Verbatim sentence or phrase from the transcript")


class Temporal(BaseModel):
    granularity: TemporalGranularity
    start: Optional[date] = None
    end: Optional[date] = None
    duration: Optional[Duration] = None


class Duration(BaseModel):
    value: float
    unit: DurationUnit


# ── Signal Variants (discriminated union) ────────────────────────────────────

class CostChange(BaseModel):
    signal_type: Literal["cost_change"] = "cost_change"
    signal_id: str
    transcript_id: str
    direction: DirectionCostChange
    volatility_intensity: Optional[VolatilityIntensity] = Field(
        default=None,
        description="Only populated when direction is 'volatile'",
    )
    subject_entity: Entity
    match_status_subject: MatchStatus
    object_entity: Optional[Entity] = Field(
        default=None,
        description="The specific input/material whose cost changed, if named",
    )
    match_status_object: MatchStatus = MatchStatus.NOT_APPLICABLE
    statement: str = Field(description="The sentence(s) from which this signal was extracted")
    evidence_quality: EvidenceQuality
    magnitude: Optional[str] = Field(
        default=None,
        description="Raw text snippet describing magnitude (e.g. 'up 15%', 'nearly doubled')",
    )
    temporal: Temporal
    source: SourceReference


class PriceAdjustment(BaseModel):
    signal_type: Literal["price_adjustment"] = "price_adjustment"
    signal_id: str
    transcript_id: str
    direction: DirectionPriceAdjustment
    volatility_intensity: Optional[VolatilityIntensity] = Field(
        default=None,
        description="Only populated when direction is 'volatile'",
    )
    subject_entity: Entity
    match_status_subject: MatchStatus
    object_entity: Optional[Entity] = Field(
        default=None,
        description="The product/service whose price was adjusted, if named",
    )
    match_status_object: MatchStatus = MatchStatus.NOT_APPLICABLE
    statement: str
    evidence_quality: EvidenceQuality
    magnitude: Optional[str] = None
    temporal: Temporal
    source: SourceReference


class MarketPriceShift(BaseModel):
    signal_type: Literal["market_price_shift"] = "market_price_shift"
    signal_id: str
    transcript_id: str
    direction: DirectionMarketPriceShift
    volatility_intensity: Optional[VolatilityIntensity] = Field(
        default=None,
        description="Only populated when direction is 'volatile'",
    )
    subject_entity: Entity
    match_status_subject: MatchStatus
    object_entity: Optional[Entity] = Field(
        default=None,
        description="The commodity/benchmark/index that shifted",
    )
    match_status_object: MatchStatus = MatchStatus.NOT_APPLICABLE
    statement: str
    evidence_quality: EvidenceQuality
    magnitude: Optional[str] = None
    temporal: Temporal
    source: SourceReference


class ProductionStatusChange(BaseModel):
    signal_type: Literal["production_status_change"] = "production_status_change"
    signal_id: str
    transcript_id: str
    direction: DirectionProductionStatusChange
    volatility_intensity: Optional[VolatilityIntensity] = Field(
        default=None,
        description="Only populated when direction is 'volatile'",
    )
    subject_entity: Entity
    match_status_subject: MatchStatus
    object_entity: Optional[Entity] = Field(
        default=None,
        description="The product/facility whose production status changed",
    )
    match_status_object: MatchStatus = MatchStatus.NOT_APPLICABLE
    statement: str
    evidence_quality: EvidenceQuality
    magnitude: Optional[str] = None
    temporal: Temporal
    source: SourceReference


class SupplyStatusChange(BaseModel):
    signal_type: Literal["supply_status_change"] = "supply_status_change"
    signal_id: str
    transcript_id: str
    direction: DirectionSupplyStatusChange
    subject_entity: Entity
    match_status_subject: MatchStatus
    object_entity: Optional[Entity] = Field(
        default=None,
        description="The supplier whose delivery status changed",
    )
    match_status_object: MatchStatus = MatchStatus.NOT_APPLICABLE
    statement: str
    evidence_quality: EvidenceQuality
    magnitude: Optional[str] = None
    temporal: Temporal
    source: SourceReference


class LogisticsStatusChange(BaseModel):
    signal_type: Literal["logistics_status_change"] = "logistics_status_change"
    signal_id: str
    transcript_id: str
    direction: DirectionLogisticsStatusChange
    subject_entity: Entity
    match_status_subject: MatchStatus
    object_entity: Optional[Entity] = Field(
        default=None,
        description="The logistics channel/route/partner affected",
    )
    match_status_object: MatchStatus = MatchStatus.NOT_APPLICABLE
    statement: str
    evidence_quality: EvidenceQuality
    magnitude: Optional[str] = None
    temporal: Temporal
    source: SourceReference


class CapacityExpansion(BaseModel):
    signal_type: Literal["capacity_expansion"] = "capacity_expansion"
    signal_id: str
    transcript_id: str
    direction: DirectionCapacityExpansion
    subject_entity: Entity
    match_status_subject: MatchStatus
    object_entity: Optional[Entity] = Field(
        default=None,
        description="The product/facility/line whose capacity changed",
    )
    match_status_object: MatchStatus = MatchStatus.NOT_APPLICABLE
    statement: str
    evidence_quality: EvidenceQuality
    magnitude: Optional[str] = None
    temporal: Temporal
    source: SourceReference


class DemandShift(BaseModel):
    signal_type: Literal["demand_shift"] = "demand_shift"
    signal_id: str
    transcript_id: str
    direction: DirectionDemandShift
    subject_entity: Entity
    match_status_subject: MatchStatus
    object_entity: Optional[Entity] = Field(
        default=None,
        description="The product/market segment experiencing demand shift",
    )
    match_status_object: MatchStatus = MatchStatus.NOT_APPLICABLE
    statement: str
    evidence_quality: EvidenceQuality
    magnitude: Optional[str] = None
    temporal: Temporal
    source: SourceReference


class ContractModification(BaseModel):
    signal_type: Literal["contract_modification"] = "contract_modification"
    signal_id: str
    transcript_id: str
    direction: DirectionContractModification
    subject_entity: Entity
    match_status_subject: MatchStatus
    object_entity: Optional[Entity] = Field(
        default=None,
        description="The counterparty or contract that was modified",
    )
    match_status_object: MatchStatus = MatchStatus.NOT_APPLICABLE
    statement: str
    evidence_quality: EvidenceQuality
    magnitude: Optional[str] = None
    temporal: Temporal
    source: SourceReference


class OutlookUncertainty(BaseModel):
    signal_type: Literal["outlook_uncertainty"] = "outlook_uncertainty"
    signal_id: str
    transcript_id: str
    direction: None = Field(
        default=None,
        description="Always null for outlook_uncertainty signals",
        validate_default=True,
        serialization_alias="direction",
    )
    subject_entity: Entity
    match_status_subject: MatchStatus
    object_entity: Optional[Entity] = Field(
        default=None,
        description="The area/subject of uncertainty, if named",
    )
    match_status_object: MatchStatus = MatchStatus.NOT_APPLICABLE
    statement: str
    evidence_quality: EvidenceQuality
    magnitude: Optional[str] = None
    temporal: Temporal
    source: SourceReference


Signal = Annotated[
    Union[
        CostChange,
        PriceAdjustment,
        MarketPriceShift,
        ProductionStatusChange,
        SupplyStatusChange,
        LogisticsStatusChange,
        CapacityExpansion,
        DemandShift,
        ContractModification,
        OutlookUncertainty,
    ],
    Field(discriminator="signal_type"),
]


# ── Relation Output ──────────────────────────────────────────────────────────

class RelationConfidence(str, Enum):
    EXPLICIT = "explicit"
    IMPLICIT = "implicit"
    SPECULATIVE = "speculative"


class RelationType(str, Enum):
    PROVIDES = ":PROVIDES"
    SUPPLIES_TO = ":SUPPLIES_TO"
    USED_IN = ":USED_IN"


class Relation(BaseModel):
    relation_id: str
    transcript_id: str
    relation_type: RelationType
    subject_entity: Entity
    match_status_subject: MatchStatus
    object_entity: Entity
    match_status_object: MatchStatus
    statement: str
    llm_confidence: Optional[RelationConfidence] = Field(
        default=None,
        description="LLM-assigned confidence (NEVER 'confirmed' — that requires human review). None if not provided.",
    )
    evidence_quality: EvidenceQuality
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    is_termination: bool = Field(
        default=False,
        description="True if the statement describes ending an existing relationship",
    )
    temporal: Temporal
    source: SourceReference


# ── Dual-Stream LLM Response ─────────────────────────────────────────────────

class ExtractionResult(BaseModel):
    relations: list[Relation] = Field(default_factory=list)
    signals: list[Signal] = Field(default_factory=list)


# ── Review Queue ──────────────────────────────────────────────────────────────

class ReviewReason(str, Enum):
    UNMATCHED_ENTITY = "unmatched_entity"
    LOW_CONFIDENCE = "low_confidence"
    BOUNDARY_OVERLAP = "boundary_overlap"
    CANDIDATE_USED_IN = "candidate_used_in"
    VALIDATION_FAILURE = "validation_failure"


class ReviewEntryType(str, Enum):
    SIGNAL = "signal"
    RELATION = "relation"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReviewEntry(BaseModel):
    review_id: str
    transcript_id: str
    review_reason: ReviewReason
    entry_type: ReviewEntryType
    payload: dict
    review_status: ReviewStatus = ReviewStatus.PENDING
    reviewer_notes: Optional[str] = None
    flagged_at: str = Field(default_factory=lambda: date.today().isoformat())


# ── Canonical Transcript Input ───────────────────────────────────────────────

class Speaker(BaseModel):
    name: str
    role: Literal["ceo", "cfo", "coo", "analyst", "executive", "operator", "other"]


class TranscriptSection(BaseModel):
    section_type: Literal["prepared_remarks", "q_and_a"]
    speakers: list[Speaker] = Field(default_factory=list)
    text: str


class TranscriptInput(BaseModel):
    transcript_id: str
    company_name: str
    company_ticker: str
    quarter: str = Field(pattern=r"^\d{4}Q[1-4]$")
    call_date: date
    sections: list[TranscriptSection]
