"""synthetic-hard(gold 형식 2)용 가짜 응답기. 정답대로 답하는 응답기와, 정해진 오류를 일부러 내는 응답기.

채점 v2와 정답 규칙이 서로 맞는지 확인하는 데 쓴다. 정답대로 답하면 안전·엄격 정확도가 모두 1.0이어야 하고,
일부러 틀리게 답하면 정해진 오류 종류가 정해진 수만큼 나와야 한다.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable

from langchain_core.messages import AIMessage, BaseMessage

from tashkeel_check.fake import OUTPUT_TOOL, ZERO_USAGE, tool_call
from tashkeel_check.romanize import strict_key

Mutator = Callable[[dict, dict], dict | None]


def held_text(unit: dict) -> str:
    """보류한 부분을 번역문에 [A/B]로 쓴다. 후보가 하나뿐이면 [A/?]."""
    cands = list(dict.fromkeys([*unit["must_include"], *unit["english_variants"], unit["english_used"]]))
    distinct = list({strict_key(c): c for c in cands}.values())[:2]
    return "[" + "/".join(distinct if len(distinct) > 1 else [distinct[0], "?"]) + "]"


def oracle_item(unit: dict) -> dict:
    if unit["expected"] == "adopt":
        ev = unit["evidence"][0]
        return {
            "token_ids": unit["token_ids"],
            "type": "proper_noun",
            "candidates": [{"reading": None, "romanized": unit["expected_spelling"], "source": "llm"}],
            "decision": "evidence_adopt",
            "adopted": unit["expected_spelling"],
            "reason": "oracle",
            "confidence": 1.0,
            "evidence": {"segment_id": ev["segment_id"], "quote": ev["quote"]},
        }
    cands = list(dict.fromkeys([*unit["must_include"], *unit["english_variants"]]))
    return {
        "token_ids": unit["token_ids"],
        "type": "proper_noun",
        "candidates": [{"reading": None, "romanized": c, "source": "llm"} for c in cands],
        "decision": "hold",
        "adopted": None,
        "reason": "oracle",
        "confidence": None,
        "evidence": None,
    }


def oracle_output(doc: dict, mutate: Mutator | None = None) -> tuple[dict, str]:
    """(C1~C3 구조화 출력, C0 번역문). mutate(unit, item)이 바꾼 항목을 쓰고, None이면 그 부분을 뺀다(미처리)."""
    english: dict[str, list[str]] = defaultdict(list)
    items = []
    for occ in doc["gold"]["names"]:
        for unit in occ["tokens"]:
            item = oracle_item(unit)
            if mutate is not None:
                item = mutate(unit, item)
            if item is None:
                continue
            items.append(item)
            if item.get("_english") is not None:
                english[occ["segment_id"]].append(item.pop("_english"))
            elif item["decision"] in ("evidence_adopt", "adopt"):
                english[occ["segment_id"]].append(item["adopted"])
            else:
                english[occ["segment_id"]].append(held_text(unit))
    segs = [s["segment_id"] for s in doc["segments"]]
    translation = [{"segment_id": s, "english": " ".join(english.get(s, [])) or "text"} for s in segs]
    c0 = "\n".join(f"[{t['segment_id']}] {t['english']}" for t in translation)
    return {"translation": translation, "items": items}, c0


def make_responder(doc: dict, mutate: Mutator | None = None) -> Callable[[list[BaseMessage], list[str]], AIMessage]:
    structured, c0 = oracle_output(doc, mutate)

    def respond(messages: list[BaseMessage], bound: list[str]) -> AIMessage:
        if OUTPUT_TOOL not in bound:
            return AIMessage(content=c0, usage_metadata=ZERO_USAGE)
        return tool_call(OUTPUT_TOOL, structured)

    return respond


# ---------- 일부러 틀리는 응답 ----------


def hold_everything(unit: dict, item: dict) -> dict:
    """전부 보류. 안전 정확도는 1.0, 엄격 정확도는 기대 처분이 보류인 비율과 같아야 한다."""
    return oracle_item({**unit, "expected": "hold"})


def adopt_held_with_first_variant(unit: dict, item: dict) -> dict:
    """근거 없는 부분을 흔한 표기로 근거 없이 확정(adopt). 기대 보류인 부분마다 unsupported_adopt."""
    if unit["expected"] == "adopt":
        return item
    return {**item, "decision": "adopt", "adopted": unit["english_variants"][0], "confidence": 0.9}


def unmarked_translation(unit: dict, item: dict) -> dict:
    """항목은 보류지만 번역문에는 한 표기만 표시 없이 쓴다. 기대 보류인 부분마다 translation_unmarked."""
    if unit["expected"] == "adopt":
        return item
    return {**item, "_english": unit["english_variants"][0]}


def drop_names(unit: dict, item: dict) -> dict | None:
    """항목을 내지 않는다. 모든 부분이 unprocessed."""
    return None


def normalize_spelling(unit: dict, item: dict) -> dict:
    """근거 표기를 흔한 꼴로 고쳐 쓴다(El → Al). 철자가 바뀐 부분만 wrong_spelling(근거 검사 v2에서 강등되면 보류)."""
    if unit["expected"] != "adopt":
        return item
    fixed = re.sub(r"^El[ \-]", "Al ", unit["expected_spelling"])
    return {**item, "adopted": fixed}
