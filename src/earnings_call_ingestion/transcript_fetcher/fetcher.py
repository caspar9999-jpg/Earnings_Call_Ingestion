from datetime import date
from pathlib import Path

import requests

from earnings_call_ingestion.schemas import TranscriptInput, TranscriptSection
from earnings_call_ingestion.transcript_fetcher.exceptions import TranscriptFetchError, TranscriptNotFoundError
from earnings_call_ingestion.transcript_fetcher.parser import NasdaqHtmlParser


class NasdaqFetcher:
    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session or requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        self._parser = NasdaqHtmlParser()

    def fetch_from_url(self, url: str) -> TranscriptInput:
        try:
            resp = self._session.get(url, timeout=30)
        except requests.RequestException as e:
            raise TranscriptFetchError(f"Failed to fetch {url}: {e}") from e

        if resp.status_code == 404:
            raise TranscriptNotFoundError(f"Transcript not found at {url}")
        resp.raise_for_status()

        return self._parser.parse(resp.text)

    def fetch_from_text(
        self,
        text: str,
        ticker: str,
        quarter: str,
        company_name: str | None = None,
    ) -> TranscriptInput:
        transcript_id = f"{ticker}-{quarter}"
        return TranscriptInput(
            transcript_id=transcript_id,
            company_name=company_name or ticker,
            company_ticker=ticker,
            quarter=quarter,
            call_date=date.today(),
            sections=[TranscriptSection(section_type="prepared_remarks", text=text)],
        )
