"""가이드 9단계: 라벨 칸이 없는 문장의 고유명사를 LLM(가짜 모델)으로 뽑아 묶음 판정에 합류시킨다.

LLM 호출 실패(openai 오류)는 이름 미검출이 아니라 실행 오류(model_error)로 기록한다."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import httpx
import openai
import pytest
from fastapi.testclient import TestClient

from tashkeel_check.bundle.loader import split_bundle_gold
from tashkeel_check.config import Settings
from tashkeel_check.data.bundles import ENTITY_TYPES, generate_bundles
from tashkeel_check.fake import FakeAgentModel, practice_responder, tool_call
from tashkeel_check.web.app import build_runtime, create_app

from .conftest import fake_analyze

ROOT = Path(__file__).resolve().parents[1]
BASE_DOC = ROOT / "data" / "synthetic" / "dev" / "dev_001.json"
TOKEN_RE = re.compile(r"(\d+)=(\S+)")


@pytest.fixture(scope="module")
def model_error_bundles(tmp_path_factory) -> dict[str, dict]:
    out = tmp_path_factory.mktemp("llm")
    paths = generate_bundles(BASE_DOC, out, "dev")
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in paths if p.stem.endswith("_model_error")}


def _client(tmp_path, responder):
    rt = build_runtime(
        Settings(llm_backend="fake", results_dir=tmp_path),
        model=FakeAgentModel(responder=responder),
        analyze_fn=fake_analyze,
    )
    return TestClient(create_app(rt))


def _wait(client: TestClient, bundle_id: str, review_id: str, timeout: float = 30) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/v1/bundles/{bundle_id}/reviews/{review_id}").json()
        if body["status"] == "done":
            return body
        time.sleep(0.05)
    raise AssertionError("bundle review did not finish")


def _responder_adopting(name_words: set[str], adopted: str | None, decision: str):
    """TOKENS 표에서 이름 토큰을 찾아 proper_noun 항목 하나를 내는 가짜 모델."""

    def responder(messages, bound):
        text = next((str(m.content) for m in messages if m.type == "human"), "")
        seg_ids = re.findall(r"^\[(s\d+)\]", text, flags=re.M)
        ids = [int(i) for i, w in TOKEN_RE.findall(text.split("TOKENS", 1)[-1]) if w in name_words]
        items = []
        if ids:
            items.append(
                {
                    "token_ids": ids,
                    "type": "proper_noun",
                    "candidates": [{"reading": None, "romanized": adopted or "?", "source": "llm"}],
                    "decision": decision,
                    "adopted": adopted,
                    "reason": "test",
                    "confidence": 0.9 if adopted else None,
                    "evidence": None,
                }
            )
        return tool_call(
            "AgentOutput", {"translation": [{"segment_id": s, "english": "x"} for s in seg_ids], "items": items}
        )

    return responder


def _subject(bundle_obj: dict) -> tuple[str, str, str]:
    """(contract 구간의 아랍어 이름, 근거 영문 표기, 대상 ID)."""
    contract = bundle_obj["documents"][0]["segments"][1]
    evidence = bundle_obj["documents"][1]["segments"][1]["text"]
    english = evidence.split("|")[1].split(":", 1)[1].strip()
    arabic = contract["text"].replace("حضر ", "").replace(" بصفته طرفاً أول.", "")
    return arabic, english, contract["entity_id"]


@pytest.mark.parametrize("entity_type", ENTITY_TYPES)
def test_llm_item_without_adopted_spelling_gets_evidence_suggestion(tmp_path, model_error_bundles, entity_type):
    obj = model_error_bundles[f"dev_{entity_type}_model_error"]
    arabic, english, eid = _subject(obj)
    with _client(tmp_path, _responder_adopting(set(arabic.split()), None, "hold")) as c:
        bundle, _ = split_bundle_gold(obj)
        assert c.post("/v1/bundles/review", json=bundle.model_dump(mode="json")).status_code == 200
        r = c.post(f"/v1/bundles/{bundle.bundle_id}/reviews", params={"condition": "C1"})
        assert r.status_code == 202 and set(r.json()["jobs"]) == {"contract_001", "evidence_001"}
        body = _wait(c, bundle.bundle_id, r.json()["review_id"])
        llm_items = [i for i in body["items"] if ":llm" in i["mention_id"]]
        assert len(llm_items) == 1
        it = llm_items[0]
        assert (it["entity_id"], it["entity_type"], it["status"], it["reason"]) == (
            eid,
            entity_type,
            "pending",
            "no_translation",
        )
        assert it["suggestion"] == english and it["evidence"][0]["document_id"] == "evidence_001"
        assert body["errors"] == {} and body["counts"]["pending"] == 1
        # 저장소에도 합류한 결과가 남는다
        assert c.get(f"/v1/bundles/{bundle.bundle_id}/pending").json()[0]["mention_id"] == it["mention_id"]


def test_llm_adopted_spelling_is_compared_with_bundle_evidence(tmp_path, model_error_bundles):
    obj = model_error_bundles["dev_person_model_error"]
    arabic, english, _ = _subject(obj)
    bundle, _ = split_bundle_gold(obj)
    for adopted, reason, status in (
        (english, "evidence_match", "confirmed"),
        (english + "x", "translation_mismatch", "pending"),
    ):
        with _client(tmp_path, _responder_adopting(set(arabic.split()), adopted, "adopt")) as c:
            c.post("/v1/bundles/review", json=bundle.model_dump(mode="json"))
            r = c.post(f"/v1/bundles/{bundle.bundle_id}/reviews", params={"condition": "C1"})
            body = _wait(c, bundle.bundle_id, r.json()["review_id"])
            it = next(i for i in body["items"] if ":llm" in i["mention_id"])
            assert (it["status"], it["reason"], it["translated_name"]) == (status, reason, adopted)


def test_labeled_segments_keep_label_result_over_llm(tmp_path):
    sample = json.loads((ROOT / "data" / "bundles" / "sample_bundle.json").read_text(encoding="utf-8"))
    with _client(tmp_path, practice_responder) as c:
        c.post("/v1/bundles/review", json=sample)
        r = c.post("/v1/bundles/bundle_sample_001/reviews", params={"condition": "C2"})
        body = _wait(c, "bundle_sample_001", r.json()["review_id"])
        assert all(":llm" not in i["mention_id"] for i in body["items"])  # 라벨 칸 구간은 라벨 결과만
        assert body["counts"] == {"confirmed": 1, "pending": 1}


@pytest.mark.parametrize("entity_type", ENTITY_TYPES)
def test_api_failure_is_model_error_not_missing_name(tmp_path, model_error_bundles, entity_type):
    obj = model_error_bundles[f"dev_{entity_type}_model_error"]
    gold = obj["gold"]

    def failing(messages, bound):
        raise openai.APIConnectionError(request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"))

    with _client(tmp_path, failing) as c:
        bundle, _ = split_bundle_gold(obj)
        c.post("/v1/bundles/review", json=bundle.model_dump(mode="json"))
        r = c.post(f"/v1/bundles/{bundle.bundle_id}/reviews", params={"condition": "C1"})
        body = _wait(c, bundle.bundle_id, r.json()["review_id"])
        errors = [i for i in body["items"] if i["reason"] == "model_error"]
        assert {i["mention_id"] for i in errors} >= {g["mention_id"] for g in gold["review_items"]}
        assert all("APIConnectionError" in i["detail"] for i in errors)
        assert set(body["errors"]) == {"contract_001", "evidence_001"}


def test_bundle_review_errors(tmp_path):
    with _client(tmp_path, practice_responder) as c:
        assert c.post("/v1/bundles/nope/reviews").status_code == 404
        sample = json.loads((ROOT / "data" / "bundles" / "sample_bundle.json").read_text(encoding="utf-8"))
        c.post("/v1/bundles/review", json=sample)
        assert c.post("/v1/bundles/bundle_sample_001/reviews", params={"condition": "C9"}).status_code == 400
        assert c.get("/v1/bundles/bundle_sample_001/reviews/nope").status_code == 404
