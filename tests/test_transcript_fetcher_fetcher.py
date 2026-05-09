"""Fetcher tests: URL download, text input, error handling."""

from datetime import date
from unittest.mock import Mock

import pytest
import requests

from earnings_call_ingestion.transcript_fetcher.fetcher import NasdaqFetcher
from earnings_call_ingestion.transcript_fetcher.exceptions import TranscriptFetchError, TranscriptNotFoundError


_APPLE_HTML = """<html><body>
<h1>Apple (AAPL) Q1 2025 Earnings Call Transcript</h1>
<p>January 30, 2025</p>
<strong>Prepared Remarks:</strong>
<p>Good afternoon.</p>
</body></html>"""


def _mock_session(status_code: int = 200, text: str = "") -> Mock:
    session = Mock()
    resp = Mock()
    resp.status_code = status_code
    resp.text = text
    resp.raise_for_status = Mock()
    session.get.return_value = resp
    return session


class TestNasdaqFetcher:
    def test_fetch_from_url_returns_transcript(self):
        session = _mock_session(text=_APPLE_HTML)
        fetcher = NasdaqFetcher(session=session)

        result = fetcher.fetch_from_url("https://example.com/apple")

        assert result.company_name == "Apple"
        assert result.company_ticker == "AAPL"
        assert result.quarter == "2025Q1"

    def test_fetch_from_url_raises_on_404(self):
        session = _mock_session(status_code=404)
        fetcher = NasdaqFetcher(session=session)

        with pytest.raises(TranscriptNotFoundError):
            fetcher.fetch_from_url("https://example.com/missing")

    def test_fetch_from_url_raises_on_network_error(self):
        session = _mock_session()
        session.get.side_effect = requests.ConnectionError("no route to host")
        fetcher = NasdaqFetcher(session=session)

        with pytest.raises(TranscriptFetchError):
            fetcher.fetch_from_url("https://example.com/broken")

    def test_fetch_from_text_returns_transcript(self):
        fetcher = NasdaqFetcher()
        result = fetcher.fetch_from_text(
            "This is a raw transcript text.",
            ticker="AAPL",
            quarter="2025Q1",
        )

        assert result.company_ticker == "AAPL"
        assert result.quarter == "2025Q1"
        assert result.transcript_id == "AAPL-2025Q1"
        assert "raw transcript" in result.sections[0].text
        assert len(result.sections) == 1
