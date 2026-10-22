"""파일 업로드 → 검수 → 후보 확정 → 회사 사전 → 다음 문서에서 자동 확정(ADR-021). 가짜 모델, DB 없음.

짜 둔 가짜 모델이 C1 출력 형식(AgentOutput)으로 답하므로 서버 기본 조건을 C1로 둔다. M2 흐름은 test_web_m2_archive.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tashkeel_check.config import Settings
from tashkeel_check.fake import OUTPUT_TOOL, FakeAgentModel, tool_call
from tashkeel_check.text import segment_text, tokenize
from tashkeel_check.web.app import build_runtime, create_app

from .conftest import fake_analyze

ARABIC = "وكالة خاصة\nحضر السيد سالم بن حمد المسلم، إماراتي الجنسية.\nPrincipal: Salem bin Hamad Al Muslim\n"
FAMILY = "المسلم"


def _family_ids() -> list[int]:
    toks = tokenize(segment_text(ARABIC))
    return [t["id"] for t in toks if t["text"] == FAMILY]


def _holding_model() -> FakeAgentModel:
    """가짜 모델: 가문명 المسلم을 후보 둘과 함께 보류한다(근거 인용 없음)."""
    segs = segment_text(ARABIC)
    out = {
        "translation": [{"segment_id": s["segment_id"], "english": "x"} for s in segs],
        "items": [
            {
                "token_ids": _family_ids(),
                "type": "proper_noun",
                "candidates": [
                    {"reading": None, "romanized": "Al Muslim", "source": "llm"},
                    {"reading": None, "romanized": "Al Musallam", "source": "llm"},
                ],
                "decision": "hold",
                "adopted": None,
                "reason": "two readings",
                "confidence": None,
                "evidence": None,
            }
        ],
    }
    reply = tool_call(OUTPUT_TOOL, out)
    return FakeAgentModel(responder=lambda messages, bound: reply)


@pytest.fixture
def client(tmp_path: Path):
    rt = build_runtime(
        Settings(llm_backend="fake", results_dir=tmp_path, review_condition="C1"),
        model=_holding_model(),
        analyze_fn=fake_analyze,
    )
    with TestClient(create_app(rt)) as c:
        yield c


def _wait(client: TestClient, job_id: str) -> list[dict]:
    out = []
    with client.stream("GET", f"/v1/jobs/{job_id}/events") as r:
        for line in r.iter_lines():
            if line.startswith("data:"):
                out.append(json.loads(line[5:]))
    return out


def _upload(client: TestClient, name: str = "contract.txt", data: bytes | None = None, **form) -> dict:
    r = client.post("/v1/reviews/upload", files={"file": (name, data or ARABIC.encode("utf-8"))}, data=form)
    assert r.status_code == 202, r.text
    body = r.json()
    events = _wait(client, body["job_id"])
    assert events[-1]["event"] == "done", events[-1]
    return body


def test_health_reports_prompt_ocr_and_dictionary_customer(client):
    h = client.get("/health").json()
    assert h["prompt_version"] == "p1" and h["ocr"] == "none" and h["dictionary_customer"] == "local"


def test_upload_txt_runs_configured_condition_and_result_has_dictionary_section(client, tmp_path):
    body = _upload(client)
    assert body["condition"] == "C1" and body["doc_id"] == "contract"
    assert body["extracted"] == {"source": "text", "backend": None, "pages": 1, "n_segments": 3, "warnings": []}
    res = client.get(f"/v1/jobs/{body['job_id']}/result").json()
    assert res["job"]["source"] == "upload" and res["meta"]["prompt_version"] == "p1"
    assert res["dictionary"] == [] and res["dictionary_customer"] == "local"
    assert [i["final_decision"] for i in res["items"] if i["type"] == "proper_noun"] == ["hold"]
    assert (tmp_path / "web" / body["job_id"] / "proper_nouns.csv").exists()


@pytest.mark.parametrize(
    ("name", "data", "msg"),
    [
        ("x.docx", b"abc", "받지 않는 파일 형식"),
        ("scan.png", b"\x89PNG", "문자 인식 백엔드가 없어"),
        ("empty.txt", b"", "빈 파일"),
        ("latin.txt", b"Principal: Salem", "아랍어 토큰이 없습니다"),
    ],
)
def test_bad_uploads_are_400(client, name, data, msg):
    r = client.post("/v1/reviews/upload", files={"file": (name, data)})
    assert r.status_code == 400 and msg in r.json()["error"], r.text
    r = client.post("/v1/extract", files={"file": (name, data)})
    assert r.status_code == 400


def test_upload_size_limit(tmp_path):
    rt = build_runtime(
        Settings(llm_backend="fake", results_dir=tmp_path, upload_max_bytes=10),
        model=_holding_model(),
        analyze_fn=fake_analyze,
    )
    with TestClient(create_app(rt)) as c:
        r = c.post("/v1/reviews/upload", files={"file": ("a.txt", ARABIC.encode("utf-8"))})
        assert r.status_code == 400 and "너무 큽니다" in r.json()["error"]


def test_bad_condition_on_upload_is_400(client):
    r = client.post("/v1/reviews/upload", files={"file": ("a.txt", ARABIC.encode("utf-8"))}, data={"condition": "C9"})
    assert r.status_code == 400 and "조건은" in r.json()["error"]


def test_extract_only_returns_text_and_segments(client):
    r = client.post("/v1/extract", files={"file": ("contract.md", ARABIC.encode("utf-8"))})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "text" and len(body["segments"]) == 3 and body["segments"][1]["segment_id"] == "s02"


def test_confirm_candidate_then_next_document_is_dictionary_adopt_then_delete(client):
    first = _upload(client)
    ids = _family_ids()

    # 1) 후보를 눌러 확정 → 사전 등록(고객 "local", 대상 "*")
    r = client.post("/v1/dictionary", json={"job_id": first["job_id"], "token_ids": ids, "english_name": "Al Musallam"})
    assert r.status_code == 201, r.text
    entry = r.json()
    assert entry["customer_id"] == "local" and entry["entity_id"] == "*" and entry["english_name"] == "Al Musallam"
    assert entry["arabic_name"] == FAMILY and entry["id"]
    # 같은 작업의 결과에도 바로 반영된다
    res1 = client.get(f"/v1/jobs/{first['job_id']}/result").json()
    assert [o["status"] for o in res1["dictionary"]] == ["dictionary_adopt"] and res1["dictionary"][0][
        "english"
    ] == "Al Musallam"

    # 2) 목록
    lst = client.get("/v1/dictionary").json()
    assert lst["customer_id"] == "local" and [e["id"] for e in lst["entries"]] == [entry["id"]]

    # 3) 같은 이름이 든 다음 문서는 처음부터 사전으로 확정된다
    second = _upload(client, name="letter.txt")
    res2 = client.get(f"/v1/jobs/{second['job_id']}/result").json()
    assert [i["final_decision"] for i in res2["items"] if i["type"] == "proper_noun"] == ["hold"]  # 모델 출력은 그대로
    assert len(res2["dictionary"]) == 1
    ov = res2["dictionary"][0]
    assert ov["status"] == "dictionary_adopt" and ov["english"] == "Al Musallam" and ov["token_ids"] == ids
    assert ov["entry_id"] == entry["id"]
    done = [e for e in _wait(client, second["job_id"]) if e["event"] == "done"][0]
    assert done["dictionary_hits"] == 1

    # 4) 확정 취소 → 목록에서 빠지고 결과 덧씌움도 사라진다
    r = client.delete(f"/v1/dictionary/{entry['id']}")
    assert r.status_code == 200 and r.json()["deleted"] == entry["id"]
    assert client.get("/v1/dictionary").json()["entries"] == []
    assert client.get(f"/v1/jobs/{second['job_id']}/result").json()["dictionary"] == []
    assert client.delete(f"/v1/dictionary/{entry['id']}").status_code == 404


def test_dictionary_register_validation(client):
    first = _upload(client)
    bad = [
        ({}, "bundle_id + mention_id 또는 job_id + token_ids"),
        ({"job_id": first["job_id"], "token_ids": []}, "token_ids가 비어"),
        ({"job_id": first["job_id"], "token_ids": [999], "english_name": "x"}, "이름 항목이 없습니다"),
        ({"job_id": first["job_id"], "token_ids": _family_ids()}, "영문 표기를 입력"),
    ]
    for body, msg in bad:
        r = client.post("/v1/dictionary", json=body)
        assert r.status_code == 400 and msg in r.json()["error"], (body, r.text)
    r = client.post("/v1/dictionary", json={"job_id": "nope", "token_ids": [1], "english_name": "x"})
    assert r.status_code == 404
