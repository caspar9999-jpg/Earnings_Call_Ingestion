from earnings_call_ingestion.ids import make_review_id
from earnings_call_ingestion.schemas import ReviewEntry, ReviewEntryType, ReviewReason


class ReviewCollector:
    def __init__(self) -> None:
        self._entries: list[ReviewEntry] = []

    @property
    def entries(self) -> list[ReviewEntry]:
        return list(self._entries)

    def add(
        self,
        *,
        reason: ReviewReason,
        entry_type: ReviewEntryType,
        payload: dict,
    ) -> ReviewEntry:
        parent_id = payload.get("signal_id") or payload.get("relation_id")
        transcript_id = payload.get("transcript_id", "unknown")

        entry = ReviewEntry(
            review_id=make_review_id(parent_id, reason.value),
            transcript_id=transcript_id,
            review_reason=reason,
            entry_type=entry_type,
            payload=payload,
        )
        self._entries.append(entry)
        return entry
