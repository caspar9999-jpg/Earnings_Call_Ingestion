"""Validate synthetic transcripts: check that ground truth entries match transcript text."""
import json
import os
import sys
from pathlib import Path


TRANSCRIPT_DIR = Path("data/synthetic_transcripts")

VALID_SIGNAL_TYPES = {
    "cost_change", "price_adjustment", "market_price_shift",
    "production_status_change", "supply_status_change",
    "logistics_status_change", "capacity_expansion",
    "demand_shift", "contract_modification", "outlook_uncertainty",
}

VALID_RELATION_TYPES = {":PROVIDES", ":SUPPLIES_TO", ":USED_IN"}


def get_all_transcript_text(transcript: dict) -> str:
    return " ".join(s["text"] for s in transcript.get("sections", []))


def get_section_for_excerpt(transcript: dict, excerpt: str) -> str | None:
    excerpt_lower = excerpt.strip().lower()
    for section in transcript.get("sections", []):
        if excerpt_lower in section["text"].lower():
            return section["section_type"]
    return None


def check_transcript(filepath: Path) -> list[str]:
    errors = []
    data = json.loads(filepath.read_text(encoding="utf-8"))
    gt = data.get("_ground_truth", {})
    full_text = get_all_transcript_text(data)

    # Check signals
    for i, signal in enumerate(gt.get("signals", [])):
        st = signal.get("signal_type")
        if st not in VALID_SIGNAL_TYPES:
            errors.append(f"  signal[{i}]: unknown signal_type '{st}'")

        statement = signal.get("statement", "")
        if statement and statement.lower() not in full_text.lower():
            errors.append(f"  signal[{i}]: statement not found in transcript text")
            errors.append(f"    Expected substring: {statement[:80]}...")

        section = get_section_for_excerpt(data, signal.get("source", {}).get("excerpt", ""))
        expected_section = signal.get("source", {}).get("section")
        if section and expected_section and section != expected_section:
            errors.append(f"  signal[{i}]: source.section mismatch (got {section}, expected {expected_section})")

    # Check relations
    for i, relation in enumerate(gt.get("relations", [])):
        rt = relation.get("relation_type")
        if rt not in VALID_RELATION_TYPES:
            errors.append(f"  relation[{i}]: unknown relation_type '{rt}'")

        statement = relation.get("statement", "")
        if statement and statement.lower() not in full_text.lower():
            errors.append(f"  relation[{i}]: statement not found in transcript text")
            errors.append(f"    Expected substring: {statement[:80]}...")

    return errors


def check_all(transcript_dir: str = str(TRANSCRIPT_DIR)) -> dict:
    srcdir = Path(transcript_dir)
    files = sorted(srcdir.glob("*.json"))
    results = {}

    for fp in files:
        errors = check_transcript(fp)
        results[fp.name] = {"errors": errors, "ok": len(errors) == 0}
        status = "OK" if not errors else f"FAIL ({len(errors)} issues)"
        print(f"{fp.name}: {status}")
        for e in errors:
            print(f"  {e}")

    total = len(files)
    ok = sum(1 for r in results.values() if r["ok"])
    print(f"\n{ok}/{total} transcripts passed.")
    return results


if __name__ == "__main__":
    check_all(sys.argv[1] if len(sys.argv) > 1 else str(TRANSCRIPT_DIR))
