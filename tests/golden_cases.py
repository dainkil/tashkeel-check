"""골든 스냅숏: 리팩토링 전후로 결과가 같은지 보는 기준값.

dev 문서 10개 × C0~C3를 가짜 모델로 돌려 반환값과 산출 파일 4종을 그대로 남긴다.
기준값은 `uv run python -m tests.golden_cases`로 만든다. 리팩토링 중에는 다시 만들지 않는다(ADR-013).
기준값을 다시 만들어야 한다면 그 변경은 리팩토링이 아니다. 이유를 docs/changelog.md에 남긴다.
"""

from __future__ import annotations

import json
import re
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from tashkeel_check.analyzer import AnalyzeFn
from tashkeel_check.config import CONDITIONS, Settings
from tashkeel_check.fake import OUTPUT_TOOL, FakeAgentModel, Responder, practice_responder, tool_call
from tashkeel_check.runner import load_doc, run_document

from .conftest import fake_analyze

ROOT = Path(__file__).resolve().parents[1]
DEV_DOCS = sorted((ROOT / "data" / "synthetic" / "dev").glob("*.json"))
GOLDEN_DIR = Path(__file__).parent / "golden"
OUTPUT_FILES = ("segments.json", "metrics.json", "run_meta.json")
VOLATILE_META = ("elapsed_s", "tracing")  # 실행 시간과 환경에 따라 바뀌는 값

SEG_LINE_RE = re.compile(r"^\[(s\d+)\] (.*)$", re.M)
LATIN_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*")


class VariedResponder:
    """처분 종류, 근거 검증 성공·실패, 무효 토큰 ID, 유형·처분 불일치, 재시도를 골고루 내는 결정적 응답기."""

    def __init__(self, retry_first: bool) -> None:
        self.retry_first = retry_first
        self.final_calls = 0

    def __call__(self, messages: list[BaseMessage], bound: list[str]) -> AIMessage:
        text = next(str(m.content) for m in messages if isinstance(m, HumanMessage))
        segs = SEG_LINE_RE.findall(text.split("TOKENS", 1)[0])
        seg_ids = [sid for sid, _ in segs]
        if self.retry_first and self.final_calls == 0:
            seg_ids = seg_ids[:-1]  # 첫 시도는 구간 하나를 빠뜨려 validate의 재시도를 탄다
        usage = {"input_tokens": len(text), "output_tokens": 10, "total_tokens": len(text) + 10}

        if OUTPUT_TOOL not in bound:  # C0: 문서의 라틴 문자 단어를 구간마다 늘어놓고, 짝수 구간은 "/"로 잇는다
            self.final_calls += 1
            words = [w for _, line in segs for w in LATIN_WORD_RE.findall(line)]
            lines = [
                f"[{sid}] " + ((" / " if i % 2 == 0 else " ").join(words) or "text") for i, sid in enumerate(seg_ids)
            ]
            return AIMessage(content="\n".join(lines), usage_metadata=usage)

        table = text.split("TOKENS", 1)[1].split("ANALYZER", 1)[0]
        ids = [int(x) for x in re.findall(r"(\d+)=", table)]
        if "analyze_tokens" in bound and not any(isinstance(m, ToolMessage) for m in messages):
            return tool_call("analyze_tokens", {"token_ids": ids[:5] + [99999]})
        self.final_calls += 1
        translation = [{"segment_id": sid, "english": f"english {sid}"} for sid in seg_ids]
        return tool_call(OUTPUT_TOOL, {"translation": translation, "items": _items(ids, segs)})


def _evidence(segs: list[tuple[str, str]], correct: bool) -> tuple[str, str, str]:
    """(segment_id, quote, adopted). 라틴 문자 구간이 없으면 없는 구간을 가리킨다."""
    for sid, line in segs:
        words = list(LATIN_WORD_RE.finditer(line))
        if words:
            last = words[min(1, len(words) - 1)]
            quote = line[words[0].start() : last.end()]
            return sid, quote, (last.group(0) if correct else "Zzzz")
    return "s99", "Nowhere", "Nowhere"


def _items(ids: list[int], segs: list[tuple[str, str]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for i, tid in enumerate(ids):
        kind = i % 7
        if kind == 6:
            continue  # 미처리로 남긴다
        item: dict[str, Any] = {
            "token_ids": [tid],
            "type": "proper_noun",
            "candidates": [{"reading": None, "romanized": f"Cand{i}", "source": "llm" if i % 2 else "analyzer"}],
            "decision": "hold",
            "adopted": None,
            "reason": f"reason {i}",
            "confidence": None,
            "evidence": None,
        }
        if kind == 1:
            item.update(decision="adopt", adopted=f"Name{i}", confidence=0.9 if i % 2 else 0.5)
        elif kind == 2:
            item.update(type="word", decision="adopt", adopted=f"reading{i}", confidence=0.4)
        elif kind == 3:
            item.update(type="word", decision="abstain")
        elif kind in (4, 5):
            sid, quote, adopted = _evidence(segs, correct=kind == 4)
            item.update(
                decision="evidence_adopt", adopted=adopted, confidence=0.7, evidence={"segment_id": sid, "quote": quote}
            )
        items.append(item)
    hold = {"candidates": [], "adopted": None, "reason": "x", "confidence": None, "evidence": None}
    if len(ids) >= 2:
        items.append({**hold, "token_ids": ids[:2], "type": "proper_noun", "decision": "hold"})
    items.append({**hold, "token_ids": [99999], "type": "proper_noun", "decision": "hold"})
    if ids:
        items.append({**hold, "token_ids": [ids[-1]], "type": "word", "decision": "hold"})
    return items


ANALYZERS: dict[str, AnalyzeFn | None] = {"fakeanalyzer": fake_analyze, "camel": None}
RESPONDERS: dict[str, Callable[[int], Responder]] = {
    "practice": lambda _doc_index: practice_responder,
    "varied": lambda doc_index: VariedResponder(retry_first=doc_index % 2 == 1),
}


def _as_dict(result: Any) -> Any:
    return result.model_dump(mode="json") if hasattr(result, "model_dump") else result


def _normalize(data: Any) -> Any:
    data = json.loads(json.dumps(data, ensure_ascii=False, default=str))
    for meta in (data["result"]["meta"], data["files"]["run_meta.json"]):
        for key in VOLATILE_META:
            meta.pop(key, None)
    return data


def _dedupe(data: dict[str, Any]) -> dict[str, Any]:
    """파일에 그대로 들어간 반환값 부분(segments·metrics·meta)은 파일 쪽에만 남긴다. 같은지는 여기서 확인한다."""
    result, files = data["result"], data["files"]
    assert result["segments"] == files["segments.json"]["segments"]
    assert result["metrics"] == files["metrics.json"]
    assert result["meta"] == files["run_meta.json"]
    rest = {k: v for k, v in result.items() if k not in ("segments", "metrics", "meta")}
    return {"result": rest, "files": files}


def snapshot(doc_index: int, condition: str, analyzer: str, responder: str) -> Any:
    doc = load_doc(DEV_DOCS[doc_index])
    model = FakeAgentModel(responder=RESPONDERS[responder](doc_index))
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        # 골든은 EXP-002 설정(지시문 p0)으로 기록했다. 서비스 기본이 p1로 바뀌어도(ADR-021) 기준값은 그대로다(ADR-013)
        settings = Settings(prompt_version="p0")
        result = run_document(doc, condition, model, settings, out_dir=out, analyze_fn=ANALYZERS[analyzer])
        files: dict[str, Any] = {name: json.loads((out / name).read_text(encoding="utf-8")) for name in OUTPUT_FILES}
        files["proper_nouns.csv"] = (out / "proper_nouns.csv").read_text(encoding="utf-8-sig")
    return _dedupe(_normalize({"result": _as_dict(result), "files": files}))


def golden_path(analyzer: str, responder: str) -> Path:
    return GOLDEN_DIR / f"{analyzer}-{responder}.json"


def build_all() -> None:
    GOLDEN_DIR.mkdir(exist_ok=True)
    for analyzer in ANALYZERS:
        for responder in RESPONDERS:
            cases = {
                f"{path.stem}:{cond}": snapshot(i, cond, analyzer, responder)
                for i, path in enumerate(DEV_DOCS)
                for cond in CONDITIONS
            }
            path = golden_path(analyzer, responder)
            lines = [f"{json.dumps(k)}: {json.dumps(v, ensure_ascii=False, sort_keys=True)}" for k, v in cases.items()]
            path.write_text("{\n" + ",\n".join(lines) + "\n}\n", encoding="utf-8")  # 사례마다 한 줄
            print(f"{path} ({len(cases)} cases)")


if __name__ == "__main__":
    build_all()
