import argparse
import json
import sys
from pathlib import Path

from earnings_call_ingestion.pipeline import Pipeline
from earnings_call_ingestion.transcript_preprocessor import TranscriptPreprocessor
from earnings_call_ingestion.transcript_fetcher import NasdaqFetcher
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
    writer.write_relations(preprocess_result.quarter, result.valid_relations)
    writer.write_signals(preprocess_result.quarter, result.production_signals)
    writer.write_vague_signals(preprocess_result.quarter, result.vague_signals)
    writer.write_review_entries(preprocess_result.quarter, result.review_entries)

    print(
        f"Processed {preprocess_result.transcript.transcript_id}: "
        f"{len(result.valid_relations)} relations, "
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


def _save_transcript_json(transcript) -> Path:
    output_dir = Path("data") / "transcripts"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{transcript.transcript_id}.json"
    path.write_text(json.dumps(transcript.model_dump(indent=2, default=str)), encoding="utf-8")
    print(f"Saved {transcript.transcript_id} to {path}")
    return path


def cmd_fetch(args) -> None:
    fetcher = NasdaqFetcher()
    if args.url:
        transcript = fetcher.fetch_from_url(args.url)
    elif args.text_file:
        if not args.ticker or not args.quarter:
            print("Error: --ticker and --quarter required with --text-file")
            sys.exit(1)
        text = Path(args.text_file).read_text(encoding="utf-8")
        transcript = fetcher.fetch_from_text(text, args.ticker, args.quarter, args.name)
    else:
        print("Error: specify --url or --text-file")
        sys.exit(1)
    _save_transcript_json(transcript)


def cmd_fetch_one(args) -> None:
    fetcher = NasdaqFetcher()
    if args.url:
        transcript = fetcher.fetch_from_url(args.url)
        path = _save_transcript_json(transcript)
    elif args.text_file:
        if not args.ticker or not args.quarter:
            print("Error: --ticker and --quarter required with --text-file")
            sys.exit(1)
        text = Path(args.text_file).read_text(encoding="utf-8")
        transcript = fetcher.fetch_from_text(text, args.ticker, args.quarter, args.name)
        path = _save_transcript_json(transcript)
    else:
        print("Error: specify --url or --text-file")
        sys.exit(1)
    process_one(str(path))


def _add_fetch_arguments(subparser) -> None:
    source_group = subparser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--url", help="Nasdaq article URL")
    source_group.add_argument("--text-file", help="Path to raw transcript text file")
    subparser.add_argument("--ticker", help="Stock ticker (required with --text-file)")
    subparser.add_argument("--quarter", help="Quarter like 2025Q1 (required with --text-file)")
    subparser.add_argument("--name", help="Company name (optional with --text-file)")


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

    fetch_parser = subparsers.add_parser("fetch", help="Fetch a transcript from Nasdaq or text file")
    _add_fetch_arguments(fetch_parser)

    fetch_one_parser = subparsers.add_parser("fetch-one", help="Fetch and process a transcript")
    _add_fetch_arguments(fetch_one_parser)

    args = parser.parse_args()

    if args.command == "process-one":
        process_one(args.file, dry_run=args.dry_run)
    elif args.command == "process":
        process_batch(args.input_dir)
    elif args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "fetch-one":
        cmd_fetch_one(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
