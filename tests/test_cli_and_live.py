import json

import pytest

from tashkeel_check.cli import main
from tashkeel_check.config import load_settings
from tashkeel_check.runner import make_model, run_document


@pytest.mark.camel
def test_cli_run_all_conditions_in_practice_mode(mini_doc, tmp_path, capsys):
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(mini_doc, ensure_ascii=False))
    assert main(["run", "--doc", str(doc_path), "--condition", "all", "--fake", "--out", str(tmp_path / "out")]) == 0
    lines = [json.loads(x) for x in capsys.readouterr().out.strip().splitlines()]
    assert [x["condition"] for x in lines] == ["C0", "C1", "C2", "C3"]
    for cond in ("C0", "C1", "C2", "C3"):
        assert (tmp_path / "out" / cond / "proper_nouns.csv").exists()


def test_cli_bundle_requires_explicit_enable(mini_doc, tmp_path, monkeypatch):
    monkeypatch.setenv("ENABLE_BUNDLE_SEARCH", "false")
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(mini_doc, ensure_ascii=False))
    assert main(["run", "--doc", str(doc_path), "--fake", "--bundle", str(tmp_path)]) == 2


def test_exp002_refuses_real_run_without_consent(capsys):
    assert main(["exp002", "--split", "eval", "--limit", "1"]) == 1
    assert "--yes" in capsys.readouterr().out


@pytest.mark.live
@pytest.mark.camel
def test_live_c1_returns_structured_dispositions(mini_doc):
    """실제 OpenAI 호출. 번역 문장이 아니라 구조만 본다."""
    settings = load_settings()
    result = run_document(mini_doc, "C1", make_model(settings), settings)
    m = result["metrics"]
    assert m["valid_output"]
    assert m["n_segments_translated"] == m["n_segments"]
    for it in result["items"]:
        assert it["final_decision"] in {"adopt", "abstain", "evidence_adopt", "hold", "adopt_unsupported"}
        if it["final_decision"] == "evidence_adopt":
            assert it["evidence"] and it["evidence_failure"] is None
    assert m["n_unprocessed"] is not None
