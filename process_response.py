import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from earnings_call_ingestion.schemas import ExtractionResult
from earnings_call_ingestion.relation_validator import RelationValidator
from earnings_call_ingestion.review_collector import ReviewCollector
from earnings_call_ingestion.signal_validator import SignalValidator
from earnings_call_ingestion.boundary_overlap import BoundaryOverlapDetector
from earnings_call_ingestion.writer import Writer

response_path = Path(sys.argv[1])
data = json.loads(response_path.read_text(encoding="utf-8"))
extraction = ExtractionResult(**data)

signal_result = SignalValidator().validate(extraction.signals)
collector = ReviewCollector()
valid_relations = RelationValidator().validate(extraction.relations, collector)
BoundaryOverlapDetector().detect(extraction, collector)

quarter = "unknown"
if extraction.relations:
    quarter = extraction.relations[0].transcript_id.split("-")[-1]
elif extraction.signals:
    quarter = extraction.signals[0].transcript_id.split("-")[-1]

writer = Writer()
writer.write_relations(quarter, valid_relations)
writer.write_signals(quarter, signal_result.production_signals)
writer.write_vague_signals(quarter, signal_result.vague_signals)
writer.write_review_entries(quarter, collector.entries)

print(f"Done: {len(valid_relations)} relations, {len(signal_result.production_signals)} signals, {len(collector.entries)} review entries")
