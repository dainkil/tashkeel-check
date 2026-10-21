"""업로드 초안(ADR-019): 올린 서류에서 이름 칸을 뽑아 "서류/구간/칸/값"과 같은 대상 **제안**을 돌려준다.

저장하지 않고 `entity_id`도 넣지 않는다. 같은 대상은 사람이 화면에서 고른다. 제안 규칙:
- 한 구간의 칸은 같은 그룹(한 줄 = 한 당사자. `extract_names`·`search_evidence`와 같은 가정).
- 아랍어 정규화 키가 같은 구간은 같은 그룹.
- 라틴 칸만 있는 구간(여권)은 그 영문 표기가 이미 어떤 그룹의 라틴 값과 정확히 같을 때만 그 그룹.
이름이 같다는 사실로 자동 연결하지 않는다(ADR-018). "제안대로 만들기"를 눌러야 대상이 된다.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from ..text import normalize_key
from .evidence import strict_form
from .extractor import english_fields, split_fields
from .schemas import Bundle, EntityType


class DraftField(BaseModel):
    document_id: str
    segment_id: str
    label: str | None  # 라벨 칸이 없는 문장 구간은 None(LLM 경로에서 대상 ID를 붙일 수 있게 나열)
    value: str
    script: str  # ar | latin | other
    entity_type: EntityType | None
    arabic_key: str | None
    suggested_group: str | None


def build_draft(bundle: Bundle) -> dict[str, Any]:
    fields: list[DraftField] = []
    groups: dict[str, dict[str, Any]] = {}
    by_arabic: dict[str, str] = {}  # arabic_key → group
    by_latin: dict[str, str] = {}  # strict latin → group
    seg_group: dict[tuple[str, str], str] = {}

    def new_group() -> str:
        gid = f"g{len(groups) + 1}"
        groups[gid] = {"group": gid, "arabic_keys": [], "latin": [], "members": []}
        return gid

    for doc in bundle.documents:
        for seg in doc.segments:
            ar = [f for f in split_fields(seg.text) if f.script == "ar"]
            latin = english_fields(seg.text)
            gid: str | None = None
            for f in ar:
                key = normalize_key(f.value)
                if key in by_arabic:
                    gid = by_arabic[key]
                    break
            if gid is None:
                for f in latin:
                    if strict_form(f.value) in by_latin:
                        gid = by_latin[strict_form(f.value)]
                        break
            if gid is None and (ar or latin):
                gid = new_group()
            if gid is not None:
                g = groups[gid]
                g["members"].append([doc.document_id, seg.segment_id])
                seg_group[(doc.document_id, seg.segment_id)] = gid
                for f in ar:
                    key = normalize_key(f.value)
                    by_arabic.setdefault(key, gid)
                    if key not in g["arabic_keys"]:
                        g["arabic_keys"].append(key)
                for f in latin:
                    by_latin.setdefault(strict_form(f.value), gid)
                    if f.value not in g["latin"]:
                        g["latin"].append(f.value)
            if not ar and not latin:
                fields.append(
                    DraftField(
                        document_id=doc.document_id,
                        segment_id=seg.segment_id,
                        label=None,
                        value=seg.text,
                        script="ar" if any("؀" <= ch <= "ۿ" for ch in seg.text) else "other",
                        entity_type=None,
                        arabic_key=None,
                        suggested_group=None,
                    )
                )
                continue
            for f in [*ar, *latin]:
                fields.append(
                    DraftField(
                        document_id=doc.document_id,
                        segment_id=seg.segment_id,
                        label=f.label,
                        value=f.value,
                        script=f.script,
                        entity_type=f.entity_type,
                        arabic_key=normalize_key(f.value) if f.script == "ar" else None,
                        suggested_group=gid,
                    )
                )
    return {
        "bundle": bundle.model_dump(mode="json"),
        "fields": [f.model_dump(mode="json") for f in fields],
        "groups": list(groups.values()),
    }
