"""라벨 칸(`라벨: 값`)에서 고유명사를 뽑는다(가이드 3단계). LLM 없이 돈다.

라벨 표(`LABELS`)는 라벨 → 대상 종류다. 종류는 표시·집계에만 쓰고 판정에는 쓰지 않는다.
한 줄에 `|`로 칸이 여러 개면 각 칸을 따로 본다. 아랍어 값이 있는 칸이 고유명사 한 건이고,
같은 구간의 영문 칸은 그 구간이 근거 출처임을 뜻한다(evidence.py).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..text import nfc, normalize_key
from .mrz import mrz_name
from .schemas import Document, EntityType, NameMention

LABELS: dict[str, EntityType] = {
    # 개인
    "الاسم": "person",
    "اسم": "person",
    "الاسم الكامل": "person",
    "name": "person",
    "full name": "person",
    # 회사·법인
    "اسم الشركة": "organization",
    "الشركة": "organization",
    "company": "organization",
    "company name": "organization",
    # 기관·단체
    "الجهة": "organization",
    "المؤسسة": "organization",
    "اسم المؤسسة": "organization",
    "organization": "organization",
    "organisation": "organization",
    "entity": "organization",
    # 상업등기·정관·여권 칸(KYC 묶음). 종류는 표시용이라 소유자가 법인이어도 판정은 같다
    "اسم المالك": "person",
    "المالك": "person",
    "اسم المدير": "person",
    "المدير": "person",
    "اسم الشريك": "person",
    "الشريك": "person",
    "owner": "person",
    "owner name": "person",
    "manager": "person",
    "manager name": "person",
    "shareholder": "person",
    "shareholder name": "person",
    "surname": "person",
    "given names": "person",
    "given name": "person",
}
# 여권 시각 영역의 성·이름 칸. 둘 다 있으면 "이름 성" 하나로 합쳐 영문 표기로 쓴다
SURNAME_LABELS = {"surname"}
GIVEN_LABELS = {"given names", "given name"}
MRZ_LABEL = "MRZ"

FIELD_SEP = "|"
LABEL_RE = re.compile(r"^\s*(?P<label>[^:：]{1,40}?)\s*[:：]\s*(?P<value>.*?)\s*$")
AR_LETTER_RE = re.compile("[ء-يٱ-ۓ]")
LATIN_LETTER_RE = re.compile("[A-Za-z]")


@dataclass(frozen=True)
class LabeledField:
    label: str  # 원문 라벨
    value: str  # 원문 값(공백만 정리)
    entity_type: EntityType
    script: str  # "ar" | "latin" | "other"


def _label_key(label: str) -> str:
    return " ".join(nfc(label).casefold().split())


def split_fields(text: str, labels: dict[str, EntityType] = LABELS) -> list[LabeledField]:
    """한 구간을 `|`로 나눠 알려진 라벨의 칸만 돌려준다."""
    out: list[LabeledField] = []
    for part in nfc(text).split(FIELD_SEP):
        m = LABEL_RE.match(part)
        if not m:
            continue
        key = _label_key(m.group("label"))
        if key not in labels:
            continue
        value = " ".join(m.group("value").split())
        if AR_LETTER_RE.search(value):
            script = "ar"
        elif LATIN_LETTER_RE.search(value):
            script = "latin"
        else:
            script = "other"
        out.append(LabeledField(label=m.group("label").strip(), value=value, entity_type=labels[key], script=script))
    return out


def extract_names(
    document: Document, labels: dict[str, EntityType] = LABELS, entity_types: dict[str, EntityType] | None = None
) -> list[NameMention]:
    """라벨 칸의 아랍어 값마다 NameMention 하나. 값이 비었거나 아랍어가 아니면 extraction_error를 남긴다."""
    mentions: list[NameMention] = []
    for seg in document.segments:
        n = 0
        for field in split_fields(seg.text, labels):
            if field.script == "latin":
                continue  # 영문 칸은 근거 출처다(evidence.py)
            n += 1
            etype = (entity_types or {}).get(seg.entity_id or "", field.entity_type)
            error = None
            if not field.value:
                error = "empty_value"
            elif field.script != "ar":
                error = "value_not_arabic"
            mentions.append(
                NameMention(
                    mention_id=f"{document.document_id}:{seg.segment_id}:{n}",
                    document_id=document.document_id,
                    segment_id=seg.segment_id,
                    entity_id=seg.entity_id,
                    entity_type=etype,
                    arabic_name=field.value,
                    arabic_key=normalize_key(field.value),
                    translated_name=seg.translated_name,
                    source="label",
                    extraction_error=error,
                )
            )
    return mentions


def english_fields(text: str, labels: dict[str, EntityType] = LABELS) -> list[LabeledField]:
    """근거로 쓸 영문 칸. 라벨 칸 외에 여권의 성·이름 칸 합성과 MRZ 첫 줄도 영문 표기 하나로 센다."""
    latin = [f for f in split_fields(text, labels) if f.script == "latin"]
    surname = next((f for f in latin if _label_key(f.label) in SURNAME_LABELS), None)
    given = next((f for f in latin if _label_key(f.label) in GIVEN_LABELS), None)
    if surname is not None and given is not None:
        latin = [f for f in latin if f is not surname and f is not given]
        latin.append(LabeledField("Given Names + Surname", f"{given.value} {surname.value}", "person", "latin"))
    for part in nfc(text).split(FIELD_SEP):
        name = mrz_name(part)
        if name is not None:
            latin.append(LabeledField(MRZ_LABEL, name, "person", "latin"))
    return latin
