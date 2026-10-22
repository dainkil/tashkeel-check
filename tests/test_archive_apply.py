"""보관함 제안 덧씌움(ADR-022): 원문 재확인, 두 역할 일치, 철자 충돌, 사전이 이김, 지어낸 구절·이번 서류는 버림."""

from __future__ import annotations

import pytest

from tashkeel_check.archive import CompanyArchive, InMemoryArchiveStore
from tashkeel_check.archive.store import text_sha256
from tashkeel_check.archive_apply import apply_archive
from tashkeel_check.config import Settings
from tashkeel_check.fake import FakeAgentModel, practice_responder
from tashkeel_check.results import ReviewResult
from tashkeel_check.runner import run_document
from tashkeel_check.text import segment_text, tokenize

from .conftest import fake_analyze, ids_of

LEASE = "عقد إيجار\nالوكيل: راشد مسلم الكعبي (Rashid Musallam Al Kaabi)\n"
OTHER = "خطاب\nالسيد راشد مسلم الكعبي\nRashed Muslim Al Kaabi\n"


@pytest.fixture
def archive():
    a = CompanyArchive(InMemoryArchiveStore())
    a.index_document("acme", "lease", "lease.txt", segment_text(LEASE))
    a.index_document("acme", "letter", "letter.txt", segment_text(OTHER))
    return a


def _hit(archive, doc):
    return next(p.hit_id for p in archive.find("acme", "راشد مسلم الكعبي", None, None) if p.document_id == doc)


def _result(mini_doc, claims) -> tuple[ReviewResult, list[int]]:
    """연습 모드로 돈 M2 결과에 대리인(s04) 보류 항목과 중재자 기록(claims)을 끼워 넣는다."""
    tokens = tokenize(mini_doc["segments"])
    agent = ids_of(tokens, "s04", ["راشد", "مسلم", "الكعبي"])
    base = run_document(
        mini_doc, "C1", FakeAgentModel(responder=practice_responder), Settings(), analyze_fn=fake_analyze
    )
    item = {
        "token_ids": agent,
        "type": "proper_noun",
        "candidates": [{"reading": None, "romanized": "Rashid", "source": "llm"}],
        "decision": "hold",
        "adopted": None,
        "reason": "r",
        "confidence": None,
        "evidence": None,
        "item_index": 0,
        "valid": True,
        "final_decision": "hold",
        "flags": [],
        "evidence_failure": None,
        "arabic": "راشد مسلم الكعبي",
        "segment_id": "s04",
    }
    dump = base.model_dump()
    dump["items"] = [item]
    dump["metrics"]["engine"] = {"archive": [{"token_ids": agent, "picks": p} for p in claims]}
    return ReviewResult.model_validate(dump), agent


def test_two_roles_agreeing_on_a_verified_passage_is_a_strong_suggestion(mini_doc, archive):
    hid = _hit(archive, "lease")
    res, agent = _result(
        mini_doc, [[{"spelling": "Rashid Musallam Al Kaabi", "hit_ids": [hid], "by": ["translator", "verifier"]}]]
    )
    (o,) = apply_archive(res, archive, "acme", "now", None, [])
    assert o.status == "archive_suggest" and o.agreement == "both" and o.token_ids == agent
    (s,) = o.suggestions
    assert s.document_id == "lease" and s.document_label == "lease.txt" and "Rashid Musallam Al Kaabi" in s.quote


def test_different_verified_spellings_are_a_conflict(mini_doc, archive):
    picks = [
        {"spelling": "Rashid Musallam Al Kaabi", "hit_ids": [_hit(archive, "lease")], "by": ["translator"]},
        {"spelling": "Rashed Muslim Al Kaabi", "hit_ids": [_hit(archive, "letter")], "by": ["verifier"]},
    ]
    res, _ = _result(mini_doc, [picks])
    (o,) = apply_archive(res, archive, "acme", "now", None, [])
    assert o.status == "archive_conflict" and {s.document_id for s in o.suggestions} == {"lease", "letter"}


@pytest.mark.parametrize(
    "spelling, hit, doc_id, sha_from",
    [
        ("Rashid Musallam Al Kaabi", "ffffffffff", "now", None),  # 지어낸 구절
        ("Rashid Musalam Al Kaabi", None, "now", None),  # 구절과 글자가 다름
        ("Rashid Musallam Al Kaabi", None, "lease", None),  # 이번 서류 자신
        ("Rashid Musallam Al Kaabi", None, "now", LEASE),  # 같은 파일을 다시 올림
    ],
)
def test_unverifiable_picks_are_dropped(mini_doc, archive, spelling, hit, doc_id, sha_from):
    hid = hit or _hit(archive, "lease")
    res, _ = _result(mini_doc, [[{"spelling": spelling, "hit_ids": [hid], "by": ["translator"]}]])
    sha = text_sha256(segment_text(sha_from)) if sha_from else None
    assert apply_archive(res, archive, "acme", doc_id, sha, []) == []


def test_dictionary_overlay_wins_and_other_customer_gets_nothing(mini_doc, archive):
    hid = _hit(archive, "lease")
    res, agent = _result(mini_doc, [[{"spelling": "Rashid Musallam Al Kaabi", "hit_ids": [hid], "by": ["translator"]}]])
    assert apply_archive(res, archive, "acme", "now", None, [{"token_ids": agent}]) == []
    assert apply_archive(res, archive, "other", "now", None, []) == []
    (o,) = apply_archive(res, archive, "acme", "now", None, [])
    assert o.agreement == "one"
