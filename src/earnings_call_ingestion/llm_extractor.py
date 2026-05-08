import json
import time
from pathlib import Path

from earnings_call_ingestion.schemas import ExtractionResult


class LLMExtractor:
    def __init__(
        self,
        model=None,
        max_retries: int = 3,
        failures_dir: str = "data/failures",
    ) -> None:
        self._model = model
        self._max_retries = max_retries
        self._failures_dir = Path(failures_dir)

    def _call_llm(self, prompt: str) -> str:
        if self._model is None:
            import google.genai as genai
            import os

            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            return response.text
        else:
            result = self._model.generate_content(prompt)
            return result.text

    def _clean_response(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if line.strip().startswith("```"):
                    lines[i] = ""
            text = "\n".join(lines).strip()
        return text

    def _try_parse(self, text: str) -> ExtractionResult | None:
        text = self._clean_response(text)
        try:
            data = json.loads(text)
            return ExtractionResult(**data)
        except (json.JSONDecodeError, Exception):
            return None

    def extract(self, transcript, prompt: str) -> ExtractionResult:
        last_error = None

        for attempt in range(self._max_retries):
            if attempt > 0:
                time.sleep(2**attempt)

            try:
                response_text = self._call_llm(prompt)
            except Exception as e:
                last_error = e
                continue

            result = self._try_parse(response_text)
            if result is not None:
                return result

            if attempt < self._max_retries - 1:
                repair_prompt = (
                    f"{prompt}\n\nYour previous response was not valid JSON. "
                    "Please return ONLY valid JSON matching the required format."
                )
                try:
                    response_text = self._call_llm(repair_prompt)
                except Exception as e:
                    last_error = e
                    continue

                result = self._try_parse(response_text)
                if result is not None:
                    return result

        self._failures_dir.mkdir(parents=True, exist_ok=True)
        log_path = self._failures_dir / "failed_extractions.jsonl"
        error_detail = str(last_error or "Failed to parse LLM response")
        entry = json.dumps(
            {
                "transcript_id": transcript.transcript_id,
                "error": error_detail,
            }
        )
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry + "\n")

        raise RuntimeError(f"Extraction failed after {self._max_retries} retries: {error_detail}")
