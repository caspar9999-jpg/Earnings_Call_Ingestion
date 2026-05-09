from earnings_call_ingestion.review_collector import ReviewCollector
from earnings_call_ingestion.schemas import (
    MatchStatus,
    Relation,
    RelationConfidence,
    RelationType,
    ReviewEntryType,
    ReviewReason,
)


class RelationValidator:
    def validate(
        self, relations: list[Relation], collector: ReviewCollector
    ) -> list[Relation]:
        valid: list[Relation] = []

        for rel in relations:
            if rel.subject_entity.name == rel.object_entity.name:
                collector.add(
                    reason=ReviewReason.VALIDATION_FAILURE,
                    entry_type=ReviewEntryType.RELATION,
                    payload=rel.model_dump(),
                )
                continue

            if rel.llm_confidence is None:
                collector.add(
                    reason=ReviewReason.VALIDATION_FAILURE,
                    entry_type=ReviewEntryType.RELATION,
                    payload=rel.model_dump(),
                )
                continue

            valid.append(rel)
            self._check_review_triggers(rel, collector)

        return valid

    def _check_review_triggers(
        self, rel: Relation, collector: ReviewCollector
    ) -> None:
        reasons: list[ReviewReason] = []

        if (
            rel.match_status_subject == MatchStatus.UNMATCHED
            or rel.match_status_object == MatchStatus.UNMATCHED
        ):
            reasons.append(ReviewReason.UNMATCHED_ENTITY)

        if rel.llm_confidence == RelationConfidence.SPECULATIVE:
            reasons.append(ReviewReason.LOW_CONFIDENCE)

        if rel.relation_type == RelationType.USED_IN:
            reasons.append(ReviewReason.CANDIDATE_USED_IN)

        for reason in reasons:
            collector.add(
                reason=reason,
                entry_type=ReviewEntryType.RELATION,
                payload=rel.model_dump(),
            )
