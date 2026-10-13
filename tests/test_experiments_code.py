"""실험 코드의 집계 로직만 확인한다. 실험 자체는 돌리지 않는다."""

import json

from tashkeel_check.experiments import exp001, exp002

from .conftest import fake_analyze


def test_exp001_unit_measure_and_summary(tmp_path):
    snap = {"rows": [
        {"ar": "سعيد مسلم المسلم", "en": "Saeed Musallam Al Muslim", "aliases": ["Said Muslim Al Muslim"]},
        {"ar": "حمد الكعبي", "en": "Hamad Al Kaabi", "aliases": []},
        {"ar": "راشد بن محمد آل مكتوم", "en": "Prince Rashid of Dubai", "aliases": []},
    ]}
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
            runs.append({"_doc_id": doc, "_repeat": rep, "n_silent": silent, "n_gold_without_evidence": 4,
                         "n_unsupported_adopt": 0, "n_hold": 4 - silent, "n_evidence_correct": 2,
                         "n_gold_with_evidence": 2, "n_unprocessed": 1, "valid_output": True,
                         "usage": {"input_tokens": 10, "output_tokens": 5}})
    s = exp002.aggregate({"C1": runs})["C1"]
    assert s["silent_rate"]["pooled"] == 0.5
    assert s["silent_rate"]["repeat_range"] == [0.25, 0.75]
    assert s["n_unprocessed"]["total"] == 4 and s["tokens_in"] == 40
