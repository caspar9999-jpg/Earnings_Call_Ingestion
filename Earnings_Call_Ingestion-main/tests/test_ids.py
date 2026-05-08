from earnings_call_ingestion.ids import (
    is_valid_relation_id,
    is_valid_signal_id,
    make_review_id,
)


class TestSignalId:
    def test_valid_signal_id(self):
        assert is_valid_signal_id("AAPL-2025Q1--signal--0001", "AAPL-2025Q1")

    def test_rejects_wrong_prefix(self):
        assert not is_valid_signal_id("AAPL-2025Q1--signal--0001", "MSFT-2025Q1")

    def test_rejects_non_signal_stream(self):
        assert not is_valid_signal_id("AAPL-2025Q1--relation--0001", "AAPL-2025Q1")

    def test_rejects_non_zero_padded_index(self):
        assert not is_valid_signal_id("AAPL-2025Q1--signal--1", "AAPL-2025Q1")

    def test_rejects_missing_index(self):
        assert not is_valid_signal_id("AAPL-2025Q1--signal--", "AAPL-2025Q1")

    def test_rejects_extra_segments(self):
        assert not is_valid_signal_id("AAPL-2025Q1--signal--0001--extra", "AAPL-2025Q1")


class TestRelationId:
    def test_valid_relation_id(self):
        assert is_valid_relation_id("AAPL-2025Q1--relation--0003", "AAPL-2025Q1")

    def test_rejects_signal_stream(self):
        assert not is_valid_relation_id("AAPL-2025Q1--signal--0003", "AAPL-2025Q1")

    def test_rejects_wrong_transcript_id(self):
        assert not is_valid_relation_id("AAPL-2025Q1--relation--0003", "MSFT-2025Q2")

    def test_rejects_non_numeric_index(self):
        assert not is_valid_relation_id("AAPL-2025Q1--relation--abc", "AAPL-2025Q1")


class TestMakeReviewId:
    def test_builds_review_id(self):
        assert make_review_id("r1", "validation_failure") == "r1--validation_failure"

    def test_builds_with_boundary_overlap(self):
        assert make_review_id("s1", "boundary_overlap") == "s1--boundary_overlap"
