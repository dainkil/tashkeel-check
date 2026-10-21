from __future__ import annotations

import os

import pytest

from tashkeel_check.analyzer import AnalyzerUnavailable, camel_analyze
from tashkeel_check.config import Settings
from tashkeel_check.text import Segment, tokenize


def _camel_ok() -> bool:
    try:
        camel_analyze("كتب")
        return True
    except AnalyzerUnavailable:
        return False


CAMEL_OK = _camel_ok()
DB_URL = os.getenv("DATABASE_URL", "")


def _db_ok() -> bool:
    if not DB_URL:
        return False
    try:
        from tashkeel_check.web.db import Database

        return Database(DB_URL).ping()
    except Exception:
        return False


DB_OK = _db_ok()


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "camel" in item.keywords and not CAMEL_OK:
            item.add_marker(pytest.mark.skip(reason="camel-tools DB가 설치되지 않음"))
        if "live" in item.keywords and not os.getenv("OPENAI_API_KEY"):
            item.add_marker(pytest.mark.skip(reason="OPENAI_API_KEY 없음"))
        if "db" in item.keywords and not DB_OK:
            item.add_marker(pytest.mark.skip(reason="DATABASE_URL이 없거나 연결되지 않음"))


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    """저장소의 .env와 이미 읽힌 환경 변수를 떼어 낸다. 실제 키로 API를 부르지 않게 키는 빈 값으로 둔다."""
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.chdir(tmp_path)
    return tmp_path


# 분석기 대역: 테스트가 camel-tools 없이도 돌도록 정해 둔 분석 결과
FAKE_ANALYSES = {
    "مسلم": [
        {"diac": "مُسْلِمٌ", "lex": "مُسْلِم", "pos": "noun", "gloss": "Muslim"},
        {"diac": "مُسَلَّمٌ", "lex": "مُسَلَّم", "pos": "adj", "gloss": "delivered"},
    ],
    "حمد": [
        {"diac": "حَمَد", "lex": "حَمَد", "pos": "noun_prop", "gloss": "Hamad"},
        {"diac": "حَمْدٌ", "lex": "حَمْد", "pos": "noun", "gloss": "praise"},
    ],
    "وكالة": [
        {"diac": "وَكالَةٌ", "lex": "وَكالَة", "pos": "noun", "gloss": "agency"},
        {"diac": "وِكالَةٌ", "lex": "وِكالَة", "pos": "noun", "gloss": "power of attorney"},
    ],
    "المسلم": [],
    "الكعبي": [],
}


def fake_analyze(surface: str) -> list[dict]:
    if surface in FAKE_ANALYSES:
        return FAKE_ANALYSES[surface]
    return [{"diac": surface, "lex": surface, "pos": "noun", "gloss": "x"}]


def _ids(tokens, segment_id, words):
    seg = [t for t in tokens if t["segment_id"] == segment_id]
    return [next(t["id"] for t in seg if t["text"] == w) for w in words]


@pytest.fixture
def mini_doc() -> dict:
    """정답 라벨이 붙은 작은 문서. 위임인(s02, s05)은 s03에 영문 근거가 있고, 대리인(s04)은 근거가 없다."""
    segments = [
        Segment(segment_id="s01", text="وكالة خاصة"),
        Segment(segment_id="s02", text="حضر السيد سالم بن حمد المسلم، إماراتي الجنسية."),
        Segment(segment_id="s03", text="Principal: Salem bin Hamad Al Muslim"),
        Segment(segment_id="s04", text="وكّل السيد راشد مسلم الكعبي."),
        Segment(segment_id="s05", text="الموكل: سالم بن حمد المسلم"),
    ]
    tokens = tokenize(segments)
    ev = {"segment_id": "s03", "quote": "Salem bin Hamad Al Muslim"}

    def occ(oid, role, sid, words, english, variants, evidence):
        ids = _ids(tokens, sid, words)
        return {
            "occurrence_id": oid,
            "role": role,
            "segment_id": sid,
            "token_ids": ids,
            "tokens": [
                {"token_id": i, "arabic": w, "position": p, "english_variants": v, "english_used": e}
                for i, w, p, v, e in zip(ids, words, ["given", "middle", "family"], variants, english, strict=True)
            ],
            "evidence": evidence,
        }

    principal_vars = [["Salem", "Salim"], ["Hamad"], ["Al Muslim"]]
    gold = {
        "names": [
            occ(
                "n1", "principal", "s02", ["سالم", "حمد", "المسلم"], ["Salem", "Hamad", "Al Muslim"], principal_vars, ev
            ),
            occ(
                "n2",
                "agent",
                "s04",
                ["راشد", "مسلم", "الكعبي"],
                ["Rashid", "Musallam", "Al Kaabi"],
                [["Rashid", "Rashed"], ["Musallam", "Muslim"], ["Al Kaabi", "Al Ka'abi"]],
                None,
            ),
            occ(
                "n3", "principal", "s05", ["سالم", "حمد", "المسلم"], ["Salem", "Hamad", "Al Muslim"], principal_vars, ev
            ),
        ],
        "neutral_token_ids": [],
    }
    return {"doc_id": "mini", "synthetic": True, "segments": segments, "gold": gold}


@pytest.fixture
def mini_tokens(mini_doc):
    return tokenize(mini_doc["segments"])


def ids_of(tokens, segment_id, words):
    return _ids(tokens, segment_id, words)
