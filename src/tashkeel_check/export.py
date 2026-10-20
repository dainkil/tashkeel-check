"""산출물 저장: segments.json, proper_nouns.csv, metrics.json, run_meta.json."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .results import ReviewResult

PN_COLUMNS = ["arabic", "token_ids", "candidates", "adopted", "decision", "evidence", "analyzer_counts", "flags"]


def _dump(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_outputs(out_dir: str | Path, result: ReviewResult) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = result.model_dump(mode="json")
    _dump(
        out / "segments.json",
        {k: data[k] for k in ("doc_id", "condition", "segments", "unprocessed", "suspected_missed_names")},
    )
    with (out / "proper_nouns.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=PN_COLUMNS)
        writer.writeheader()
        for row in data["proper_nouns"]:
            writer.writerow({k: row[k] for k in PN_COLUMNS})
    _dump(out / "metrics.json", data["metrics"])
    _dump(out / "run_meta.json", data["meta"])
    return out
