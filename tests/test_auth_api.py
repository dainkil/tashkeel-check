"""API 키 인증·고객 분리·사용량(ADR-019). 가짜 모델, 메모리 저장소. Postgres는 db 마커."""

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
SAMPLE.pop("customer_id")  # 인증된 요청은 서버가 키의 고객을 채운다
ARABIC = "وكالة خاصة\nحضر السيد سالم بن حمد المسلم، إماراتي الجنسية.\nPrincipal: Salem bin Hamad Al Muslim\n"


def _rt(tmp_path, **kw):
    return build_runtime(Settings(llm_backend="fake", results_dir=tmp_path, **kw), analyze_fn=fake_analyze)


def _finish_job(client: TestClient, body: dict, headers: dict | None = None) -> str:
    r = client.post("/v1/reviews", json=body, headers=headers or {})
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]
    with client.stream("GET", f"/v1/jobs/{job_id}/events", headers=headers or {}) as s:
        for _ in s.iter_lines():
            pass
    return job_id


def test_auto_mode_is_open_until_a_customer_exists(tmp_path):
    rt = _rt(tmp_path)
    with TestClient(create_app(rt)) as c:
        assert c.get("/health").json()["auth"] == "disabled"
        assert c.post("/v1/bundles/review", json=SAMPLE).status_code == 200
        rt.customers.add("acme")
        assert c.get("/health").json()["auth"] == "required"
        r = c.post("/v1/bundles/review", json=SAMPLE)
        assert r.status_code == 401 and r.json()["kind"] == "auth"
        assert c.get("/health").status_code == 200  # 공개
        assert c.get("/").status_code == 200


def test_key_in_header_bearer_or_query(tmp_path):
    rt = _rt(tmp_path)
    acme, key = rt.customers.add("acme")
    with TestClient(create_app(rt)) as c:
        assert c.post("/v1/bundles/review", json=SAMPLE, headers={"X-API-Key": key}).status_code == 200
        assert c.get("/v1/bundles", headers={"Authorization": f"Bearer {key}"}).status_code == 200
        assert c.get(f"/v1/bundles?api_key={key}").status_code == 200
        assert c.get("/v1/bundles", headers={"X-API-Key": "tk_wrong"}).status_code == 401
        body = c.get("/v1/bundles/bundle_sample_001", headers={"X-API-Key": key}).json()
        assert body["customer_id"] == acme.id  # 서버가 키의 고객을 채운다


def test_body_customer_id_must_match_key(tmp_path):
    rt = _rt(tmp_path)
    _, key = rt.customers.add("acme")
    h = {"X-API-Key": key}
    with TestClient(create_app(rt)) as c:
        r = c.post("/v1/bundles/review", json=dict(SAMPLE, customer_id="someone_else"), headers=h)
        assert r.status_code == 400 and "API 키의 고객" in r.json()["error"]
        files = [("files", ("b.json", json.dumps(SAMPLE).encode(), "application/json"))]
        r = c.post("/v1/bundles", files=files, data={"customer_id": "someone_else"}, headers=h)
        assert r.status_code == 400


def test_customers_are_separated(tmp_path):
    rt = _rt(tmp_path)
    a_cust, a = rt.customers.add("a")
    _, b = rt.customers.add("b")
    ha, hb = {"X-API-Key": a}, {"X-API-Key": b}
    with TestClient(create_app(rt)) as c:
        assert c.post("/v1/bundles/review", json=SAMPLE, headers=ha).status_code == 200
        assert c.post("/v1/bundles/review", json=SAMPLE, headers=hb).status_code == 200  # 같은 bundle_id
        assert [x["bundle_id"] for x in c.get("/v1/bundles", headers=ha).json()] == ["bundle_sample_001"]
        assert len(c.get("/v1/bundles", headers=hb).json()) == 1
        # a의 항목을 b 키로는 못 본다
        assert c.get("/v1/bundles/bundle_sample_001/items", headers=ha).status_code == 200
        pend = c.get("/v1/bundles/bundle_sample_001/pending", headers=ha).json()[0]
        rid = c.post("/v1/bundles/bundle_sample_001/reviews?condition=C1", headers=ha).json()["review_id"]
        assert c.get(f"/v1/bundles/bundle_sample_001/reviews/{rid}", headers=hb).status_code == 404
        assert c.get(f"/v1/bundles/bundle_sample_001/reviews/{rid}/events", headers=hb).status_code == 404
        assert c.get(f"/v1/bundles/bundle_sample_001/reviews/{rid}", headers=ha).status_code == 200
        # 사전 등록은 키의 고객으로(본문 customer_id 없이도)
        r = c.post(
            "/v1/dictionary", json={"bundle_id": "bundle_sample_001", "mention_id": pend["mention_id"]}, headers=ha
        )
        assert r.status_code == 201 and r.json()["customer_id"] == a_cust.id
        # 단일 문서 작업도 분리
        job = _finish_job(c, {"text": ARABIC, "condition": "C1"}, ha)
        assert c.get(f"/v1/jobs/{job}", headers=hb).status_code == 404
        assert c.get(f"/v1/jobs/{job}/result", headers=hb).status_code == 404
        assert c.get(f"/v1/jobs/{job}", headers=ha).json()["customer_id"] == a_cust.id
        listed = c.get("/v1/jobs", headers=ha).json()  # 묶음 LLM 검수의 서류별 작업 3개 + 단일 문서 1개
        assert job in [j["job_id"] for j in listed] and {j["customer_id"] for j in listed} == {a_cust.id}
        assert c.get("/v1/jobs", headers=hb).json() == []


def test_revoke_and_explicit_modes(tmp_path):
    rt = _rt(tmp_path)
    cust, key = rt.customers.add("acme")
    with TestClient(create_app(rt)) as c:
        assert c.get("/v1/bundles", headers={"X-API-Key": key}).status_code == 200
        rt.customers.revoke(cust.id)
        assert c.get("/v1/bundles", headers={"X-API-Key": key}).status_code == 401
        assert c.get("/health").json()["auth"] == "disabled"  # 활성 고객 0 → auto는 다시 열림
    rt2 = _rt(tmp_path, auth="required")
    with TestClient(create_app(rt2)) as c:
        assert c.get("/health").json()["auth"] == "required"
        assert c.get("/v1/bundles").status_code == 401
    rt3 = _rt(tmp_path, auth="disabled")
    rt3.customers.add("acme")
    with TestClient(create_app(rt3)) as c:
        assert c.get("/v1/bundles").status_code == 200


def test_usage_is_recorded_per_customer(tmp_path):
    rt = _rt(tmp_path)
    _, a = rt.customers.add("a")
    _, b = rt.customers.add("b")
    ha, hb = {"X-API-Key": a}, {"X-API-Key": b}
    with TestClient(create_app(rt)) as c:
        _finish_job(c, {"text": ARABIC, "condition": "C1"}, ha)
        assert c.post("/v1/bundles/review", json=SAMPLE, headers=ha).status_code == 200
        body = c.get("/v1/usage", headers=ha).json()
        n_bundle_segments = sum(len(d["segments"]) for d in SAMPLE["documents"])
        assert body["totals"]["jobs"] == 2 and body["totals"]["segments"] == 3 + n_bundle_segments
        assert {k["kind"]: k["jobs"] for k in body["by_kind"]} == {"bundle_label": 1, "document": 1}
        assert body["totals"]["llm_calls"] >= 1  # 가짜 모델도 호출 수는 센다
        assert c.get("/v1/usage", headers=hb).json()["totals"]["jobs"] == 0
        assert c.get("/v1/usage?from=2026-01-01&to=2026-01-02", headers=ha).json()["totals"]["jobs"] == 0
        assert c.get("/v1/usage?from=nope", headers=ha).status_code == 400
        assert c.get("/v1/usage?from=2026-02-01&to=2026-01-01", headers=ha).status_code == 400


def test_m1_condition_is_rejected_unless_enabled(tmp_path):
    with TestClient(create_app(_rt(tmp_path))) as c:
        r = c.post("/v1/reviews", json={"text": ARABIC, "condition": "M1"})
        assert r.status_code == 400 and "MULTI_AGENT" in r.json()["error"]
        assert c.get("/health").json()["conditions"] == ["C0", "C1", "C2", "C3", "M2"]
        assert c.get("/health").json()["multi_agent"] is False


@pytest.mark.db
def test_customers_and_usage_persist_in_postgres(tmp_path):
    from .conftest import DB_URL

    rt = _rt(tmp_path, database_url=DB_URL)
    assert rt.db is not None
    rt.db.create_all()
    a_cust, a = rt.customers.add(f"a_{tmp_path.name}")
    _, b = rt.customers.add(f"b_{tmp_path.name}")
    bid = f"bundle_auth_{tmp_path.name}"
    body = dict(SAMPLE, bundle_id=bid)
    with TestClient(create_app(rt)) as c:
        assert c.post("/v1/bundles/review", json=body, headers={"X-API-Key": a}).status_code == 200
        assert c.post("/v1/bundles/review", json=body, headers={"X-API-Key": b}).status_code == 200
        assert c.post("/v1/bundles/review", json=body, headers={"X-API-Key": a}).status_code == 200  # 덮어쓰기
        assert c.get(f"/v1/bundles/{bid}", headers={"X-API-Key": a}).json()["customer_id"] == a_cust.id
        assert c.get("/v1/usage", headers={"X-API-Key": a}).json()["totals"]["jobs"] == 2
    rt2 = _rt(tmp_path, database_url=DB_URL)
    with TestClient(create_app(rt2)) as c:
        assert c.get(f"/v1/bundles/{bid}/items", headers={"X-API-Key": a}).status_code == 200
        assert c.get(f"/v1/bundles/{bid}/items", headers={"X-API-Key": b}).status_code == 200
        assert c.get(f"/v1/bundles/{bid}/items").status_code == 401  # 활성 고객이 있으니 auto = required
        assert (
            len([r for r in c.get("/v1/bundles?limit=200", headers={"X-API-Key": a}).json() if r["bundle_id"] == bid])
            == 1
        )
    # 다른 테스트가 auto 모드에서 막히지 않게 정리
    rt.customers.revoke(a_cust.id)
    for cust in rt.customers.list():
        if cust.active and cust.name.endswith(tmp_path.name):
            rt.customers.revoke(cust.id)
