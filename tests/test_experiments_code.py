"""실험 코드의 집계 로직만 확인한다. 실험 자체는 돌리지 않는다."""

import json

from tashkeel_check.experiments import exp001, exp002

from .conftest import fake_analyze


def test_exp001_unit_measure_and_summary(tmp_path):
    snap = {
        "rows": [
            {"ar": "سعيد مسلم المسلم", "en": "Saeed Musallam Al Muslim", "aliases": ["Said Muslim Al Muslim"]},
            {"ar": "حمد الكعبي", "en": "Hamad Al Kaabi", "aliases": []},
            {"ar": "راشد بن محمد آل مكتوم", "en": "Prince Rashid of Dubai", "aliases": []},
        ]
    }
    path = tmp_path / "snap.json"
    path.write_text(json.dumps(snap, ensure_ascii=False))
    units, stats = exp001.collect_units(path)
    assert stats == {"persons_aligned": 2, "persons_unaligned": 1}
    by_key = {u["arabic"]: u for u in units}
    assert by_key["مسلم"]["english"] == ["Musallam", "Muslim"]
    rows = [exp001.unit_measure(u, fake_analyze) for u in units]
    r = {x["arabic"]: x for x in rows}
    assert r["مسلم"]["ambiguous"] and r["مسلم"]["covered_strict"]
    assert r["الكعبي"]["analysis_count"] == 0 and not r["الكعبي"]["covered_strict"]
    s = exp001.summarize_measures(rows)["all"]
    assert s["M1_zero_analysis_rate"] == round(2 / 5, 4)
    assert s["M6_ge2_variants_rate"] == round(2 / 5, 4)


def test_exp001_split_is_deterministic_and_disjoint():
    units = [{"key": str(i)} for i in range(20)]
    a, b = exp001.split_units(units, dev_size=5), exp001.split_units(units, dev_size=5)
    assert a == b and len(a["dev"]) == 5 and not ({u["key"] for u in a["dev"]} & {u["key"] for u in a["main"]})


def test_exp002_pools_counts_and_reports_repeat_range():
    runs = []
    for doc in ("d1", "d2"):
        for rep, silent in ((0, 1), (1, 3)):
            runs.append(
                {
                    "_doc_id": doc,
                    "_repeat": rep,
                    "n_silent": silent,
                    "n_gold_without_evidence": 4,
                    "n_unsupported_adopt": 0,
                    "n_hold": 4 - silent,
                    "n_evidence_correct": 2,
                    "n_gold_with_evidence": 2,
                    "n_unprocessed": 1,
                    "valid_output": True,
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                }
            )
    s = exp002.aggregate({"C1": runs})["C1"]
    assert s["silent_rate"]["pooled"] == 0.5
    assert s["silent_rate"]["repeat_range"] == [0.25, 0.75]
    assert s["n_unprocessed"]["total"] == 4 and s["tokens_in"] == 40


def test_exp002_reports_none_for_rates_a_condition_does_not_have():
    # C0에는 처분 형식이 없어 n_hold·n_evidence_correct가 없다. 0.0이 아니라 None이어야 한다
    runs = [
        {"_doc_id": d, "_repeat": 0, "n_silent": 1, "n_gold_without_evidence": 2, "n_gold_with_evidence": 3}
        for d in ("d1", "d2")
    ]
    s = exp002.aggregate({"C0": runs})["C0"]
    assert s["silent_rate"]["pooled"] == 0.5
    assert s["hold_rate"] == {"pooled": None, "repeat_range": None, "doc_bootstrap_95": None}
    assert s["evidence_pass_rate"]["pooled"] is None


def _runs(hidden: int, unsupported: int = 0, evidence_ok: int = 4, docs: int = 6) -> list[dict]:
    """문서마다 근거 없는 이름 10개, 근거 있는 이름 4개인 실행 기록(반복 2회, 모든 문서·회차가 같은 값)."""
    return [
        {
            "_doc_id": f"d{i}",
            "_repeat": rep,
            "n_gold_without_evidence": 10,
            "n_hidden_pick": hidden,
            "n_silent": hidden - unsupported,
            "n_unsupported_adopt": unsupported,
            "n_hold": 10 - hidden,
            "n_gold_with_evidence": 4,
            "n_evidence_correct": evidence_ok,
        }
        for i in range(docs)
        for rep in range(2)
    ]


def _judge(**runs_by_condition):
    return exp002.judge(exp002.aggregate(runs_by_condition), exp002.compare(runs_by_condition))


def test_exp002_stops_when_instructions_alone_pass_the_bar():
    v = _judge(C0=_runs(8), C1=_runs(1), C2=_runs(0), C3=_runs(0))
    assert v["decision"] == "stop"


def test_exp002_passes_when_a_tool_condition_fixes_what_c1_failed():
    v = _judge(C0=_runs(8), C1=_runs(5), C2=_runs(1), C3=_runs(3))
    assert v["decision"] == "pass" and v["passing"] == ["C2"]
    # C1이 근거 있는 이름을 보류만 하다가(통과율 0.5) 떨어지고, C3가 그것을 고친 경우
    v = _judge(C1=_runs(0, evidence_ok=2), C2=_runs(0, evidence_ok=2), C3=_runs(0))
    assert v["decision"] == "pass" and v["passing"] == ["C3"]


def test_exp002_fails_when_no_condition_passes_or_unsupported_adopts_are_too_many():
    assert _judge(C1=_runs(5), C2=_runs(4), C3=_runs(3))["decision"] == "fail"
    # 몰래 정함은 0.1 이하지만 그중 근거 없는 확정이 0.1이라 0.02를 넘는다
    assert _judge(C1=_runs(5), C2=_runs(1, unsupported=1), C3=_runs(5))["decision"] == "fail"


def test_exp002_paired_difference_uses_the_same_documents_for_both_conditions():
    d = exp002.compare({"C1": _runs(5), "C2": _runs(1)})["C1-C2"]["hidden_pick_rate"]
    assert d == {"diff": 0.4, "doc_bootstrap_95": [0.4, 0.4]}  # 문서마다 차이가 같으면 구간 폭이 0이다
