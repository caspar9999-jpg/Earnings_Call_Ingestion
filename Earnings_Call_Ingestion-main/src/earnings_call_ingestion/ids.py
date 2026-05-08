import re

_SIGNAL_ID_PATTERN = re.compile(r"^(.+)--signal--(\d{4})$")
_RELATION_ID_PATTERN = re.compile(r"^(.+)--relation--(\d{4})$")


def is_valid_signal_id(signal_id: str, transcript_id: str) -> bool:
    m = _SIGNAL_ID_PATTERN.match(signal_id)
    if not m:
        return False
    return m.group(1) == transcript_id


def is_valid_relation_id(relation_id: str, transcript_id: str) -> bool:
    m = _RELATION_ID_PATTERN.match(relation_id)
    if not m:
        return False
    return m.group(1) == transcript_id


def make_review_id(parent_id: str, reason: str) -> str:
    return f"{parent_id}--{reason}"
