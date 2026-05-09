class TranscriptFetchError(Exception):
    """Network or HTTP error during transcript fetching."""


class TranscriptNotFoundError(TranscriptFetchError):
    """Transcript not found at the given URL or source."""


class TranscriptParseError(Exception):
    """Failed to parse transcript HTML into TranscriptInput."""
