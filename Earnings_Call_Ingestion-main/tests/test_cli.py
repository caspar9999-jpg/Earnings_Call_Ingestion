import json

from earnings_call_ingestion.cli import process_batch, process_one


class TestProcessOne:
    def test_dry_run_prints_to_stdout(self, tmp_path, capsys, monkeypatch):
        transcript = {
            "transcript_id": "TST-2025Q1",
            "company_name": "Test",
            "company_ticker": "TST",
            "quarter": "2025Q1",
            "call_date": "2025-01-01",
            "sections": [],
        }
        transcript_path = tmp_path / "transcript.json"
        transcript_path.write_text(json.dumps(transcript))

        from earnings_call_ingestion.pipeline import Pipeline
        from earnings_call_ingestion.schemas import ExtractionResult

        def mock_run(self, transcript, quarter):
            return type(
                "PipelineResult",
                (),
                {
                    "extraction": ExtractionResult(),
                    "production_signals": [],
                    "vague_signals": [],
                    "review_entries": [],
                },
            )()

        monkeypatch.setattr(Pipeline, "run", mock_run)

        process_one(str(transcript_path), dry_run=True)
        captured = capsys.readouterr()
        assert "ExtractionResult" in captured.out or "relations" in captured.out


class TestProcessBatch:
    def test_processes_all_json_files_in_directory(self, tmp_path, monkeypatch):
        transcripts = [
            {"transcript_id": "T1", "company_name": "A", "company_ticker": "A", "quarter": "2025Q1", "call_date": "2025-01-01", "sections": []},
            {"transcript_id": "T2", "company_name": "B", "company_ticker": "B", "quarter": "2025Q1", "call_date": "2025-01-01", "sections": []},
        ]
        for i, t in enumerate(transcripts):
            (tmp_path / f"transcript_{i}.json").write_text(json.dumps(t))
        (tmp_path / "readme.txt").write_text("not a json")

        processed = []

        def mock_process_one(path, dry_run=False, writer=None):
            processed.append(str(path))

        monkeypatch.setattr("earnings_call_ingestion.cli.process_one", mock_process_one)

        process_batch(str(tmp_path))
        assert len(processed) == 2

    def test_continues_on_failure(self, tmp_path, monkeypatch):
        (tmp_path / "good.json").write_text(json.dumps({"transcript_id": "T1", "company_name": "A", "company_ticker": "A", "quarter": "2025Q1", "call_date": "2025-01-01", "sections": []}))
        (tmp_path / "bad.json").write_text("not json")

        processed = []

        def mock_process_one(path, dry_run=False, writer=None):
            processed.append(str(path))
            if "bad" in str(path):
                raise ValueError("failed")

        monkeypatch.setattr("earnings_call_ingestion.cli.process_one", mock_process_one)

        result = process_batch(str(tmp_path))
        assert result["succeeded"] == 1
        assert result["failed"] == 1

    def test_prints_progress_summary(self, tmp_path, capsys, monkeypatch):
        (tmp_path / "t.json").write_text(json.dumps({"transcript_id": "T1", "company_name": "A", "company_ticker": "A", "quarter": "2025Q1", "call_date": "2025-01-01", "sections": []}))

        def mock_process_one(path, dry_run=False, writer=None):
            pass

        monkeypatch.setattr("earnings_call_ingestion.cli.process_one", mock_process_one)

        process_batch(str(tmp_path))
        captured = capsys.readouterr()
        assert "succeeded" in captured.out.lower() or "processed" in captured.out.lower()
