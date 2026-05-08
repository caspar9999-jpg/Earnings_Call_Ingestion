from earnings_call_ingestion.review_collector import ReviewCollector
from earnings_call_ingestion.schemas import ExtractionResult, ReviewEntryType, ReviewReason


class BoundaryOverlapDetector:
    def detect(
        self,
        extraction: ExtractionResult,
        collector: ReviewCollector,
    ) -> None:
        relation_excerpt_map: dict[str, list] = {}
        for rel in extraction.relations:
            excerpt = rel.source.excerpt.strip().lower()
            relation_excerpt_map.setdefault(excerpt, []).append(rel)

        signal_excerpt_map: dict[str, list] = {}
        for sig in extraction.signals:
            excerpt = sig.source.excerpt.strip().lower()
            signal_excerpt_map.setdefault(excerpt, []).append(sig)

        for excerpt in relation_excerpt_map:
            if excerpt in signal_excerpt_map:
                for rel in relation_excerpt_map[excerpt]:
                    collector.add(
                        reason=ReviewReason.BOUNDARY_OVERLAP,
                        entry_type=ReviewEntryType.RELATION,
                        payload=rel.model_dump(),
                    )
                for sig in signal_excerpt_map[excerpt]:
                    collector.add(
                        reason=ReviewReason.BOUNDARY_OVERLAP,
                        entry_type=ReviewEntryType.SIGNAL,
                        payload=sig.model_dump(),
                    )
