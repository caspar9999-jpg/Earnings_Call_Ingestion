from earnings_call_ingestion.review_collector import ReviewCollector
from earnings_call_ingestion.schemas import ReviewEntryType, ReviewReason


class TestReviewCollector:
    def test_builds_review_entry_from_signal_payload(self):
        collector = ReviewCollector()
        entry = collector.add(
            reason=ReviewReason.BOUNDARY_OVERLAP,
            entry_type=ReviewEntryType.SIGNAL,
            payload={
                "signal_id": "TST--signal--0001",
                "transcript_id": "TST-2025Q1",
                "signal_type": "cost_change",
            },
        )
        assert entry.review_id == "TST--signal--0001--boundary_overlap"
        assert entry.transcript_id == "TST-2025Q1"
        assert entry.review_reason == ReviewReason.BOUNDARY_OVERLAP
        assert entry.entry_type == ReviewEntryType.SIGNAL

    def test_builds_review_entry_from_relation_payload(self):
        collector = ReviewCollector()
        entry = collector.add(
            reason=ReviewReason.VALIDATION_FAILURE,
            entry_type=ReviewEntryType.RELATION,
            payload={
                "relation_id": "TST--relation--0003",
                "transcript_id": "TST-2025Q1",
            },
        )
        assert entry.review_id == "TST--relation--0003--validation_failure"
        assert entry.transcript_id == "TST-2025Q1"

    def test_accumulates_multiple_entries(self):
        collector = ReviewCollector()
        collector.add(
            reason=ReviewReason.UNMATCHED_ENTITY,
            entry_type=ReviewEntryType.RELATION,
            payload={"relation_id": "r1", "transcript_id": "TST-2025Q1"},
        )
        collector.add(
            reason=ReviewReason.LOW_CONFIDENCE,
            entry_type=ReviewEntryType.RELATION,
            payload={"relation_id": "r2", "transcript_id": "TST-2025Q1"},
        )
        collector.add(
            reason=ReviewReason.BOUNDARY_OVERLAP,
            entry_type=ReviewEntryType.SIGNAL,
            payload={"signal_id": "s1", "transcript_id": "TST-2025Q1"},
        )
        assert len(collector.entries) == 3

    def test_entries_returns_copy(self):
        collector = ReviewCollector()
        collector.add(
            reason=ReviewReason.UNMATCHED_ENTITY,
            entry_type=ReviewEntryType.RELATION,
            payload={"relation_id": "r1", "transcript_id": "TST-2025Q1"},
        )
        entries = collector.entries
        entries.clear()
        assert len(collector.entries) == 1

    def test_uses_unknown_transcript_id_when_missing(self):
        collector = ReviewCollector()
        entry = collector.add(
            reason=ReviewReason.UNMATCHED_ENTITY,
            entry_type=ReviewEntryType.RELATION,
            payload={"relation_id": "r1"},
        )
        assert entry.transcript_id == "unknown"
