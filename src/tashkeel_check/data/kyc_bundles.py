"""합성 KYC 온보딩 묶음 생성기(bundles-kyc-v1): 아랍어 상업등기 + 영문 여권(시각 영역·MRZ) + 이중언어 정관.

합성 문서(synthetic-v2)의 정답 이름(회사 1, 개인 2)으로 묶음 하나를 만든다. 상업등기의 번역 표기가 검수 대상이고,
여권과 정관이 근거다. 정답(`gold.review_items`)은 생성기가 낸다. 실제 서식이 아니라 칸 이름과 MRZ 규칙만 흉내 낸다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..bundle.evidence import strict_form
from ..bundle.mrz import mrz_line1, mrz_name
from .bundles import NOTICE, _bundle, _doc, _namesake, _seg, _variant

GENERATOR_VERSION = "bundles-kyc-v1"
CASES = (
    "match",  # 등기 번역이 여권·정관과 모두 일치 → 전부 확정
    "passport_mismatch",  # 소유자 번역 표기가 여권과 다름 → 대기(번역 표기 불일치)
    "no_passport",  # 관리자 여권이 없음 → 대기(근거 없음)
    "passport_aoa_conflict",  # 여권과 정관의 영문이 다름 → 대기(서류 간 표기 충돌)
    "namesake_shareholder",  # 정관의 다른 주주가 소유자와 같은 아랍어 표기(다른 대상 ID) → 연결하지 않음
    "company_mismatch",  # 회사명 번역이 정관과 다름 → 대기(번역 표기 불일치)
    "mrz_only",  # 여권에 시각 영역 칸이 없고 MRZ만 있음 → MRZ 해독으로 확정
    "unlinked_manager",  # 등기의 관리자 칸에 대상 ID가 없음 → 대기(대상 ID 없음)
)
DOC_TYPES = ("commercial_register", "passport", "articles_of_association")


def _person(n: dict[str, Any]) -> dict[str, str]:
    """정답 이름 하나에서 여권용 성·이름과 변이·동명 표기를 만든다."""
    en = n["english_full"]
    family = [t["english_used"] for t in n["tokens"] if t["position"] == "family"]
    surname = family[-1] if family and en.endswith(family[-1]) else en.split()[-1]
    given = en[: len(en) - len(surname)].strip()
    return {
        "arabic": n["arabic_full"],
        "english": en,
        "surname": surname,
        "given": given,
        "variant": _variant(n, en),
        "namesake_english": _namesake(en),
    }


def _subjects(doc: dict[str, Any]) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    names = doc["gold"]["names"]
    company = next(x for x in names if x["role"] == "company")
    persons: list[dict[str, Any]] = []
    for x in names:
        if x["role"] != "company" and all(p["arabic_full"] != x["arabic_full"] for p in persons):
            persons.append(x)
    if len(persons) < 2:
        raise ValueError(f"{doc['doc_id']}: 서로 다른 개인 이름이 둘 필요하다")
    org = {
        "arabic": f"شركة {company['arabic_full']} للتجارة",
        "english": f"{company['english_full']} Trading Company",
        "variant": f"{company['english_full']} Trading Co.",
    }
    return org, _person(persons[0]), _person(persons[1])


def _passport(doc_id: str, p: dict[str, str], entity_id: str, number: int, mrz_only: bool = False) -> dict[str, Any]:
    line1 = mrz_line1(p["surname"], p["given"])
    line2 = (f"A{number:07d}<0SAU9001015F3501015<<<<<<<<<<<<<<<<<" + "<" * 44)[:44]
    segs = [_seg("s01", NOTICE)]
    if not mrz_only:
        segs.append(_seg("s02", f"Surname: {p['surname'].upper()} | Given Names: {p['given'].upper()}", entity_id))
    segs += [_seg("s03", line1, entity_id), _seg("s04", line2)]
    return _doc(doc_id, "passport", segs)


def make_kyc_case(doc: dict[str, Any], case: str, split: str, index: int) -> dict[str, Any]:
    org, p1, p2 = _subjects(doc)
    tag = f"{split}_{index:03d}"
    org_id, p1_id, p2_id = f"org_{tag}", f"person_{tag}_1", f"person_{tag}_2"
    entities = {org_id: "organization", p1_id: "person", p2_id: "person"}
    gold: dict[str, Any] = {"case": case, "entity_types": entities, "requires_llm": False, "base_doc": doc["doc_id"]}

    org_tr, p1_tr, p2_tr, p2_entity = org["english"], p1["english"], p2["english"], p2_id
    aoa_p1_en, aoa_p1_entity = p1["english"], p1_id
    mrz_only, with_p2_passport = False, True
    if case == "passport_mismatch":
        p1_tr = p1["variant"]
    elif case == "no_passport":
        with_p2_passport = False
    elif case == "passport_aoa_conflict":
        aoa_p1_en = p1["variant"]
    elif case == "namesake_shareholder":
        aoa_p1_en, aoa_p1_entity = p1["namesake_english"], f"person_{tag}_3"
        entities[aoa_p1_entity] = "person"
    elif case == "company_mismatch":
        org_tr = org["variant"]
    elif case == "mrz_only":
        mrz_only = True
    elif case == "unlinked_manager":
        p2_entity = None  # type: ignore[assignment]
    elif case != "match":
        raise ValueError(f"unknown case {case!r}")

    register = _doc(
        "register_001",
        "commercial_register",
        [
            _seg("s01", NOTICE),
            _seg("s02", f"اسم الشركة: {org['arabic']}", org_id, org_tr),
            _seg("s03", f"اسم المالك: {p1['arabic']}", p1_id, p1_tr),
            _seg("s04", f"اسم المدير: {p2['arabic']}", p2_entity, p2_tr),
        ],
    )
    aoa = _doc(
        "aoa_001",
        "articles_of_association",
        [
            _seg("s01", NOTICE),
            _seg("s02", f"اسم الشركة: {org['arabic']} | Company Name: {org['english']}", org_id),
            _seg("s03", f"اسم الشريك: {p1['arabic']} | Shareholder: {aoa_p1_en}", aoa_p1_entity),
        ],
    )
    docs = [register, _passport("passport_p1", p1, p1_id, index * 10 + 1, mrz_only)]
    if with_p2_passport:
        docs.append(_passport("passport_p2", p2, p2_id, index * 10 + 2, mrz_only))
    docs.append(aoa)

    ok = ("confirmed", "evidence_match")
    expected = {"register_001:s02:1": ok, "register_001:s03:1": ok, "register_001:s04:1": ok}
    if case in ("passport_mismatch", "company_mismatch"):
        expected["register_001:s03:1" if case == "passport_mismatch" else "register_001:s02:1"] = (
            "pending",
            "translation_mismatch",
        )
    elif case == "no_passport":
        expected["register_001:s04:1"] = ("pending", "no_evidence")
    elif case == "passport_aoa_conflict":
        expected["register_001:s03:1"] = ("pending", "cross_document_conflict")
    elif case == "unlinked_manager":
        expected["register_001:s04:1"] = ("pending", "no_entity_id")
    gold["review_items"] = [{"mention_id": m, "status": s, "reason": r} for m, (s, r) in expected.items()]
    if case == "namesake_shareholder":
        gold["must_not_link"] = {"document_id": "aoa_001", "segment_id": "s03", "english": p1["namesake_english"]}
    if case == "mrz_only":
        # MRZ는 영문자만 담고 39자에서 잘린다. 해독값이 인쇄 표기와 다르면 정확 일치가 아니라 대기다
        lossy = []
        for mid, p in (("register_001:s03:1", p1), ("register_001:s04:1", p2)):
            decoded = mrz_name(mrz_line1(p["surname"], p["given"]))
            if decoded is None or strict_form(decoded) != strict_form(p["english"]):
                lossy.append(mid)
                expected[mid] = ("pending", "translation_mismatch")
        gold["review_items"] = [{"mention_id": m, "status": s, "reason": r} for m, (s, r) in expected.items()]
        gold["evidence_only_from"] = "MRZ"
        gold["mrz_lossy"] = lossy

    bundle = _bundle(f"{split}_kyc_{case}", f"customer_{split}_kyc", org_id, "organization", docs, gold)
    bundle["entities"] = entities
    bundle["gold"]["generator"] = GENERATOR_VERSION
    return bundle


def generate_kyc_bundles(synthetic_dir: str | Path, out_dir: str | Path, split: str) -> list[Path]:
    """사례마다 다른 합성 문서(`{split}_{i:03d}`)를 base로 묶음 하나씩. 파일 이름은 `{split}_kyc_{case}.json`."""
    out = Path(out_dir) / split
    out.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for i, case in enumerate(CASES, start=1):
        doc = json.loads((Path(synthetic_dir) / split / f"{split}_{i:03d}.json").read_text(encoding="utf-8"))
        bundle = make_kyc_case(doc, case, split, i)
        p = out / f"{bundle['bundle_id']}.json"
        p.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        paths.append(p)
    return paths
