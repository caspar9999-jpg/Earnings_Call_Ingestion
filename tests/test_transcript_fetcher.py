"""Parser tests: extract TranscriptInput from Nasdaq/Motley Fool HTML."""

from datetime import date

from earnings_call_ingestion.transcript_fetcher.parser import NasdaqHtmlParser
from earnings_call_ingestion.schemas import TranscriptInput


_APPLE_HTML = """
<html><body>
<h1>Apple (AAPL) Q1 2025 Earnings Call Transcript</h1>
<p>January 30, 2025 &mdash; 05:00 PM EST</p>
<h2>Prepared Remarks:</h2>
<p>Good afternoon and welcome to the Apple Q1 fiscal year 2025 earnings conference call.</p>
<p><strong>Questions & Answers:</strong></p>
<p>We will now begin the question-and-answer session.</p>
</body></html>
"""


class TestNasdaqHtmlParser:
    def test_extracts_metadata_from_minimal_html(self):
        parser = NasdaqHtmlParser()
        result = parser.parse(_APPLE_HTML)

        assert isinstance(result, TranscriptInput)
        assert result.company_name == "Apple"
        assert result.company_ticker == "AAPL"
        assert result.quarter == "2025Q1"
        assert result.transcript_id == "AAPL-2025Q1"

    def test_extracts_call_date(self):
        parser = NasdaqHtmlParser()
        result = parser.parse(_APPLE_HTML)

        assert result.call_date == date(2025, 1, 30)

    def test_splits_into_prepared_and_qa_sections(self):
        parser = NasdaqHtmlParser()
        result = parser.parse(_APPLE_HTML)

        assert len(result.sections) == 2
        assert result.sections[0].section_type == "prepared_remarks"
        assert result.sections[1].section_type == "q_and_a"
        assert "Good afternoon" in result.sections[0].text
        assert "question-and-answer" in result.sections[1].text

    def test_handles_no_qa_section(self):
        html = """
        <html><body>
        <h1>Tesla (TSLA) Q4 2024 Earnings Call Transcript</h1>
        <p>January 29, 2025</p>
        <strong>Prepared Remarks:</strong>
        <p>Elon Musk spoke about autonomy.</p>
        </body></html>
        """
        parser = NasdaqHtmlParser()
        result = parser.parse(html)

        assert len(result.sections) == 1
        assert result.sections[0].section_type == "prepared_remarks"
        assert "autonomy" in result.sections[0].text

    def test_raises_on_malformed_html(self):
        from earnings_call_ingestion.transcript_fetcher.exceptions import TranscriptParseError

        parser = NasdaqHtmlParser()
        try:
            parser.parse("<html><body><p>No heading here</p></body></html>")
            assert False, "Expected TranscriptParseError"
        except TranscriptParseError:
            pass
