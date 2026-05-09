from datetime import date
import re

from bs4 import BeautifulSoup

from earnings_call_ingestion.transcript_fetcher.exceptions import TranscriptParseError
from earnings_call_ingestion.schemas import (
    TranscriptInput,
    TranscriptSection,
)


_HEADING_PATTERN = re.compile(
    r"(.+?)\s*\(([A-Z]+)\)\s*Q([1-4])\s+(\d{4})\s+Earnings\s+Call\s+Transcript",
    re.IGNORECASE,
)

_DATE_PATTERN = re.compile(
    r"(\w+)\s+(\d{1,2}),\s*(\d{4})",
)


def _parse_date(text: str) -> date | None:
    m = _DATE_PATTERN.search(text)
    if not m:
        return None
    month = _MONTH_NAMES.get(m.group(1).lower()[:3])
    if month is None:
        return None
    return date(int(m.group(3)), month, int(m.group(2)))


_MONTH_NAMES = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


class NasdaqHtmlParser:
    def parse(self, html: str) -> TranscriptInput:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n")

        m = _HEADING_PATTERN.search(text)
        if not m:
            raise TranscriptParseError("Could not parse transcript heading")

        company_name = m.group(1).strip()
        ticker = m.group(2).upper()
        q = m.group(3)
        year = m.group(4)
        quarter = f"{year}Q{q}"
        transcript_id = f"{ticker}-{quarter}"

        prepared_text = self._extract_section(text, "prepared_remarks")
        qa_text = self._extract_section(text, "q_and_a")

        sections = []
        if prepared_text:
            sections.append(TranscriptSection(
                section_type="prepared_remarks",
                text=prepared_text,
            ))
        if qa_text:
            sections.append(TranscriptSection(
                section_type="q_and_a",
                text=qa_text,
            ))

        return TranscriptInput(
            transcript_id=transcript_id,
            company_name=company_name,
            company_ticker=ticker,
            quarter=quarter,
            call_date=_parse_date(text) or date.today(),
            sections=sections,
        )

    @staticmethod
    def _extract_section(text: str, section_type: str) -> str | None:
        if section_type == "prepared_remarks":
            marker = "Prepared Remarks"
            end_marker = "Questions & Answers"
        else:
            marker = "Questions & Answers"
            end_marker = None

        start = text.find(marker)
        if start == -1:
            return None
        start = text.index("\n", start) + 1

        if end_marker:
            end = text.find(end_marker, start)
            if end == -1:
                return text[start:].strip()
            return text[start:end].strip()
        return text[start:].strip()
