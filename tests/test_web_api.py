"""단계 1.5 API(FastAPI TestClient + 가짜 모델). DB는 DATABASE_URL이 닿을 때만(db 마커)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from tashkeel_check.config import Settings
from tashkeel_check.errors import ConfigError
from tashkeel_check.fake import FakeAgentModel, practice_responder, tool_call
from tashkeel_check.web.app import build_runtime, create_app

from .conftest import fake_analyze

ARABIC = "وكالة خاصة\nحضر السيد سالم بن حمد المسلم، إماراتي الجنسية.\nPrincipal: Salem bin Hamad Al Muslim\n"


def _settings(tmp_path: Path, **kw) -> Settings:
    return Settings(llm_backend="fake", results_dir=tmp_path, **kw)


@pytest.fixture
def client(tmp_path):
    rt = build_runtime(_settings(tmp_path), analyze_fn=fake_analyze)
    with TestClient(create_app(rt)) as c:
        yield c


def _events(client: TestClient, job_id: str) -> list[dict]:
    out = []
    with client.stream("GET", f"/v1/jobs/{job_id}/events") as r:
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
        for line in r.iter_lines():
            if line.startswith("data:"):
                out.append(json.loads(line[5:]))
    return out


def _finish(client: TestClient, body: dict) -> tuple[str, list[dict]]:
    r = client.post("/v1/reviews", json=body)
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]
    return job_id, _events(client, job_id)


def test_health_reports_backend_analyzer_db_and_mcp(client):
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["backend"] == "fake" and h["model"] == "fake-agent"
    assert h["analyzer"]["db"] == "calima-msa-r13"
    assert h["db"] == "disabled" and h["mcp"] == "disabled"
    assert h["nodes"] == ["load", "analyze", "agent", "validate", "reconcile", "export"]


def test_samples_list_and_detail_without_gold(client):
    rows = client.get("/v1/samples").json()
    assert [r["doc_id"] for r in rows][:2] == ["dev_001", "dev_002"] and len(rows) == 10
    assert {"doc_id", "evidence_layout"} <= set(rows[0])
    d = client.get("/v1/samples/dev_005").json()
    assert d["doc_id"] == "dev_005" and d["segments"][0]["segment_id"] == "s01"
    assert "gold" not in d and "evidence_roles" not in d
    assert client.get("/v1/samples/eval_001").status_code == 404  # eval은 화면에 내지 않는다
    assert client.get("/v1/samples/../dev_001").status_code in (404, 400)


@pytest.mark.parametrize(
    ("body", "msg"),
    [
        ({"text": "   \n"}, "빈 입력"),
        ({"segments": []}, "빈 입력"),
        ({"text": "Principal: Salem bin Hamad"}, "아랍어 토큰이 없습니다"),
        ({"text": ARABIC, "condition": "C9"}, "조건은"),
        ({"doc_id": "nope"}, "샘플 문서가 없습니다"),
    ],
)
def test_bad_input_is_400_with_reason(client, body, msg):
    r = client.post("/v1/reviews", json=body)
    assert r.status_code == 400 and msg in r.json()["error"] and r.json()["kind"] == "input"


@pytest.mark.parametrize("condition", ["C0", "C1", "C2", "C3"])
def test_pasted_text_runs_every_condition_and_writes_files(client, tmp_path, condition):
    job_id, events = _finish(client, {"text": ARABIC, "condition": condition})
    names = [e["event"] for e in events]
    assert names[0] == "queued" and names[-1] == "done"
    assert [e["node"] for e in events if e["event"] == "node"] == [
        "load",
        "analyze",
        "agent",
        "validate",
        "reconcile",
        "export",
    ]
    res = client.get(f"/v1/jobs/{job_id}/result")
    assert res.status_code == 200
    body = res.json()
    assert body["condition"] == condition and body["metrics"]["valid_output"] and body["errors"] == []
    assert [s["segment_id"] for s in body["segments"]] == ["s01", "s02", "s03"]
    assert body["job"]["status"] == "done" and body["job"]["source"] == "paste"
    out = tmp_path / "web" / job_id
    expected = ["metrics.json", "proper_nouns.csv", "run_meta.json", "segments.json"]
    assert sorted(p.name for p in out.iterdir()) == expected
    assert client.get(f"/v1/jobs/{job_id}").json()["status"] == "done"
    assert client.get("/v1/jobs").json()[0]["job_id"] == job_id


def test_sample_document_runs_with_gold_metrics(client):
    job_id, events = _finish(client, {"doc_id": "dev_005", "condition": "C2"})
    body = client.get(f"/v1/jobs/{job_id}/result").json()
    assert body["doc_id"] == "dev_005" and body["job"]["source"] == "sample"
    assert body["metrics"]["n_gold_name_tokens"] > 0  # 샘플은 정답이 있어 gold 지표가 나온다
    assert body["proper_nouns"]


def test_format_error_is_retried_once_and_recorded(tmp_path):
    """첫 응답이 구간을 빠뜨리면 validate가 한 번 다시 시키고, attempts=2가 이벤트와 결과에 남는다."""
    calls = {"n": 0}

    def responder(messages, bound) -> AIMessage:
        calls["n"] += 1
        if calls["n"] == 1:
            return tool_call("AgentOutput", {"translation": [{"segment_id": "s01", "english": "x"}], "items": []})
        return practice_responder(messages, bound)

    rt = build_runtime(_settings(tmp_path), model=FakeAgentModel(responder=responder), analyze_fn=fake_analyze)
    with TestClient(create_app(rt)) as c:
        job_id, events = _finish(c, {"text": ARABIC, "condition": "C1"})
        agent_attempts = [e["attempts"] for e in events if e["event"] == "node" and e["node"] == "agent"]
        assert agent_attempts == [1, 2]
        first_validate = next(e for e in events if e["event"] == "node" and e["node"] == "validate")
        assert first_validate["valid"] is False and "segments missing" in first_validate["last_error"]
        body = c.get(f"/v1/jobs/{job_id}/result").json()
        assert body["metrics"]["attempts"] == 2 and body["metrics"]["valid_output"]
        assert len(body["errors"]) == 1 and "segments missing" in body["errors"][0]
        assert c.get(f"/v1/jobs/{job_id}").json()["attempts"] == 2


def test_result_before_done_is_409_and_unknown_job_404(client):
    assert client.get("/v1/jobs/nope").status_code == 404
    assert client.get("/v1/jobs/nope/result").status_code == 404
    assert client.get("/v1/jobs/nope/events").status_code == 404


def test_missing_key_refuses_to_start(clean_env):
    """LLM_BACKEND=openai(기본)인데 키가 없으면 ConfigError. 조용히 가짜로 떨어지지 않는다."""
    with pytest.raises(ConfigError, match="OPENAI_API_KEY"):
        build_runtime(Settings(), analyze_fn=fake_analyze)


def test_fake_backend_only_when_explicit(tmp_path):
    rt = build_runtime(_settings(tmp_path), analyze_fn=fake_analyze)
    assert rt.backend == "fake" and isinstance(rt.model, FakeAgentModel)


def test_db_unreachable_starts_but_refuses_reviews(tmp_path):
    """DB 불통: 기동은 되고 /health가 db=false, 검수 작업 생성은 503."""
    bad = "postgresql+psycopg://nobody:nope@127.0.0.1:1/none?connect_timeout=1"
    rt = build_runtime(_settings(tmp_path, database_url=bad), analyze_fn=fake_analyze)
    with TestClient(create_app(rt)) as c:
        assert c.get("/health").json()["db"] is False
        r = c.post("/v1/reviews", json={"text": ARABIC})
        assert r.status_code == 503 and "DB" in r.json()["error"] and r.json()["kind"] == "config"


def test_static_form_is_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "Tashkeel Check" in r.text and "EventSource" in r.text
    assert "API 키" in r.text and "대상 지정" in r.text and "/v1/bundles/draft" in r.text  # ADR-019 화면


@pytest.mark.db
def test_results_are_stored_in_postgres(tmp_path):
    url = os.environ["DATABASE_URL"]
    rt = build_runtime(_settings(tmp_path, database_url=url), analyze_fn=fake_analyze)
    assert rt.db is not None
    rt.db.create_all()
    with TestClient(create_app(rt)) as c:
        assert c.get("/health").json()["db"] is True
        job_id, events = _finish(c, {"doc_id": "dev_005", "condition": "C3"})
        done = events[-1]
        assert done["event"] == "done" and done["run_id"] and done["db_error"] is None
        job = c.get(f"/v1/jobs/{job_id}").json()
        assert job["document_id"] and job["run_id"] == done["run_id"]
        stored = rt.db.run_for_job(job_id)
        assert stored is not None and stored["result"]["doc_id"] == "dev_005"
        assert stored["result"]["segments"]  # 번역은 runs.result JSONB에 있다
        n_items = rt.db.count_name_items(stored["run_id"])
        body = c.get(f"/v1/jobs/{job_id}/result").json()
        assert n_items == sum(1 for it in body["items"] if it["type"] == "proper_noun")
        assert rt.db.recent_jobs(5)[0]["job_id"] == job_id


def test_m1_runs_when_multi_agent_is_enabled(tmp_path):
    rt = build_runtime(_settings(tmp_path, multi_agent=True), analyze_fn=fake_analyze)
    with TestClient(create_app(rt)) as c:
        h = c.get("/health").json()
        assert h["multi_agent"] is True and h["conditions"] == ["C0", "C1", "C2", "C3", "M1"]
        job_id, events = _finish(c, {"text": ARABIC, "condition": "M1"})
        assert events[-1]["event"] == "done" and events[-1]["valid_output"]
        body = c.get(f"/v1/jobs/{job_id}/result").json()
        assert body["condition"] == "M1" and body["metrics"]["engine"]["translator"]["llm_calls"] == 1
        assert body["metrics"]["usage"]["llm_calls"] == 2
