"""단일 문서 결과에 보관함 제안을 덧씌운다(ADR-022). LLM 없이 코드가 한다. 사전 덧씌움(dictionary_apply) 다음에 돈다.

`ReviewResult`는 건드리지 않는다. 재료는 M2 중재자가 `metrics.engine["archive"]`에 적은 역할별 선택이다.
규칙:
- 보류(hold)나 근거 검증에 실패한 확정(adopt_unsupported)이고, 사전 덧씌움이 없는 항목만 본다(사전이 이긴다).
- 선택마다 보관함 원문을 다시 읽어 확인한다: 같은 고객의 다른 서류 구절인가(문서 ID·파일 해시), 이름이 그 구절에
  단어 단위로 있는가, 철자가 구절 안 라틴 문자와 글자 그대로 같은가(근거 검사 v2 규칙).
- 확인을 통과한 철자가 하나면 `archive_suggest`(두 역할이 같은 철자를 골랐으면 agreement "both"), 둘 이상이면
  `archive_conflict`. 어느 쪽도 확정이 아니다. 확정은 사람이 후보를 눌러 사전에 넣을 때만 한다(ADR-010).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .archive.search import CompanyArchive
from .dictionary_apply import name_text
from .results import ReviewResult
from .romanize import strict_key
from .text import normalize_key

ArchiveStatus = Literal["archive_suggest", "archive_conflict"]


class ArchiveSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spelling: str
    hit_id: str
    by: list[str]  # translator / verifier
    document_id: str
    document_label: str
    document_date: str
    segment_id: str
    quote: str  # 보관함 구절(구간 + 다음 구간)


class ArchiveOverlay(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_index: int
    token_ids: list[int]
    arabic: str
    arabic_key: str
    status: ArchiveStatus
    agreement: Literal["both", "one"]
    suggestions: list[ArchiveSuggestion]
    detail: str = ""


def apply_archive(
    result: ReviewResult,
    archive: CompanyArchive | None,
    customer_id: str | None,
    document_id: str | None,
    sha256: str | None,
    dictionary_overlays: list[dict],
) -> list[ArchiveOverlay]:
    if archive is None or not customer_id:
        return []
    claims = (result.metrics.get("engine") or {}).get("archive") or []
    taken = {tuple(o["token_ids"]) for o in dictionary_overlays}
    items = {tuple(it.token_ids): it for it in result.items if it.type == "proper_noun" and it.valid}
    out: list[ArchiveOverlay] = []
    for claim in claims:
        key = tuple(claim.get("token_ids") or [])
        it = items.get(key)
        if it is None or key in taken or it.final_decision not in ("hold", "adopt_unsupported"):
            continue
        arabic = name_text(it)
        verified: list[ArchiveSuggestion] = []
        for pick in claim.get("picks", []):
            for hid in pick.get("hit_ids", []):
                p = archive.verify_pick(customer_id, hid, arabic, pick["spelling"], document_id, sha256)
                if p is None:
                    continue
                same = next((v for v in verified if strict_key(v.spelling) == strict_key(pick["spelling"])), None)
                if same is not None:
                    same.by = sorted(set(same.by) | set(pick["by"]))
                    continue
                verified.append(
                    ArchiveSuggestion(
                        spelling=pick["spelling"],
                        hit_id=hid,
                        by=sorted(pick["by"]),
                        document_id=p.document_id,
                        document_label=p.document_label,
                        document_date=p.created_at.date().isoformat(),
                        segment_id=p.segment_id,
                        quote=p.window,
                    )
                )
        if not verified:
            continue
        conflict = len(verified) > 1
        both = not conflict and len(verified[0].by) > 1
        out.append(
            ArchiveOverlay(
                item_index=it.item_index,
                token_ids=list(it.token_ids),
                arabic=arabic,
                arabic_key=normalize_key(arabic),
                status="archive_conflict" if conflict else "archive_suggest",
                agreement="both" if both else "one",
                suggestions=verified,
                detail=(
                    "지난 서류들의 영문 표기가 서로 다르다"
                    if conflict
                    else "두 에이전트가 같은 지난 서류 표기를 골랐다"
                    if both
                    else "한 에이전트만 지난 서류 표기를 골랐다"
                ),
            )
        )
    return out
