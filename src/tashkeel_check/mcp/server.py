"""MCP 서버(FastMCP, stdio).

툴 analyze_tokens·search_bundle, 리소스 document://synthetic/{split}[/{doc_id}]·document://synthetic/bundles/{split}[/{bundle_id}],
프롬프트 review_instructions.

같은 분석기·같은 프롬프트 함수를 서브프로세스에서 돌릴 뿐이다(ADR-004: 분석기는 코드에서 항상 돈다).
실행: `python -m tashkeel_check.mcp.server`. 데이터 폴더는 DATA_DIR(없으면 작업 디렉터리의 data/)을 쓴다.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastmcp import FastMCP
from pydantic import BaseModel

from ..analyzer import AnalyzeFn, thread_safe_analyze, view_for_llm
from ..analyzer import analyze_tokens as _analyze
from ..bundle.evidence import search_evidence, validated
from ..bundle.loader import parse_bundle
from ..bundle.schemas import Document as BundleDocument
from ..bundle.schemas import NameMention
from ..config import CONDITIONS, load_settings
from ..prompts import system_prompt
from ..runner import load_doc, split_gold
from ..text import Token, normalize_key

SERVER_NAME = "tashkeel-check"
SPLITS = ("dev", "eval")

mcp = FastMCP(
    SERVER_NAME,
    instructions=(
        "Tashkeel Check: Arabic morphological analysis (CAMeL Tools), synthetic sample documents, "
        "and the review instructions used by conditions C0-C3."
    ),
)

_analyze_fn: AnalyzeFn | None = None


def _fn() -> AnalyzeFn:
    """분석기는 첫 호출 때 띄운다. FastMCP가 툴을 스레드에서 돌리므로 잠금이 있는 래퍼를 쓴다."""
    global _analyze_fn
    if _analyze_fn is None:
        _analyze_fn = thread_safe_analyze()
    return _analyze_fn


def _data_dir() -> Path:
    return load_settings().data_dir


class TokenIn(BaseModel):
    id: int
    text: str
    script: str  # "ar" | "latin" | "num"


@mcp.tool
def analyze_tokens(tokens: list[TokenIn], token_ids: list[int], max_candidates: int = 10) -> list[dict]:
    """Return candidate readings for Arabic token ids from an independent morphological analyzer (CAMeL Tools).

    `tokens` is the document's token table (id, text, script); `token_ids` are the ids to analyze.
    Each result has analysis_count (0 means the analyzer does not know the word, often a name),
    ambiguous (two or more distinct readings) and candidates with reading, romanized, pos and gloss.
    Unknown ids and non-Arabic tokens come back as {"token_id", "error"} entries.
    """
    by_id = {int(t.id): t for t in tokens}
    wanted = [
        Token(id=int(t.id), segment_id="", text=t.text, start=0, end=len(t.text), script=t.script)
        for tid in token_ids
        if (t := by_id.get(int(tid))) is not None and t.script == "ar"
    ]
    analyses = _analyze(wanted, _fn())
    results: list[dict] = []
    for tid in token_ids:
        if tid not in by_id:
            results.append({"token_id": tid, "error": "unknown token id"})
        elif tid not in analyses:
            results.append({"token_id": tid, "error": "not an Arabic token"})
        else:
            results.append(view_for_llm(analyses[tid], max_candidates))
    return results


@mcp.tool
def search_bundle(
    documents: list[BundleDocument], entity_id: str, arabic_name: str, from_document_id: str = ""
) -> dict:
    """Find Latin-script spellings of `arabic_name` for the party `entity_id` in the other documents of a bundle.

    `documents` is the bundle (document_id, document_type, segments with segment_id, text, entity_id).
    Only segments tagged with the same `entity_id` count; an identical Arabic spelling under another entity id
    is never used. Each evidence row carries document_id, segment_id, the quoted segment text, the English
    spelling and the validation result (valid/failure). Unknown entity ids come back as {"error": ...}.
    """
    if not any(seg.entity_id == entity_id for doc in documents for seg in doc.segments):
        return {"error": f"unknown entity id {entity_id!r}", "evidence": []}
    bundle = parse_bundle({"bundle_id": "mcp", "documents": [d.model_dump() for d in documents]})
    mention = NameMention(
        mention_id="mcp",
        document_id=from_document_id,
        segment_id="",
        entity_id=entity_id,
        arabic_name=arabic_name,
        arabic_key=normalize_key(arabic_name),
    )
    evidence = validated(bundle, search_evidence(bundle, mention))
    return {"entity_id": entity_id, "evidence": [e.model_dump() for e in evidence]}


def _bundles_dir(split: str) -> Path:
    if split not in SPLITS:
        raise ValueError(f"unknown split {split!r}; expected one of {SPLITS}")
    return _data_dir() / "synthetic" / "bundles" / split


@mcp.resource("document://synthetic/bundles/{split}", mime_type="application/json")
def list_bundles(split: str) -> str:
    """합성 묶음 목록(bundle_id, case, entity_type). gold는 넣지 않는다."""
    rows = []
    for path in sorted(_bundles_dir(split).glob("*.json")):
        obj = json.loads(path.read_text(encoding="utf-8"))
        gold = obj.get("gold", {})
        rows.append({"bundle_id": obj["bundle_id"], "case": gold.get("case"), "entity_type": gold.get("entity_type")})
    return json.dumps(rows, ensure_ascii=False)


@mcp.resource("document://synthetic/bundles/{split}/{bundle_id}", mime_type="application/json")
def get_bundle(split: str, bundle_id: str) -> str:
    """합성 묶음 하나(gold 제외). 없는 묶음은 오류."""
    path = _bundles_dir(split) / f"{bundle_id}.json"
    if not path.is_file() or path.name != f"{bundle_id}.json":
        raise ValueError(f"bundle not found: {split}/{bundle_id}")
    return parse_bundle(json.loads(path.read_text(encoding="utf-8"))).model_dump_json()


def _split_dir(split: str) -> Path:
    if split not in SPLITS:
        raise ValueError(f"unknown split {split!r}; expected one of {SPLITS}")
    return _data_dir() / "synthetic" / split


@mcp.resource("document://synthetic/{split}", mime_type="application/json")
def list_documents(split: str) -> str:
    """합성 문서 목록(doc_id, doc_type, evidence_layout). gold는 넣지 않는다."""
    rows = []
    for path in sorted(_split_dir(split).glob("*.json")):
        doc = load_doc(path)
        rows.append(
            {"doc_id": doc["doc_id"], "doc_type": doc.get("doc_type"), "evidence_layout": doc.get("evidence_layout")}
        )
    return json.dumps(rows, ensure_ascii=False)


@mcp.resource("document://synthetic/{split}/{doc_id}", mime_type="application/json")
def get_document(split: str, doc_id: str) -> str:
    """합성 문서 하나(gold 제외). 없는 문서는 오류."""
    path = _split_dir(split) / f"{doc_id}.json"
    if not path.is_file() or path.name != f"{doc_id}.json":
        raise ValueError(f"document not found: {split}/{doc_id}")
    doc_in, _ = split_gold(load_doc(path))
    return json.dumps(doc_in, ensure_ascii=False)


@mcp.prompt
def review_instructions(condition: str) -> str:
    """조건 C0~C3의 시스템 지시문(prompts.system_prompt 그대로)."""
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition {condition!r}; expected one of {CONDITIONS}")
    return system_prompt(condition)


def main() -> None:
    mcp.run(show_banner=False)


if __name__ == "__main__":
    main()
