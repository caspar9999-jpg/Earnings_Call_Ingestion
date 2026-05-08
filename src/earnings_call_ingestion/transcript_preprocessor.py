import json
from pathlib import Path

from pydantic import ValidationError

from earnings_call_ingestion.schemas import TranscriptInput


class PreprocessingResult:
    def __init__(self, transcript: TranscriptInput, quarter: str) -> None:
        self.transcript = transcript
        self.quarter = quarter


class TranscriptPreprocessor:
    def process(self, file_path: str) -> PreprocessingResult:
        path = Path(file_path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e

        data.pop("_ground_truth", None)

        try:
            transcript = TranscriptInput(**data)
        except ValidationError as e:
            raise ValueError(f"Invalid transcript: {e}") from e

        return PreprocessingResult(transcript=transcript, quarter=transcript.quarter)
