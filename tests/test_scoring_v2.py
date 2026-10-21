"""채점 v2(scoring_v2): gold 형식 2의 이름 부분마다 안전·엄격 판정. 오류 종류마다 하나씩 만든다."""

import glob
import json
from pathlib import Path

import pytest

from tashkeel_check.analyzer import analyze_tokens
from tashkeel_check.config import Settings
from tashkeel_check.fake import FakeAgentModel
from tashkeel_check.reconcile import reconcile
from tashkeel_check.runner import run_document
from tashkeel_check.scoring_v2 import marked_t1
from tashkeel_check.text import Segment, tokenize

from . import hard_responders as H
from .conftest import fake_analyze, ids_of

SEGMENTS = [
    Segment(segment_id="s01", text="حضر السيد سالم بن حمد المسلم."),
    Segment(segment_id="s02", text="Principal: Salem bin Hamad Al Muslim"),
    Segment(segment_id="s03", text="وكّل السيد سليم المسلم."),
    Segment(segment_id="s04", text="Email: info@almuslim.example.com"),
]
TOKENS = tokenize(SEGMENTS)
QUOTE = {"segment_id": "s02", "quote": "Salem bin Hamad Al Muslim"}


def _unit(sid, word, slot, expected, spelling, variants, case_types=(), arguable=False):
    tids = ids_of(TOKENS, sid, [word])
    return {
        "token_id": tids[-1],
        "token_ids": tids,
        "unit_id": f"{sid}.{slot}",
        "slot": slot,
        "arabic": word,
        "position": "family" if slot == "family" else "given",
        "english_variants": variants,
        "raw_variants": variants,
        "english_used": variants[0],
        "expected": expected,
        "expected_spelling": spelling,
        "evidence": [QUOTE] if expected == "adopt" else [],
        "must_include": [],
        "case_types": list(case_types),
        "arguable": arguable,
    }


GOLD = {
    "format_version": 2,
    "names": [
        {
            "occurrence_id": "n1",
            "role": "principal",
            "person_id": "p1",
            "mention": "full",
            "segment_id": "s01",
            "evidence": QUOTE,
            "tokens": [
                _unit("s01", "سالم", "given", "adopt", "Salem", ["Salem", "Salim"]),
                _unit("s01", "حمد", "father", "adopt", "Hamad", ["Hamad", "Hamed"]),
                _unit("s01", "المسلم", "family", "adopt", "Al Muslim", ["Al Muslim", "Al Musallam"]),
            ],
        },
        {
            "occurrence_id": "n2",
            "role": "agent",
            "person_id": "p2",
            "mention": "full",
            "segment_id": "s03",
            "evidence": None,
            "tokens": [
                _unit("s03", "سليم", "given", "hold", None, ["Saleem", "Sulayem"], ["C1"]),
                _unit("s03", "المسلم", "family", "hold", None, ["Al Muslim", "Al Musallam"], ["A1", "C2"], True),
            ],
        },
    ],
    "persons": [
        {"person_id": "p1", "kind": "person", "renderings": [{"segment_id": "s02", "quote": QUOTE["quote"]}]},
        {"person_id": "p2", "kind": "person", "renderings": []},
    ],
    "decoys": [
        {"segment_id": "s04", "quote": "info@almuslim.example.com", "kind": "email", "resembles": ["p2.family"]}
    ],
    "neutral_token_ids": [],
    "lookalike_token_ids": [],
}


def _item(word_sid, words, decision="hold", adopted=None, evidence=None, cands=("A", "B"), typ="proper_noun"):
    return {
        "token_ids": ids_of(TOKENS, word_sid, words),
        "type": typ,
        "candidates": [{"reading": None, "romanized": c, "source": "llm"} for c in cands],
        "decision": decision,
        "adopted": adopted,
        "reason": "test",
        "confidence": 0.9 if adopted else None,
        "evidence": evidence,
    }


def _good(**overrides):
    """정답 출력. overrides로 항목·번역문을 바꾼다."""
    items = {
        "p1.given": _item("s01", ["سالم"], "evidence_adopt", "Salem", QUOTE),
        "p1.father": _item("s01", ["حمد"], "evidence_adopt", "Hamad", QUOTE),
        "p1.family": _item("s01", ["المسلم"], "evidence_adopt", "Al Muslim", QUOTE),
        "p2.given": _item("s03", ["سليم"], cands=("Saleem", "Sulayem")),
        "p2.family": _item("s03", ["المسلم"], cands=("Al Muslim", "Al Musallam")),
    }
    english = {
        "s01": "Mr. Salem bin Hamad Al Muslim appeared.",
        "s02": "Principal: Salem bin Hamad Al Muslim",
        "s03": "He appointed Mr. [Saleem/Sulayem] [Al Muslim/Al Musallam].",
        "s04": "Email: info@almuslim.example.com",
    }
    for key, value in overrides.items():
        if key in english:
            english[key] = value
        elif value is None:
            items.pop(key)
        else:
            items[key] = value
    return {"translation": [{"segment_id": s, "english": e} for s, e in english.items()], "items": list(items.values())}


def _score(output, condition="C1"):
    analyses = analyze_tokens(TOKENS, fake_analyze)
    return reconcile(condition, SEGMENTS, TOKENS, analyses, output, gold=GOLD, evidence_rule="v2")["metrics"]


def _errors(m):
    return {u["unit_id"]: u["error"] for u in m["units"] if u["error"]}


def test_correct_output_is_fully_correct():
    m = _score(_good())
    assert (m["n_scored_units"], m["n_strict_correct"], m["n_safety_ok"]) == (5, 5, 5)
    assert m["doc_strict_all_correct"] == m["doc_safety_all_ok"] == 1
    assert m["by_case_type"]["A1"] == {"n": 1, "strict": 1, "safety_ok": 1}
    assert (m["n_scored_units_nonarguable"], m["n_safety_ok_nonarguable"]) == (4, 4)
    assert "units" in m and m["scoring"]["scoring"] == "v2"


@pytest.mark.parametrize(
    ("override", "unit", "kind"),
    [
        # 다른 사람(p1)의 표기로 p2의 가문명을 확정
        (
            {"p2.family": _item("s03", ["المسلم"], "evidence_adopt", "Al Muslim", QUOTE)},
            "s03.family",
            "unsupported_other_person",
        ),
        # 이메일 주소를 근거로 확정
        (
            {
                "p2.family": _item(
                    "s03",
                    ["المسلم"],
                    "evidence_adopt",
                    "Almuslim",
                    {"segment_id": "s04", "quote": "info@almuslim.example.com"},
                )
            },
            "s03.family",
            "unsupported_decoy",
        ),
        ({"p2.given": _item("s03", ["سليم"], "adopt", "Saleem")}, "s03.given", "unsupported_adopt"),
        ({"p2.given": _item("s03", ["سليم"], "adopt", "Saleem", typ="word")}, "s03.given", "unsupported_word_adopt"),
        # 철자는 맞지만 근거로 든 것이 그 사람의 표기가 아니다
        (
            {
                "p1.family": _item(
                    "s01",
                    ["المسلم"],
                    "evidence_adopt",
                    "Almuslim",
                    {"segment_id": "s04", "quote": "info@almuslim.example.com"},
                )
            },
            "s01.family",
            "decoy_evidence_correct_spelling",
        ),
        # Salim은 근거 검사 v2에서 강등되어 보류가 되고, 번역문에 표시 없이 쓴 한 표기가 안전 오류다
        (
            {
                "p1.given": _item("s01", ["سالم"], "evidence_adopt", "Salim", QUOTE),
                "s01": "Mr. Salim bin Hamad Al Muslim",
            },
            "s01.given",
            "translation_unmarked",
        ),
        ({"s01": "Mr. Salem bin Hamed Al Muslim appeared."}, "s01.father", "translation_wrong_spelling"),
        ({"s03": "He appointed Mr. Saleem [Al Muslim/Al Musallam]."}, "s03.given", "translation_unmarked"),
        ({"p2.given": None}, "s03.given", "unprocessed"),
    ],
)
def test_each_safety_error_kind(override, unit, kind):
    m = _score(_good(**override))
    assert _errors(m) == {unit: kind}
    assert m[f"n_err_{kind}"] == 1 and m["n_safety_ok"] == 4 and m["n_strict_correct"] == 4


@pytest.mark.parametrize(
    ("override", "unit", "kind"),
    [
        (
            {
                "p1.given": _item("s01", ["سالم"], cands=("Salem", "Salim")),
                "s01": "Mr. [Salem/Salim] bin Hamad Al Muslim",
            },
            "s01.given",
            "hold_instead_of_adopt",
        ),
        ({"s01": "Mr. Salem Al Muslim appeared."}, "s01.father", "translation_missing"),
    ],
)
def test_strict_only_errors_keep_safety(override, unit, kind):
    m = _score(_good(**override))
    assert _errors(m) == {unit: kind}
    assert m["n_safety_ok"] == 5 and m["n_strict_correct"] == 4 and m[f"n_strict_only_{kind}"] == 1


def test_c0_rule_v1():
    text = (
        "[s01] Mr. Salem bin Hamad Al Muslim appeared.\n[s02] Principal\n"
        "[s03] He appointed Mr. Saleem Al Muslim.\n[s04] x"
    )
    m = _score(text, "C0")
    assert _errors(m) == {"s03.given": "silent_pick", "s03.family": "silent_pick"}
    m = _score(text.replace("Saleem Al Muslim", "[Saleem/Sulayem] [Al Muslim/Al Musallam]"), "C0")
    assert not _errors(m) and m["n_strict_correct"] == 5
    m = _score(text.replace("Salem bin Hamad", "Salim bin Hamad"), "C0")
    assert _errors(m) == {"s01.given": "wrong_spelling", "s03.given": "silent_pick", "s03.family": "silent_pick"}


def test_marked_t1_ignores_a_neighbours_marker():
    text = "Mr. [Sultan/?] Al Kuwaiti and Saleh (?) and [Ali/Aly]"
    for word, marked in [("Al Kuwaiti", False), ("Saleh", True), ("Ali", True), ("Sultan", True)]:
        i = text.index(word)
        assert marked_t1(text, i, i + len(word)) is marked, word


def test_old_gold_format_is_scored_as_before(mini_doc, mini_tokens):
    """gold 형식 1(synthetic-v2)에는 채점 v2 지표가 붙지 않는다."""
    analyses = analyze_tokens(mini_tokens, fake_analyze)
    m = reconcile("C1", mini_doc["segments"], mini_tokens, analyses, {"translation": [], "items": []}, mini_doc["gold"])
    assert "n_scored_units" not in m["metrics"] and "hidden_pick_rate" in m["metrics"]


HARD_DEV = sorted(glob.glob("data/synthetic-hard/dev/*.json"))[:6]
HARD_SETTINGS = Settings(prompt_version="p1", evidence_rule="v2")


def _run_hard(mutate=None, conditions=("C0", "C1", "C3")):
    totals = {}
    for path in HARD_DEV:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        for cond in conditions:
            model = FakeAgentModel(responder=H.make_responder(doc, mutate))
            m = run_document(doc, cond, model, HARD_SETTINGS, analyze_fn=fake_analyze).metrics
            t = totals.setdefault(cond, {"n": 0, "strict": 0, "safety": 0, "hold": 0, "errors": {}})
            t["n"] += m["n_scored_units"]
            t["strict"] += m["n_strict_correct"]
            t["safety"] += m["n_safety_ok"]
            t["hold"] += m["n_expected_hold"]
            for u in m["units"]:
                if u["error"]:
                    t["errors"][u["error"]] = t["errors"].get(u["error"], 0) + 1
    return totals


def test_oracle_scores_perfectly_on_hard_dev():
    """정답대로 답하면 정답 규칙·근거 검사 v2·채점 v2가 서로 맞아 1.0이어야 한다."""
    for cond, t in _run_hard().items():
        assert t["strict"] == t["safety"] == t["n"] > 0, (cond, t["errors"])


@pytest.mark.parametrize(
    ("mutate", "kind"),
    [
        (H.adopt_held_with_first_variant, "unsupported_adopt"),
        (H.unmarked_translation, "translation_unmarked"),
        (H.drop_names, "unprocessed"),
    ],
)
def test_adversarial_responders_produce_exactly_their_error(mutate, kind):
    t = _run_hard(mutate, ("C1",))["C1"]
    expected = t["n"] if kind == "unprocessed" else t["hold"]
    assert t["errors"] == {kind: expected}


def test_holding_everything_is_safe_but_not_strict():
    t = _run_hard(H.hold_everything, ("C1",))["C1"]
    assert t["safety"] == t["n"] and t["strict"] == t["hold"] < t["n"]
