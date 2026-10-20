"""Wikidata에서 걸프 6개국 국적 인물의 아랍어·영어 이름을 받아 스냅숏으로 저장한다(CC0).

조회는 나라별로 나눠 보낸다. 한 번에 보내면 시간 초과(HTTP 504)가 날 수 있다(TS-001).
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from ..text import normalize_key
from .names import ALIGN_VERSION, align

ENDPOINTS = {
    "wdqs": "https://query.wikidata.org/sparql",  # Wikidata 공식
    "qlever": "https://qlever.dev/api/wikidata",  # Freiburg 대학의 공개 Wikidata 미러(같은 CC0 데이터)
}
COUNTRIES = {
    "Q878": "UAE",
    "Q851": "Saudi Arabia",
    "Q846": "Qatar",
    "Q817": "Kuwait",
    "Q398": "Bahrain",
    "Q842": "Oman",
}
GENDERS = {"http://www.wikidata.org/entity/Q6581097": "male", "http://www.wikidata.org/entity/Q6581072": "female"}

PREFIXES = """PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
"""
QUERY = (
    PREFIXES
    + """SELECT ?p ?ar ?en ?gender (GROUP_CONCAT(DISTINCT ?al; separator="|") AS ?aliases) WHERE {
  ?p wdt:P31 wd:Q5; wdt:P27 wd:%s; rdfs:label ?ar. FILTER(LANG(?ar)="ar")
  ?p rdfs:label ?en. FILTER(LANG(?en)="en")
  OPTIONAL { ?p wdt:P21 ?gender }
  OPTIONAL { ?p skos:altLabel ?al. FILTER(LANG(?al)="en") }
} GROUP BY ?p ?ar ?en ?gender"""
)


def _user_agent() -> str:
    contact = os.getenv("WIKIDATA_CONTACT", "set WIKIDATA_CONTACT in .env")
    return f"tashkeel-check/0.1 (research prototype; {contact})"


def _log(msg: str) -> None:
    print(f"[wikidata {datetime.now().strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def _sparql(
    query: str, endpoint: str = "wdqs", attempts: int = 6, wait_s: float = 65.0, max_wait_s: float = 180.0
) -> list[dict]:
    """429(요청 제한)·5xx면 기다렸다가 다시 보낸다. 2026-10-13에는 분당 1회로 제한됐다(TS-002).
    Retry-After가 길어도 max_wait_s까지만 기다린다."""
    url = ENDPOINTS[endpoint] + "?" + urllib.parse.urlencode({"query": query})
    req = urllib.request.Request(
        url, headers={"User-Agent": _user_agent(), "Accept": "application/sparql-results+json"}
    )
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.load(resp)["results"]["bindings"]
        except urllib.error.HTTPError as exc:
            retry_after = exc.headers.get("Retry-After")
            if exc.code not in (429, 500, 502, 503, 504) or attempt == attempts:
                raise
            if retry_after and retry_after.isdigit() and float(retry_after) > max_wait_s:
                raise RuntimeError(
                    f"{endpoint}가 Retry-After={retry_after}s를 요구합니다. "
                    "나중에 다시 실행하거나 --endpoint qlever를 쓰세요."
                ) from exc
            wait = float(retry_after) if retry_after and retry_after.isdigit() else wait_s
            wait = min(wait, max_wait_s)
            _log(f"HTTP {exc.code}, retry {attempt}/{attempts - 1} after {wait:.0f}s (Retry-After={retry_after})")
            time.sleep(wait)
    raise RuntimeError("unreachable")


def fetch(out_dir: str | Path, endpoint: str = "wdqs") -> Path:
    """나라별 결과를 raw/<QID>.json에 저장해 두고, 다시 실행하면 받은 나라는 건너뛴다."""
    out = Path(out_dir)
    raw = out / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    rows: dict[str, dict] = {}
    first = True
    for qid, name in COUNTRIES.items():
        cache = raw / f"{qid}.json"
        if cache.exists():
            bindings = json.loads(cache.read_text(encoding="utf-8"))
            _log(f"{name}: cached ({len(bindings)} rows)")
        else:
            if not first and endpoint == "wdqs":
                time.sleep(65.0)  # 2026-10-13 WDQS의 분당 1회 제한에 맞춘다
            _log(f"{name}: querying {endpoint}")
            bindings = _sparql(QUERY % qid, endpoint)
            cache.write_text(json.dumps(bindings, ensure_ascii=False) + "\n", encoding="utf-8")
            _log(f"{name}: {len(bindings)} rows")
            first = False
        for b in bindings:
            pid = b["p"]["value"].rsplit("/", 1)[-1]
            aliases = [a for a in b.get("aliases", {}).get("value", "").split("|") if a]
            row = rows.setdefault(
                pid,
                {
                    "qid": pid,
                    "ar": b["ar"]["value"],
                    "en": b["en"]["value"],
                    "aliases": [],
                    "gender": None,
                    "countries": [],
                },
            )
            row["aliases"] = sorted(set(row["aliases"]) | set(aliases))
            row["gender"] = row["gender"] or GENDERS.get(b.get("gender", {}).get("value", ""))
            if name not in row["countries"]:
                row["countries"].append(name)
    (out / "query.rq").write_text(QUERY + "\n", encoding="utf-8")
    snapshot = {
        "source": "Wikidata SPARQL (CC0)",
        "endpoint": ENDPOINTS[endpoint],
        "retrieved_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "countries": COUNTRIES,
        "n_rows": len(rows),
        "rows": sorted(rows.values(), key=lambda r: r["qid"]),
    }
    path = out / "gcc_persons.json"
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


def build_name_pool(snapshot_path: str | Path, out_path: str | Path) -> Path:
    """이름 단위 풀. 아랍어 키(normalize_key)마다 실제 영문 표기와 빈도, 위치, 성별."""
    snap = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    pool: dict[str, dict] = {}
    stats: Counter = Counter()
    for r in snap["rows"]:
        primary = align(r["ar"], r["en"])
        stats["label_aligned" if primary else "label_unaligned"] += 1
        for en in [r["en"], *r["aliases"]]:
            pairs = primary if en == r["en"] else align(r["ar"], en)
            for ar_u, en_u, pos in pairs or []:
                e = pool.setdefault(
                    normalize_key(ar_u),
                    {"arabic": Counter(), "english": Counter(), "positions": Counter(), "genders": Counter()},
                )
                e["english"][en_u] += 1
                if en == r["en"]:
                    e["arabic"][ar_u] += 1
                    e["positions"][pos] += 1
                    e["genders"][r.get("gender") or "unknown"] += 1
    tokens = {
        k: {
            "arabic": (v["arabic"].most_common(1) or [(k, 0)])[0][0],
            "english_variants": dict(v["english"].most_common()),
            "positions": dict(v["positions"]),
            "genders": dict(v["genders"]),
        }
        for k, v in sorted(pool.items())
    }
    data = {
        "source": str(snapshot_path),
        "retrieved_at": snap["retrieved_at"],
        "align_version": ALIGN_VERSION,
        "stats": dict(stats),
        "n_units": len(tokens),
        "tokens": tokens,
        "full_names": sorted({normalize_key(r["ar"]) for r in snap["rows"]}),
    }
    out = Path(out_path)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return out
