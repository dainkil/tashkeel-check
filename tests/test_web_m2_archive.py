"""서비스 기본 경로 M2(ADR-022): 올린 서류가 보관함에 들어가고, 다음 서류에서 보관함 제안 → 사람이 확정 → 그다음 서류는
사전 확정. 고객 분리, 보관함 삭제, 범위 토큰 폐기, 묶음 경로 거부, C1로 되돌리기. 가짜 모델(연습 모드), DB 없음."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from tashkeel_check.config import Settings
from tashkeel_check.text import segment_text, tokenize
from tashkeel_check.web.app import build_runtime, create_app

from .conftest import fake_analyze

LEASE = "عقد إيجار\nالمؤجر: نوال الحربي (Nawal Al-Harbi)\nالمستأجر شركة الريان\n"
NOTICE = "إشعار حكومي\nالسيدة نوال الحربي مطلوبة\n"


def _rt(tmp_path, **kw):
    return build_runtime(Settings(llm_backend="fake", results_dir=tmp_path, **kw), analyze_fn=fake_analyze)


def _upload(c: TestClient, name: str, text: str, headers: dict | None = None) -> dict:
    r = c.post("/v1/reviews/upload", files={"file": (name, text.encode("utf-8"))}, headers=headers or {})
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]
    with c.stream("GET", f"/v1/jobs/{job_id}/events", headers=headers or {}) as s:
        events = [json.loads(ln[5:]) for ln in s.iter_lines() if ln.startswith("data:")]
    assert events[-1]["event"] == "done", events[-1]
    res = c.get(f"/v1/jobs/{job_id}/result", headers=headers or {}).json()
    res["_done"] = events[-1]
    return res


def _ids(text: str, word: str) -> list[int]:
    return [t["id"] for t in tokenize(segment_text(text)) if t["text"] == word]


@pytest.fixture
def rt(tmp_path):
    return _rt(tmp_path)


def test_health_reports_m2_default_and_records_server(rt):
    with TestClient(create_app(rt)) as c:
        h = c.get("/health").json()
    assert h["default_condition"] == "M2" and h["records_mcp"] is True and "M2" in h["conditions"]
    assert h["archive"] == {"store": "memory", "embeddings": "practice-char-ngram"}


def test_archive_suggestion_then_confirm_then_dictionary_on_next_document(rt):
    with TestClient(create_app(rt)) as c:
        lease = _upload(c, "lease.txt", LEASE)
        assert lease["condition"] == "M2" and lease["archive"] == []
        assert lease["job"]["archived_passages"] == 2 and lease["_done"]["records_calls"] == 2
        docs = c.get("/v1/archive").json()
        assert docs["customer_id"] == "local" and [d["document_label"] for d in docs["documents"]] == ["lease.txt"]

        notice = _upload(c, "notice.txt", NOTICE)
        by_tokens = {tuple(o["token_ids"]): o for o in notice["archive"]}
        nawal = by_tokens[tuple(_ids(NOTICE, "نوال"))]
        assert nawal["status"] == "archive_suggest" and nawal["agreement"] == "both"
        (s,) = nawal["suggestions"]
        assert s["spelling"] == "Nawal" and s["document_id"] == lease["job"]["archive_id"]
        assert "Nawal Al-Harbi" in s["quote"] and notice["_done"]["archive_suggestions"] == 2
        # 제안은 확정이 아니다: 결과의 처분은 보류 그대로
        held = {tuple(i["token_ids"]): i["final_decision"] for i in notice["items"]}
        assert held[tuple(_ids(NOTICE, "نوال"))] == "hold"

        r = c.post(
            "/v1/dictionary",
            json={"job_id": notice["job"]["job_id"], "token_ids": _ids(NOTICE, "نوال"), "archive_hit_id": s["hit_id"]},
        )
        assert r.status_code == 201, r.text
        entry = r.json()
        assert entry["english_name"] == "Nawal" and entry["evidence_document_id"] == lease["job"]["archive_id"]
        again = c.get(f"/v1/jobs/{notice['job']['job_id']}/result").json()
        assert tuple(_ids(NOTICE, "نوال")) not in {tuple(o["token_ids"]) for o in again["archive"]}
        assert any(o["status"] == "dictionary_adopt" for o in again["dictionary"])

        bad = c.post(
            "/v1/dictionary",
            json={"job_id": notice["job"]["job_id"], "token_ids": _ids(NOTICE, "الحربي"), "archive_hit_id": "nope"},
        )
        assert bad.status_code == 400

        third = _upload(c, "notice2.txt", NOTICE + "تاريخ\n")
        dict_hits = [o for o in third["dictionary"] if o["status"] == "dictionary_adopt"]
        assert [o["english"] for o in dict_hits] == ["Nawal"]
        assert tuple(_ids(NOTICE, "نوال")) not in {tuple(o["token_ids"]) for o in third["archive"]}  # 사전이 이긴다
    assert len(rt.scopes) == 0  # 작업마다 발급한 범위 토큰은 끝나면 없앤다


def test_reuploading_the_same_file_does_not_suggest_itself(rt):
    with TestClient(create_app(rt)) as c:
        _upload(c, "lease.txt", LEASE)
        again = _upload(c, "lease-copy.txt", LEASE)
    assert again["archive"] == []


def test_deleting_from_archive_removes_its_suggestions(rt):
    with TestClient(create_app(rt)) as c:
        lease = _upload(c, "lease.txt", LEASE)
        notice = _upload(c, "notice.txt", NOTICE)
        assert notice["archive"]
        r = c.delete(f"/v1/archive/{lease['job']['archive_id']}")
        assert r.status_code == 200
        assert c.get(f"/v1/jobs/{notice['job']['job_id']}/result").json()["archive"] == []
        assert c.get("/v1/archive").json()["documents"][0]["document_label"] == "notice.txt"
        assert c.delete("/v1/archive/nope").status_code == 404
        later = _upload(c, "notice2.txt", NOTICE + "تاريخ\n")
    assert later["archive"] == []


def test_customers_have_separate_archives(rt):
    acme, key_a = rt.customers.add("acme")
    _, key_b = rt.customers.add("beta")
    a, b = {"X-API-Key": key_a}, {"X-API-Key": key_b}
    with TestClient(create_app(rt)) as c:
        _upload(c, "lease.txt", LEASE, a)
        assert _upload(c, "notice.txt", NOTICE, a)["archive"]
        assert _upload(c, "notice.txt", NOTICE, b)["archive"] == []
        assert c.get("/v1/archive", headers=b).json()["documents"][0]["document_label"] == "notice.txt"
        assert c.get("/v1/archive", headers=a).json()["customer_id"] == acme.id


def test_bundle_review_rejects_m2(rt):
    with TestClient(create_app(rt)) as c:
        r = c.post("/v1/bundles/any/reviews", params={"condition": "M2"})
    assert r.status_code == 400 and "M2" in r.json()["error"]


def test_review_condition_c1_rolls_back_the_default(tmp_path):
    with TestClient(create_app(_rt(tmp_path, review_condition="C1"))) as c:
        assert c.get("/health").json()["default_condition"] == "C1"
        res = _upload(c, "lease.txt", LEASE)
        assert res["condition"] == "C1" and res["job"]["archived_passages"] == 2  # C1도 보관함에는 넣는다
        r = c.post("/v1/reviews", json={"text": NOTICE, "condition": "M2"})  # 요청마다 고를 수는 있다
        assert r.status_code == 202 and r.json()["condition"] == "M2"
        with c.stream("GET", f"/v1/jobs/{r.json()['job_id']}/events") as s:
            assert s.status_code == 200 and list(s.iter_lines())
