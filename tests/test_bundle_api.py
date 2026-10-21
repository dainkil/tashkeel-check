"""가이드 8단계: 묶음 검수 API. JSON으로 검수하고 전체·대기 목록을 조회하며, 없는 묶음은 404다."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tashkeel_check.config import Settings
from tashkeel_check.web.app import build_runtime, create_app

from .conftest import fake_analyze

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = json.loads((ROOT / "data" / "bundles" / "sample_bundle.json").read_text(encoding="utf-8"))


@pytest.fixture
def client(tmp_path):
    rt = build_runtime(Settings(llm_backend="fake", results_dir=tmp_path), analyze_fn=fake_analyze)
    with TestClient(create_app(rt)) as c:
        yield c


def test_review_then_items_and_pending(client):
    r = client.post("/v1/bundles/review", json=SAMPLE)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["bundle_id"] == "bundle_sample_001" and body["counts"] == {"confirmed": 1, "pending": 1}
    items = client.get("/v1/bundles/bundle_sample_001/items").json()
    assert {i["entity_type"] for i in items} == {"person", "organization"}
    pending = client.get("/v1/bundles/bundle_sample_001/pending").json()
    assert len(pending) == 1 and pending[0]["reason"] == "translation_mismatch"
    assert pending[0]["reason_label"] == "번역 표기 불일치"
    assert pending[0]["evidence"][0]["document_id"] == "id_001" and pending[0]["evidence"][0]["valid"] is True
    assert client.get("/v1/bundles").json()[0]["pending"] == 1
    assert client.get("/v1/bundles/bundle_sample_001").json()["documents"][0]["document_id"] == "contract_001"


def test_unknown_bundle_is_404(client):
    assert client.get("/v1/bundles/nope/items").status_code == 404
    assert client.get("/v1/bundles/nope/pending").status_code == 404
    assert client.get("/v1/bundles/nope").status_code == 404
    assert client.get("/v1/bundles/samples/nope").status_code == 404


def test_invalid_bundle_is_400_with_reason(client):
    r = client.post("/v1/bundles/review", json={"bundle_id": "x", "documents": []})
    assert r.status_code == 400 and r.json()["kind"] == "input" and "묶음 구조 오류" in r.json()["error"]
    r = client.post("/v1/bundles/review", content=b"{not json", headers={"content-type": "application/json"})
    assert r.status_code == 422  # FastAPI의 JSON 파싱 오류


def test_sample_bundles_are_listed_without_gold(client):
    rows = client.get("/v1/bundles/samples").json()
    assert any(r["bundle_id"] == "dev_person_match" for r in rows)
    b = client.get("/v1/bundles/samples/dev_person_match").json()
    assert "gold" not in b and b["entities"] == {"person_dev_001": "person"}
    r = client.post("/v1/bundles/review", json=b)
    assert r.json()["counts"] == {"confirmed": 1, "pending": 0}


def test_close_pending_registers_dictionary_and_next_review_uses_it(client):
    client.post("/v1/bundles/review", json=SAMPLE)
    pending = client.get("/v1/bundles/bundle_sample_001/pending").json()[0]
    r = client.post(
        "/v1/dictionary",
        json={"bundle_id": "bundle_sample_001", "mention_id": pending["mention_id"], "english_name": "Musallam"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["entity_id"] == "person_001" and r.json()["verified_by"] == "reviewer"
    # 같은 고객의 다음 묶음: 근거 서류가 없어도 사전으로 확정한다
    next_bundle = {
        "bundle_id": "bundle_sample_002",
        "customer_id": "customer_demo",
        "documents": [
            {
                "document_id": "contract_002",
                "document_type": "contract",
                "segments": [
                    {
                        "segment_id": "s01",
                        "entity_id": "person_001",
                        "text": "الاسم: مسلم",
                        "translated_name": "Musallam",
                    }
                ],
            }
        ],
    }
    body = client.post("/v1/bundles/review", json=next_bundle).json()
    assert body["items"][0]["reason"] == "dictionary_match" and body["counts"]["confirmed"] == 1
    # 다른 고객은 그 사전을 보지 않는다
    other = dict(next_bundle, bundle_id="bundle_sample_003", customer_id="someone_else")
    assert client.post("/v1/bundles/review", json=other).json()["items"][0]["reason"] == "no_evidence"


def test_close_pending_errors(client):
    client.post("/v1/bundles/review", json=SAMPLE)
    assert client.post("/v1/dictionary", json={"bundle_id": "nope", "mention_id": "x"}).status_code == 404
    assert client.post("/v1/dictionary", json={"bundle_id": "bundle_sample_001", "mention_id": "x"}).status_code == 404
    no_customer = dict(SAMPLE, bundle_id="b_no_customer")
    no_customer.pop("customer_id")
    client.post("/v1/bundles/review", json=no_customer)
    r = client.post("/v1/dictionary", json={"bundle_id": "b_no_customer", "mention_id": "contract_001:s01:1"})
    assert r.status_code == 400 and "customer_id" in r.json()["error"]


def test_db_unreachable_refuses_bundle_review(tmp_path):
    rt = build_runtime(
        Settings(llm_backend="fake", results_dir=tmp_path, database_url="postgresql+psycopg://x:y@127.0.0.1:1/none"),
        analyze_fn=fake_analyze,
    )
    with TestClient(create_app(rt)) as c:
        r = c.post("/v1/bundles/review", json=SAMPLE)
        assert r.status_code == 503 and r.json()["kind"] == "config"


@pytest.mark.db
def test_bundle_review_is_stored_in_postgres(tmp_path):
    import os

    from tashkeel_check.web.db import Database

    url = os.environ["DATABASE_URL"]
    Database(url).create_all()
    rt = build_runtime(Settings(llm_backend="fake", results_dir=tmp_path, database_url=url), analyze_fn=fake_analyze)
    with TestClient(create_app(rt)) as c:
        bid = f"bundle_db_{tmp_path.name}"
        body = dict(SAMPLE, bundle_id=bid, customer_id=f"cust_{tmp_path.name}")
        assert c.post("/v1/bundles/review", json=body).status_code == 200
        assert c.post("/v1/bundles/review", json=body).status_code == 200  # 덮어쓰기
        items = c.get(f"/v1/bundles/{bid}/items").json()
        assert len(items) == 2 and {i["status"] for i in items} == {"confirmed", "pending"}
        pend = c.get(f"/v1/bundles/{bid}/pending").json()[0]
        r = c.post(
            "/v1/dictionary", json={"bundle_id": bid, "mention_id": pend["mention_id"], "english_name": "Musallam"}
        )
        assert r.status_code == 201
    # 서버를 다시 띄워도 남아 있다(가이드 7단계 완료 기준)
    rt2 = build_runtime(Settings(llm_backend="fake", results_dir=tmp_path, database_url=url), analyze_fn=fake_analyze)
    with TestClient(create_app(rt2)) as c:
        assert len(c.get(f"/v1/bundles/{bid}/items").json()) == 2
        assert c.get(f"/v1/bundles/{bid}").json()["bundle_id"] == bid
        # 근거 서류 없이 계약서만 다시 보내면 사람 항목은 사전으로 확정되고 회사 항목은 근거 없음이다
        contract_only = json.loads(json.dumps(dict(body, bundle_id=bid + "_2", documents=body["documents"][:1])))
        contract_only["documents"][0]["segments"][0]["translated_name"] = "Musallam"
        again = c.post("/v1/bundles/review", json=contract_only).json()
        assert {i["reason"] for i in again["items"]} == {"dictionary_match", "no_evidence"}
