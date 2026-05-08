import json
from pathlib import Path


class Writer:
    def __init__(self, output_dir: str = "data") -> None:
        self._output_dir = Path(output_dir)
        self._written: set[str] = set()

    def _ensure_dir(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

    def _write_jsonl(self, path: Path, items: list) -> None:
        self._ensure_dir(path)
        key = str(path)
        if key in self._written:
            mode = "a"
        else:
            mode = "w"
            self._written.add(key)
        with open(path, mode, encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item.model_dump()) + "\n")

    def write_signals(self, quarter: str, signals: list) -> None:
        path = self._output_dir / "signal_library" / f"signals_{quarter}.jsonl"
        self._write_jsonl(path, signals)

    def write_vague_signals(self, quarter: str, signals: list) -> None:
        path = self._output_dir / "signal_library" / f"vague_{quarter}.jsonl"
        self._write_jsonl(path, signals)

    def write_review_entries(self, quarter: str, entries: list) -> None:
        path = self._output_dir / "review_queue" / f"review_{quarter}.jsonl"
        self._write_jsonl(path, entries)
