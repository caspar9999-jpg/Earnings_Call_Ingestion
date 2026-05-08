import argparse
import json
import sys
from pathlib import Path

from earnings_call_ingestion.pipeline import Pipeline
from earnings_call_ingestion.transcript_preprocessor import TranscriptPreprocessor
from earnings_call_ingestion.writer import Writer


def process_one(transcript_path: str, dry_run: bool = False, writer: Writer | None = None) -> None:
    preprocessor = TranscriptPreprocessor()
    preprocess_result = preprocessor.process(transcript_path)

    pipeline = Pipeline()
    result = pipeline.run(preprocess_result.transcript, preprocess_result.quarter)

    if dry_run:
        print(json.dumps(result.extraction.model_dump(), indent=2))
        return

    if writer is None:
        writer = Writer()
    writer.write_signals(preprocess_result.quarter, result.production_signals)
    writer.write_vague_signals(preprocess_result.quarter, result.vague_signals)
    writer.write_review_entries(preprocess_result.quarter, result.review_entries)

    print(
        f"Processed {preprocess_result.transcript.transcript_id}: "
        f"{len(result.production_signals)} signals, {len(result.vague_signals)} vague, "
        f"{len(result.review_entries)} review entries"
    )


def process_batch(input_dir: str) -> dict:
    succeeded = 0
    failed = 0
    json_files = sorted(Path(input_dir).glob("*.json"))
    total = len(json_files)

    writer = Writer()

    for i, path in enumerate(json_files, 1):
        transcript_id = path.stem
        try:
            print(f"[{i}/{total}] Processing {transcript_id}... ", end="")
            sys.stdout.flush()
            process_one(str(path), writer=writer)
            succeeded += 1
            print("done")
        except Exception as e:
            print(f"FAILED: {e}")
            failed += 1

    print(f"Processed {succeeded}/{total} transcripts. {failed} failures.")
    return {"succeeded": succeeded, "failed": failed}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Supply Chain Signal Extractor — Earnings Call Ingestion Pipeline"
    )
    subparsers = parser.add_subparsers(dest="command")

    one_parser = subparsers.add_parser("process-one", help="Process a single transcript")
    one_parser.add_argument("file", help="Path to transcript JSON file")
    one_parser.add_argument("--dry-run", action="store_true", help="Print result without writing to storage")

    batch_parser = subparsers.add_parser("process", help="Process a directory of transcripts")
    batch_parser.add_argument("input_dir", help="Directory containing transcript JSON files")

    args = parser.parse_args()

    if args.command == "process-one":
        process_one(args.file, dry_run=args.dry_run)
    elif args.command == "process":
        process_batch(args.input_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
