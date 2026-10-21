"""업로드 초안(ADR-019): 이름 칸과 같은 대상 제안. 저장·자동 연결 없음."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tashkeel_check.bundle.draft import build_draft
from tashkeel_check.bundle.loader import parse_bundle
from tashkeel_check.bundle.mrz import mrz_line1
from tashkeel_check.bundle.upload import bundle_from_uploads
from tashkeel_check.config import Settings
from tashkeel_check.web.app import build_runtime, create_app

from .conftest import fake_analyze

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = json.loads((ROOT / "data" / "bundles" / "sample_bundle.json").read_text(encoding="utf-8"))

CONTRACT = "عقد خدمات بين الطرفين.\nالاسم: مسلم\nاسم الشركة: شركة الخليج للتجارة\n"
ID_CARD = "Surname: AL KAABI | Given Names: MUSALLAM\n" + mrz_line1("Al Kaabi", "Musallam") + "\n"
REGISTER = "اسم الشركة: شركة الخليج للتجارة | Company Name: Gulf Trading Company\n"
FILES = [("contract.txt", CONTRACT.encode()), ("id.txt", ID_CARD.encode()), ("cr.txt", REGISTER.encode())]


def test_draft_groups_same_arabic_and_lists_plain_segments():
    draft = build_draft(bundle_from_uploads(FILES, bundle_id="d1"))
    fields = draft["fields"]
    # 초안은 대상 ID를 넣지 않는다
    assert all(s.get("entity_id") is None for d in draft["bundle"]["documents"] for s in d["segments"])
    assert "entity_id" not in json.dumps(fields)
    plain = [f for f in fields if f["label"] is None]
    assert [(f["document_id"], f["segment_id"]) for f in plain] == [("contract", "s01")] and plain[0][
        "suggested_group"
    ] is None
    by = {(f["document_id"], f["segment_id"], f["label"]): f for f in fields if f["label"]}
    company_contract = by[("contract", "s03", "اسم الشركة")]
    company_cr = by[("cr", "s01", "اسم الشركة")]
    assert company_contract["suggested_group"] == company_cr["suggested_group"]  # 같은 아랍어 → 같은 그룹(제안)
    assert by[("cr", "s01", "Company Name")]["suggested_group"] == company_cr["suggested_group"]  # 같은 줄 → 같은 그룹
    assert by[("contract", "s02", "الاسم")]["suggested_group"] != company_contract["suggested_group"]
    # 여권: 성·이름 칸은 하나로 합쳐지고 MRZ는 같은 값이라 같은 그룹. 아랍어 이름과는 연결되지 않는다(라틴만 있어서)
    passport = [f for f in fields if f["document_id"] == "id"]
    assert [f["value"] for f in passport] == ["MUSALLAM AL KAABI", "MUSALLAM AL KAABI"]
    assert len({f["suggested_group"] for f in passport}) == 1
    assert passport[0]["suggested_group"] != by[("contract", "s02", "الاسم")]["suggested_group"]
    groups = {g["group"]: g for g in draft["groups"]}
    assert groups[company_cr["suggested_group"]]["latin"] == ["Gulf Trading Company"]
    assert len(groups) == 3


def test_draft_of_sample_bundle_keeps_person_and_company_apart():
    draft = build_draft(parse_bundle(SAMPLE))
    labelled = [f for f in draft["fields"] if f["label"]]
    assert {f["entity_type"] for f in labelled} == {"person", "organization"}
    person = {f["suggested_group"] for f in labelled if f["entity_type"] == "person"}
    org = {f["suggested_group"] for f in labelled if f["entity_type"] == "organization"}
    assert person.isdisjoint(org)


@pytest.fixture
def client(tmp_path):
    rt = build_runtime(Settings(llm_backend="fake", results_dir=tmp_path), analyze_fn=fake_analyze)
    with TestClient(create_app(rt)) as c:
        yield c


def test_draft_endpoint_does_not_store_and_assembled_review_works(client):
    parts = [("files", (name, data, "application/octet-stream")) for name, data in FILES]
    r = client.post("/v1/bundles/draft", files=parts, data={"bundle_id": "draft_1", "customer_id": "c1"})
    assert r.status_code == 201 or r.status_code == 200, r.text
    draft = r.json()
    assert client.get("/v1/bundles/draft_1").status_code == 404  # 저장하지 않는다
    # 화면이 하는 일: 제안 그룹마다 대상을 만들고 구간에 붙여 묶음 JSON을 조립한다
    gid_of = {
        (f["document_id"], f["segment_id"]): f["suggested_group"] for f in draft["fields"] if f["suggested_group"]
    }
    entities = {
        g["group"]: "person" if g["group"] == gid_of[("contract", "s02")] else "organization" for g in draft["groups"]
    }
    entities[gid_of[("id", "s01")]] = "person"
    bundle = draft["bundle"]
    bundle["entities"] = entities
    for doc in bundle["documents"]:
        for seg in doc["segments"]:
            gid = gid_of.get((doc["document_id"], seg["segment_id"]))
            if gid:
                seg["entity_id"] = gid
    # 사람은 여권 그룹과 다른 그룹으로 제안됐으므로, 담당자가 같은 대상이라고 고른다
    for seg in next(d for d in bundle["documents"] if d["document_id"] == "id")["segments"]:
        seg["entity_id"] = gid_of[("contract", "s02")]
    next(d for d in bundle["documents"] if d["document_id"] == "contract")["segments"][1]["translated_name"] = (
        "Musallam Al Kaabi"
    )
    next(d for d in bundle["documents"] if d["document_id"] == "contract")["segments"][2]["translated_name"] = (
        "Gulf Trading Company"
    )
    r = client.post("/v1/bundles/review", json=bundle)
    assert r.status_code == 200, r.text
    got = {i["mention_id"]: (i["status"], i["reason"]) for i in r.json()["items"]}
    assert got == {"contract:s02:1": ("confirmed", "evidence_match"), "contract:s03:1": ("confirmed", "evidence_match")}
    assert client.post("/v1/bundles/draft", files=[("files", ("x.pdf", b"%PDF", "application/pdf"))]).status_code == 400
