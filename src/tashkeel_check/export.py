"""산출물 저장: segments.json, proper_nouns.csv, metrics.json, run_meta.json."""

from __future__ import annotations

import csv
import json
from pathlib import Path

PN_COLUMNS = ["arabic", "token_ids", "candidates", "adopted", "decision", "evidence", "analyzer_counts", "flags"]


def _dump(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_outputs(out_dir: str | Path, result: dict, meta: dict) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    _dump(
        out / "segments.json",
        {
            "doc_id": result.get("doc_id"),
            "condition": result.get("condition"),
            "segments": result["segments"],
            "unprocessed": result["unprocessed"],
            "suspected_missed_names": result.get("suspected_missed_names", []),
        },
    )
    with (out / "proper_nouns.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=PN_COLUMNS)
        writer.writeheader()
        for row in result["proper_nouns"]:
            writer.writerow({k: row.get(k, "") for k in PN_COLUMNS})
    _dump(out / "metrics.json", result["metrics"])
    _dump(out / "run_meta.json", meta)
    return out
