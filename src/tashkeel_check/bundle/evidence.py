"""근거 검색과 인용 검증(가이드 4·5단계).

근거는 같은 묶음의 **다른 서류**에서, **같은 대상 ID**가 붙은 구간의 영문 칸이다.
아랍어 표기가 같다는 이유로 다른 대상의 구간을 쓰지 않는다. 검증은 서류·구간·인용·영문 표기를
원문과 다시 대조한다. 실패 코드는 `reconcile.verify_evidence`와 같은 이름 체계를 쓴다.
"""

from __future__ import annotations

from typing import Any

from ..text import nfc, normalize_key
from .extractor import LABELS, MRZ_LABEL, LabeledField, english_fields, split_fields
from .schemas import Bundle, BundleEvidence, Document, EntityType, NameMention


def strict_form(spelling: str) -> str:
    """대소문자·앞뒤·연속 공백만 정리한 비교형. 철자는 바꾸지 않는다."""
    return " ".join(nfc(spelling).casefold().split())


def search_evidence(
    bundle: Bundle, mention: NameMention, labels: dict[str, EntityType] = LABELS
) -> list[BundleEvidence]:
    """같은 대상 ID가 붙은 다른 서류의 영문 칸을 전부 돌려준다. 검증은 하지 않는다."""
    if mention.entity_id is None:
        return []
    found: list[BundleEvidence] = []
    for doc in bundle.documents:
        if doc.document_id == mention.document_id:
            continue
        in_doc: list[tuple[str, LabeledField]] = [
            (seg.segment_id, field)
            for seg in doc.segments
            if seg.entity_id == mention.entity_id
            for field in english_fields(seg.text, labels)
        ]
        # 같은 서류에 인쇄된 영문 칸이 있으면 MRZ는 쓰지 않는다. MRZ는 영문자만 담고 39자에서 잘려
        # 같은 여권의 인쇄 칸과 다른 꼴이 될 수 있어서다. MRZ만 있는 서류에서는 MRZ 해독값이 근거다
        if any(f.label != MRZ_LABEL for _, f in in_doc):
            in_doc = [(sid, f) for sid, f in in_doc if f.label != MRZ_LABEL]
        for sid, field in in_doc:
            seg = doc.segment(sid)
            assert seg is not None
            found.append(
                BundleEvidence(document_id=doc.document_id, segment_id=sid, quote=seg.text, english_name=field.value)
            )
    return found


def evidence_rows_for_document(bundle: Bundle, document: Document, dictionary: Any = None) -> list[dict[str, Any]]:
    """M1(멀티 에이전트 틀) 참고용: 이 서류의 대상 ID가 붙은 구간마다 다른 서류·사전의 영문 표기(ADR-019).

    인용할 수 있는 근거가 아니라 참고다. 교차 서류 확정은 `rules.decide_status`가 한다.
    """
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for seg in document.segments:
        if seg.entity_id is None:
            continue
        probe = NameMention(
            mention_id=f"{document.document_id}:{seg.segment_id}:probe",
            document_id=document.document_id,
            segment_id=seg.segment_id,
            entity_id=seg.entity_id,
            arabic_name=seg.text,
            arabic_key=normalize_key(seg.text),
        )
        for ev in search_evidence(bundle, probe):
            key = (seg.segment_id, ev.document_id, strict_form(ev.english_name))
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "segment_id": seg.segment_id,
                    "entity_id": seg.entity_id,
                    "english": ev.english_name,
                    "document_id": ev.document_id,
                    "source_segment_id": ev.segment_id,
                }
            )
        if dictionary is not None and bundle.customer_id:
            for field in split_fields(seg.text):
                if field.script != "ar":
                    continue
                hit = dictionary.lookup_verified_name(bundle.customer_id, seg.entity_id, normalize_key(field.value))
                if hit is not None and (seg.segment_id, "dictionary", strict_form(hit.english_name)) not in seen:
                    seen.add((seg.segment_id, "dictionary", strict_form(hit.english_name)))
                    rows.append(
                        {
                            "segment_id": seg.segment_id,
                            "entity_id": seg.entity_id,
                            "english": hit.english_name,
                            "document_id": "dictionary",
                            "source_segment_id": hit.evidence_segment_id or "",
                        }
                    )
    return rows


def validate_evidence(bundle: Bundle, evidence: BundleEvidence) -> tuple[bool, str | None]:
    """근거가 원문에 실제로 있는지 본다. (통과 여부, 실패 코드)."""
    doc = bundle.document(evidence.document_id)
    if doc is None:
        return False, "document_not_found"
    seg = doc.segment(evidence.segment_id)
    if seg is None:
        return False, "segment_not_found"
    if not evidence.quote.strip():
        return False, "empty_quote"
    if strict_form(evidence.quote) not in strict_form(seg.text):
        return False, "quote_not_in_segment"
    name = strict_form(evidence.english_name)
    if not name:
        return False, "name_not_in_quote"
    # 영문 표기는 인용 안에 그대로 있거나, 인용의 영문 칸(성·이름 합성, MRZ 해독)에서 나온 것이어야 한다
    if name not in strict_form(evidence.quote) and name not in {
        strict_form(f.value) for f in english_fields(evidence.quote)
    }:
        return False, "name_not_in_quote"
    return True, None


def validated(bundle: Bundle, evidence: list[BundleEvidence]) -> list[BundleEvidence]:
    out: list[BundleEvidence] = []
    for ev in evidence:
        ok, failure = validate_evidence(bundle, ev)
        out.append(ev.model_copy(update={"valid": ok, "failure": failure}))
    return out
