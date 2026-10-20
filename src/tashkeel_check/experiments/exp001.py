"""EXP-001 (Q0): 형태소 분석기가 실제 걸프 인명에서 내는 후보 (계획 6.1절).

단위는 정렬된 (아랍어 이름 단위, 실제 영문 표기 집합) 고유 쌍이다.
개발용 표본(dev)으로 정렬·일치 규칙을 고친 뒤 고정하고, 나머지(main)로 한 번만 잰다.
"""

from __future__ import annotations

import itertools
import json
import random
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from ..analyzer import AnalyzeFn, analyzer_version, camel_analyze, summarize
from ..data.names import ALIGN_VERSION, align
from ..romanize import MATCHER_VERSION, match_spelling, romanize
from ..text import dediac, normalize_key

DEV_SIZE = 300
SPLIT_SEED = 7
MAX_COMBINATIONS = 50


def collect_units(snapshot_path: str | Path) -> tuple[list[dict], dict]:
    snap = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    units: dict[str, dict] = {}
    stats: Counter = Counter()
    for r in snap["rows"]:
        any_aligned = False
        for en in [r["en"], *r["aliases"]]:
            pairs = align(r["ar"], en)
            if not pairs:
                continue
            any_aligned = True
            for ar_u, en_u, pos in pairs:
                u = units.setdefault(
                    normalize_key(ar_u),
                    {"key": normalize_key(ar_u), "arabic": ar_u, "english": set(), "positions": Counter()},
                )
                u["english"].add(en_u)
                u["positions"][pos] += 1
        stats["persons_aligned" if any_aligned else "persons_unaligned"] += 1
    out = [
        {
            **u,
            "english": sorted(u["english"]),
            "position": u["positions"].most_common(1)[0][0],
            "positions": dict(u["positions"]),
        }
        for _, u in sorted(units.items())
    ]
    return out, dict(stats)


def split_units(units: list[dict], dev_size: int = DEV_SIZE, seed: int = SPLIT_SEED) -> dict[str, list[dict]]:
    order = list(range(len(units)))
    random.Random(seed).shuffle(order)
    dev_idx = set(order[:dev_size])
    return {
        "dev": [u for i, u in enumerate(units) if i in dev_idx],
        "main": [u for i, u in enumerate(units) if i not in dev_idx],
    }


def unit_measure(unit: dict, analyze_fn: AnalyzeFn) -> dict:
    words = unit["arabic"].split()
    per_word = [summarize(i, w, analyze_fn(dediac(w))) for i, w in enumerate(words)]
    forms = [[c["diac"] for c in s["candidates"]] or [] for s in per_word]
    romanized = (
        [
            " ".join(romanize(f) for f in combo)
            for combo in itertools.islice(itertools.product(*forms), MAX_COMBINATIONS)
        ]
        if all(forms)
        else []
    )
    strict = any(match_spelling(r, e) for r in romanized for e in unit["english"])
    dialect = strict or any(match_spelling(r, e, dialect=True) for r in romanized for e in unit["english"])
    single = per_word[0] if len(per_word) == 1 else None
    return {
        "key": unit["key"],
        "arabic": unit["arabic"],
        "position": unit["position"],
        "english": unit["english"],
        "n_words": len(words),
        "analysis_count": single["analysis_count"] if single else None,
        "ambiguous": single["ambiguous"] if single else None,
        "has_noun_prop": single["has_noun_prop"] if single else None,
        "candidates_romanized": romanized[:10],
        "covered_strict": strict,
        "covered_dialect": dialect,
    }


def _bucket(n: int) -> str:
    return "0" if n == 0 else "1" if n == 1 else "2-5" if n <= 5 else "6+"


def summarize_measures(rows: list[dict]) -> dict:
    single = [r for r in rows if r["n_words"] == 1]

    def rate(xs: list[bool]) -> float | None:
        return round(sum(xs) / len(xs), 4) if xs else None

    def block(rs: list[dict]) -> dict:
        sg = [r for r in rs if r["n_words"] == 1]
        return {
            "n_units": len(rs),
            "n_single_word": len(sg),
            "M1_zero_analysis_rate": rate([r["analysis_count"] == 0 for r in sg]),
            "M2_analysis_count_distribution": dict(Counter(_bucket(r["analysis_count"]) for r in sg)),
            "M3_ambiguous_rate": rate([bool(r["ambiguous"]) for r in sg]),
            "M4_noun_prop_rate": rate([bool(r["has_noun_prop"]) for r in sg]),
            "M5_coverage_strict": rate([r["covered_strict"] for r in rs]),
            "M5_coverage_dialect": rate([r["covered_dialect"] for r in rs]),
            "M6_english_variants_distribution": dict(Counter(min(len(r["english"]), 5) for r in rs)),
            "M6_ge2_variants_rate": rate([len(r["english"]) >= 2 for r in rs]),
        }

    by_position = {p: block([r for r in rows if r["position"] == p]) for p in sorted({r["position"] for r in rows})}
    return {"all": block(rows), "by_position": by_position, "n_single_word": len(single)}


def run(
    snapshot_path: str | Path,
    split: str,
    out_dir: str | Path,
    analyze_fn: AnalyzeFn | None = None,
    coverage_threshold: float = 0.5,
) -> Path:
    units, stats = collect_units(snapshot_path)
    rows = [unit_measure(u, analyze_fn or camel_analyze) for u in split_units(units)[split]]
    summary = summarize_measures(rows)
    m5 = summary["all"]["M5_coverage_dialect"]
    report = {
        "experiment": "EXP-001",
        "split": split,
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "snapshot": str(snapshot_path),
        "align_version": ALIGN_VERSION,
        "matcher_version": MATCHER_VERSION,
        "analyzer": analyzer_version(),
        "alignment_stats": stats,
        "summary": summary,
        "decision_rule": f"M5_coverage_dialect < {coverage_threshold} → 분석기를 이름 독법 근거로 쓰지 않는다",
        "decision": None
        if m5 is None
        else ("analyzer_not_name_evidence" if m5 < coverage_threshold else "analyzer_usable_for_names"),
    }
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"exp001_{split}_units.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8"
    )
    path = out / f"exp001_{split}_summary.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
