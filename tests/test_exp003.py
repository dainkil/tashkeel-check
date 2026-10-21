"""EXP-003 판정(99% 두 기준, 서비스 기준 문구)과 실행 장치 공유. 가짜 모델로만 돌린다."""

import csv
import json
from pathlib import Path

from tashkeel_check.config import Settings
from tashkeel_check.experiments import exp002, exp003
from tashkeel_check.experiments.harness import clopper_pearson_lower
from tashkeel_check.fake import FakeAgentModel

from . import hard_responders as H
from .conftest import fake_analyze

HARD_DEV = Path("data/synthetic-hard/dev")


def test_clopper_pearson_matches_the_99_percent_sample_sizes():
    assert clopper_pearson_lower(1000, 1000) > 0.99
    assert clopper_pearson_lower(996, 1000) >= 0.99 > clopper_pearson_lower(995, 1000)
    assert clopper_pearson_lower(499, 500) >= 0.99 > clopper_pearson_lower(498, 500)
    assert clopper_pearson_lower(300, 300) >= 0.99 > clopper_pearson_lower(299, 300)
    assert clopper_pearson_lower(0, 10) == 0.0 and clopper_pearson_lower(0, 0) is None


def _runs(n_docs, units, errors_by_repeat, repeats=3):
    """문서 n_docs개 × 반복. 반복마다 정해진 수의 오류를 앞 문서부터 하나씩 나눠 준다."""
    runs = []
    for rep in range(repeats):
        left = errors_by_repeat[rep]
        for d in range(n_docs):
            err = 1 if left > 0 else 0
            left -= err
            ok = units - err
            runs.append(
                {
                    "_doc_id": f"d{d:02d}",
                    "_repeat": rep,
                    "n_scored_units": units,
                    "n_strict_correct": ok,
                    "n_safety_ok": ok,
                    "n_docs": 1,
                    "doc_strict_all_correct": int(ok == units),
                    "doc_safety_all_ok": int(ok == units),
                    "valid_output": True,
                    "by_case_type": {"A1": {"n": 2, "strict": 2, "safety_ok": 2}},
                }
            )
    return runs


def test_judge_and_service_claim():
    perfect = _runs(70, 20, [0, 0, 0])  # 1,400개 × 3회 오류 0
    near = _runs(70, 20, [10, 12, 9])  # 99.2~99.4%: 점추정은 넘지만 하한은 못 넘는다
    low = _runs(70, 20, [60, 70, 65])  # 약 95%
    summary = exp003.aggregate({"C1": low, "C2": perfect, "C3": near})
    assert summary["C2"]["service_claim"]["claim"] is True
    assert summary["C3"]["strict_accuracy"]["pooled"] >= 0.99 and summary["C3"]["service_claim"]["claim"] is False
    assert summary["C2"]["by_case_type"]["A1"]["n"] == 2 * 70 * 3
    verdict = exp003.judge(summary, exp003.compare({"C1": low, "C2": perfect, "C3": near}))
    assert verdict["decision"] == "pass" and "C2" in verdict["passing"]
    stop = exp003.aggregate({"C1": perfect, "C2": low})
    assert exp003.judge(stop, exp003.compare({"C1": perfect, "C2": low}))["decision"] == "stop"
    fail = exp003.aggregate({"C1": low, "C2": low, "C3": low})
    assert exp003.judge(fail, exp003.compare({"C1": low, "C2": low, "C3": low}))["decision"] == "fail"


def _oracle_factory(paths):
    """사용자 메시지의 구간 원문으로 문서를 찾아 그 문서의 정답대로 답하는 가짜 모델."""
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in paths]

    def respond(messages, bound):
        text = str(next(m.content for m in messages if m.type == "human"))
        doc = next(d for d in docs if all(seg["text"] in text for seg in d["segments"][:3]))
        return H.make_responder(doc)(messages, bound)

    return lambda: FakeAgentModel(responder=respond)


def test_fake_oracle_run_resumes_and_reports(tmp_path):
    paths = sorted(HARD_DEV.glob("*.json"))[:2]
    first = exp003.run(
        HARD_DEV, tmp_path, _oracle_factory(paths), Settings(), limit=2, repeats=1, max_runs=3, analyze_fn=fake_analyze
    )
    assert first.paused_reason == "max_runs"
    plan = exp003.load_plan(first.run_dir)
    assert (plan["experiment"], plan["prompt_version"], plan["evidence_rule"]) == ("EXP-003", "p1", "v2")
    assert plan["pass_bar"] == {"strict_accuracy": 0.99, "safety_accuracy": 0.99}
    done = exp003.run(
        HARD_DEV,
        tmp_path,
        _oracle_factory(paths),
        Settings(),
        limit=2,
        repeats=1,
        run_dir=first.run_dir,
        analyze_fn=fake_analyze,
    )
    report = json.loads(done.summary_path.read_text(encoding="utf-8"))
    for cond in ("C0", "C1", "C2", "C3"):
        assert report["summary"][cond]["strict_accuracy"]["pooled"] == 1.0, cond
    assert report["verdict"]["decision"] == "stop"
    assert report["verdict"]["service_claim"]["C1"] is False  # 문서 2개로는 하한이 0.99에 못 미친다
    rows = [r for r in exp003.read_ledger(first.run_dir) if r["type"] == "run"]
    assert all("units" not in r["metrics"] for r in rows)
    metrics = json.loads((first.run_dir / "C1" / paths[0].stem / "r0" / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["units"] and metrics["n_scored_units"] == len(metrics["units"])
    rescored = json.loads(exp003.rescore(first.run_dir, analyze_fn=fake_analyze).read_text(encoding="utf-8"))
    for cond in ("C0", "C1", "C2", "C3"):
        assert rescored["summary"][cond]["strict_accuracy"] == report["summary"][cond]["strict_accuracy"], cond
    out = exp003.export_errors(first.run_dir, n_correct_sample=5)
    with out.open(encoding="utf-8-sig") as f:
        table = list(csv.DictReader(f))
    assert len(table) == 5 and {r["auto_judged"] for r in table} == {"correct"}


def test_exp002_plan_keys_are_unchanged_by_the_shared_harness():
    plan = exp002.make_plan(
        "data/synthetic/dev",
        sorted(Path("data/synthetic/dev").glob("*.json"))[:2],
        ("C0", "C1"),
        1,
        Settings(),
        "fake-agent",
    )
    assert list(plan) == [
        "experiment",
        "docs_dir",
        "docs",
        "conditions",
        "repeats",
        "order",
        "model",
        "model_label",
        "settings",
        "prompt_version",
        "prompt_hash",
        "matcher_version",
        "analyzer",
        "package_version",
    ]
    assert plan["prompt_version"] == "p0"
    hard = Settings(prompt_version="p1", evidence_rule="v2")
    assert exp002.SPEC.configure(hard).prompt_version == "p0" and exp002.SPEC.configure(hard).evidence_rule == "v1"
