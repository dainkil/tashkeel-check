"""합성 묶음 생성기(가이드 14단계 평가 사례). 합성 문서(synthetic-v2)의 정답 이름으로 묶음을 만든다.

사례 9개를 대상 종류 세 가지(person / organization / other)마다 만든다. 종류가 달라도 기대 결과가 같아야 한다.
정답(`gold`)은 평가에만 쓰고 입력에서는 떼어 낸다(`bundle.loader.split_bundle_gold`).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

GENERATOR_VERSION = "bundles-v1"
NOTICE = "SYNTHETIC: 합성 데이터. 실존 인물·회사·서류·선박이 아니다. 이름은 Wikidata 이름 단위를 무작위로 조합했다."
ENTITY_TYPES = ("person", "organization", "other")
CASES = (
    "match",  # 번역 표기와 근거 일치 → 확정
    "translation_mismatch",  # 번역 표기와 근거가 다름 → 대기
    "no_english",  # 영문 근거 없음 → 대기
    "conflict",  # 서류 간 표기 충돌 → 대기
    "namesake",  # 같은 아랍어 표기, 다른 대상 → 연결하지 않음
    "bad_quote",  # 원문에 없는 인용 → 근거 거부
    "extraction_failed",  # 라벨 칸이 비어 있음 → 추출 실패 기록
    "model_error",  # LLM 호출 실패 → 실행 오류(LLM 경로에서만 평가)
    "other_customer",  # 다른 고객 묶음에만 근거 → 쓰지 않음
)
# 종류별 라벨. `other`는 일반 라벨을 쓰고 `entities`로 종류를 지정한다.
LABELS = {
    "person": ("الاسم", "Name"),
    "organization": ("اسم الشركة", "Company Name"),
    "other": ("الاسم", "Name"),
}
EVIDENCE_DOC_TYPE = {"person": "identity", "organization": "commercial_register", "other": "registry_extract"}


def _subject(doc: dict[str, Any], entity_type: str) -> dict[str, str]:
    """합성 문서의 정답 이름에서 종류별 대상 하나와 변이 표기를 고른다."""
    names = doc["gold"]["names"]
    if entity_type == "organization":
        n = next(x for x in names if x["role"] == "company")
        ar, en = f"شركة {n['arabic_full']} للتجارة", f"{n['english_full']} Trading Company"
    else:
        n = next(x for x in names if x["role"] != "company")
        ar, en = n["arabic_full"], n["english_full"]
        if entity_type == "other":
            ar, en = f"مشروع {ar}", f"{en} Project"
    variant_en = _variant(n, en)
    return {"arabic": ar, "english": en, "variant": variant_en, "namesake_english": _namesake(en)}


def _variant(n: dict[str, Any], english: str) -> str:
    """정답 토큰의 다른 영문 변이 하나를 끼운 표기. 변이가 없으면 하이픈 표기로 바꾼다."""
    for tok in n["tokens"]:
        used = tok["english_used"]
        for v in tok["english_variants"]:
            if v != used and used in english:
                return english.replace(used, v, 1)
    return english.replace("Al ", "Al-", 1) if "Al " in english else english + "h"


def _namesake(english: str) -> str:
    return english.replace("Al ", "El ", 1) if "Al " in english else "Other " + english


def _seg(sid: str, text: str, entity_id: str | None = None, translated: str | None = None) -> dict[str, Any]:
    seg: dict[str, Any] = {"segment_id": sid, "text": text}
    if entity_id is not None:
        seg["entity_id"] = entity_id
    if translated is not None:
        seg["translated_name"] = translated
    return seg


def _doc(doc_id: str, doc_type: str, segments: list[dict[str, Any]]) -> dict[str, Any]:
    return {"document_id": doc_id, "document_type": doc_type, "segments": segments}


def _bundle(
    bundle_id: str, customer_id: str, entity_id: str, entity_type: str, docs: list[dict[str, Any]], gold: dict[str, Any]
) -> dict[str, Any]:
    return {
        "bundle_id": bundle_id,
        "customer_id": customer_id,
        "synthetic": True,
        "notice": NOTICE,
        "entities": {entity_id: entity_type},
        "documents": docs,
        "gold": dict(gold, generator=GENERATOR_VERSION),
    }


def make_case(doc: dict[str, Any], entity_type: str, case: str, split: str) -> list[dict[str, Any]]:
    """사례 하나의 묶음(대개 1개, other_customer는 2개)을 만든다."""
    s = _subject(doc, entity_type)
    ar_label, en_label = LABELS[entity_type]
    eid = f"{entity_type}_{split}_001"
    bid = f"{split}_{entity_type}_{case}"
    customer = f"customer_{split}_a"
    ev_type = EVIDENCE_DOC_TYPE[entity_type]
    contract_text = f"{ar_label}: {s['arabic']}"
    bilingual = f"{ar_label}: {s['arabic']} | {en_label}: {s['english']}"
    intro = _seg("s01", "عقد خدمات بين الطرفين المذكورين أدناه.")

    def contract(translated: str | None, text: str = contract_text) -> dict[str, Any]:
        return _doc("contract_001", "contract", [intro, _seg("s02", text, eid, translated)])

    def evidence(doc_id: str, text: str, entity_id: str = eid) -> dict[str, Any]:
        return _doc(doc_id, ev_type, [_seg("s01", NOTICE), _seg("s02", text, entity_id)])

    mention = "contract_001:s02:1"
    gold: dict[str, Any] = {"case": case, "entity_type": entity_type, "requires_llm": False}

    if case == "match":
        docs = [contract(s["english"]), evidence("evidence_001", bilingual)]
        gold["review_items"] = [{"mention_id": mention, "status": "confirmed", "reason": "evidence_match"}]
    elif case == "translation_mismatch":
        docs = [contract(s["variant"]), evidence("evidence_001", bilingual)]
        gold["review_items"] = [{"mention_id": mention, "status": "pending", "reason": "translation_mismatch"}]
    elif case == "no_english":
        docs = [contract(s["english"]), evidence("evidence_001", contract_text)]
        gold["review_items"] = [
            {"mention_id": mention, "status": "pending", "reason": "no_evidence"},
            {"mention_id": "evidence_001:s02:1", "status": "pending", "reason": "no_evidence"},
        ]
    elif case == "conflict":
        other = f"{ar_label}: {s['arabic']} | {en_label}: {s['variant']}"
        docs = [contract(s["english"]), evidence("evidence_001", bilingual), evidence("evidence_002", other)]
        gold["review_items"] = [{"mention_id": mention, "status": "pending", "reason": "cross_document_conflict"}]
    elif case == "namesake":
        same_arabic = f"{ar_label}: {s['arabic']} | {en_label}: {s['namesake_english']}"
        docs = [contract(s["english"]), evidence("evidence_001", same_arabic, entity_id=f"{entity_type}_{split}_002")]
        gold["review_items"] = [{"mention_id": mention, "status": "pending", "reason": "no_evidence"}]
        gold["must_not_link"] = {"document_id": "evidence_001", "english": s["namesake_english"]}
    elif case == "bad_quote":
        docs = [contract(s["english"]), evidence("evidence_001", bilingual)]
        gold["review_items"] = [{"mention_id": mention, "status": "confirmed", "reason": "evidence_match"}]
        gold["claimed_evidence"] = {
            "document_id": "evidence_001",
            "segment_id": "s02",
            "quote": f"{en_label}: {s['variant']}",  # 원문에 없는 인용
            "english_name": s["variant"],
            "expected_failure": "quote_not_in_segment",
        }
    elif case == "extraction_failed":
        docs = [contract(s["english"], text=f"{ar_label}: "), evidence("evidence_001", bilingual)]
        gold["review_items"] = [{"mention_id": mention, "status": "pending", "reason": "extraction_failed"}]
    elif case == "model_error":
        prose = _doc("contract_001", "contract", [intro, _seg("s02", f"حضر {s['arabic']} بصفته طرفاً أول.", eid)])
        docs = [prose, evidence("evidence_001", bilingual)]
        gold["requires_llm"] = True
        gold["review_items"] = [{"mention_id": "contract_001:llm", "status": "pending", "reason": "model_error"}]
    elif case == "other_customer":
        a = _bundle(bid, customer, eid, entity_type, [contract(s["english"])], dict(gold, related_bundle=f"{bid}_b"))
        a["gold"]["review_items"] = [{"mention_id": mention, "status": "pending", "reason": "no_evidence"}]
        b_gold = {"case": case, "entity_type": entity_type, "requires_llm": False, "related_bundle": bid}
        b_gold["review_items"] = [{"mention_id": mention, "status": "confirmed", "reason": "evidence_match"}]
        b = _bundle(
            f"{bid}_b",
            f"customer_{split}_b",
            eid,
            entity_type,
            [contract(s["english"]), evidence("evidence_001", bilingual)],
            b_gold,
        )
        return [a, b]
    else:
        raise ValueError(f"unknown case {case!r}")
    return [_bundle(bid, customer, eid, entity_type, docs, gold)]


def generate_bundles(doc_path: str | Path, out_dir: str | Path, split: str) -> list[Path]:
    """합성 문서 하나로 사례 9개 × 종류 3개 묶음을 만든다. 파일 이름은 `{split}_{type}_{case}.json`."""
    doc = json.loads(Path(doc_path).read_text(encoding="utf-8"))
    out = Path(out_dir) / split
    out.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for entity_type in ENTITY_TYPES:
        for case in CASES:
            for bundle in make_case(doc, entity_type, case, split):
                p = out / f"{bundle['bundle_id']}.json"
                p.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                paths.append(p)
    return paths
