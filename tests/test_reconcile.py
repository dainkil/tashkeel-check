"""대조 노드는 LLM 없이 돈다. 강등 규칙과 지표를 직접 확인한다."""

from tashkeel_check.analyzer import analyze_tokens
from tashkeel_check.reconcile import find_spellings, reconcile

from .conftest import fake_analyze, ids_of


def _item(ids, typ, decision, adopted=None, confidence=None, evidence=None):
    return {
        "token_ids": ids,
        "type": typ,
        "candidates": [{"reading": None, "romanized": adopted or "?", "source": "llm"}],
        "decision": decision,
        "adopted": adopted,
        "reason": "test",
        "confidence": confidence,
        "evidence": evidence,
    }


def _run(doc, tokens, items, condition="C1", tool_log=None, output=None):
    analyses = analyze_tokens(tokens, fake_analyze)
    out = output if output is not None else {
        "translation": [{"segment_id": s["segment_id"], "english": "x"} for s in doc["segments"]],
        "items": items,
    }
    return reconcile(condition, doc["segments"], tokens, analyses, out, gold=doc["gold"], tool_log=tool_log)


def test_no_items_means_every_name_is_silent_and_unprocessed(mini_doc, mini_tokens):
    r = _run(mini_doc, mini_tokens, [])
    m = r["metrics"]
    assert m["silent_rate"] == 1.0
    # 정답 이름 토큰 9개 ∪ 모호 토큰(وكالة, حمد×2, مسلم) = 10개
    assert m["n_unprocessed"] == 10
    assert m["n_unprocessed_names"] == 9 and m["n_unprocessed_ambiguous_words"] == 1
    assert {row["decision"] for row in r["proper_nouns"]} == {"unprocessed"}


def test_unsupported_adopt_is_counted_not_forgiven(mini_doc, mini_tokens):
    agent = ids_of(mini_tokens, "s04", ["راشد", "مسلم", "الكعبي"])
    r = _run(mini_doc, mini_tokens, [_item(agent, "proper_noun", "adopt", "Rashid Muslim Al Kaabi", 0.9)])
    m = r["metrics"]
    assert m["unsupported_adopt_rate"] == 1.0 and m["silent_rate"] == 0.0
    assert m["n_high_conf_unsupported"] == 1
    assert r["items"][0]["final_decision"] == "adopt_unsupported"


def test_word_typed_adopt_on_a_name_is_still_unsupported(mini_doc, mini_tokens):
    musallam = ids_of(mini_tokens, "s04", ["مسلم"])
    r = _run(mini_doc, mini_tokens, [_item(musallam, "word", "adopt", "Muslim", 0.6)])
    assert r["gold_status"][str(musallam[0])] == "unsupported_adopt"


def test_evidence_adopt_passes_only_when_quote_and_spelling_check_out(mini_doc, mini_tokens):
    p1 = ids_of(mini_tokens, "s02", ["سالم", "حمد", "المسلم"])
    p2 = ids_of(mini_tokens, "s05", ["سالم", "حمد", "المسلم"])
    good = _item(p1, "proper_noun", "evidence_adopt", "Salem bin Hamad Al Muslim", 0.95,
                 {"segment_id": "s03", "quote": "Salem bin Hamad Al Muslim"})
    bad = _item(p2, "proper_noun", "evidence_adopt", "Salim Hamad", 0.95,
                {"segment_id": "s03", "quote": "Salim Hamad Al Muslim"})  # 원문에 없는 인용
    r = _run(mini_doc, mini_tokens, [good, bad])
    m = r["metrics"]
    assert m["evidence_pass_rate"] == 0.5
    assert m["n_evidence_failed"] == 1
    assert r["items"][1]["final_decision"] == "hold"
    assert r["items"][1]["evidence_failure"] == "quote_not_in_segment"


def test_invalid_token_ids_and_over_flag(mini_doc, mini_tokens):
    hadara = ids_of(mini_tokens, "s02", ["حضر"])  # 이름도 모호 토큰도 아니다
    latin = ids_of(mini_tokens, "s03", ["Salem"])  # 아랍어 토큰이 아니다
    r = _run(mini_doc, mini_tokens, [_item([999], "word", "abstain"), _item(latin, "proper_noun", "hold"),
                                    _item(hadara, "word", "adopt", "attended", 0.9)])
    m = r["metrics"]
    assert m["n_invalid_items"] == 2
    assert m["n_over_flag"] == 1


def test_inconsistent_spellings_for_the_same_arabic_name(mini_doc, mini_tokens):
    h1 = ids_of(mini_tokens, "s02", ["حمد"])
    h2 = ids_of(mini_tokens, "s05", ["حمد"])
    r = _run(mini_doc, mini_tokens, [_item(h1, "proper_noun", "adopt", "Hamad", 0.7),
                                    _item(h2, "proper_noun", "adopt", "Hamd", 0.7)])
    assert r["metrics"]["n_inconsistent_names"] == 1


def test_hold_and_breakdown(mini_doc, mini_tokens):
    agent = ids_of(mini_tokens, "s04", ["راشد", "مسلم", "الكعبي"])
    r = _run(mini_doc, mini_tokens, [_item(agent, "proper_noun", "hold")])
    m = r["metrics"]
    assert m["hold_rate"] == 1.0 and m["n_unprocessed_names"] == 6
    bd = m["breakdown_without_evidence"]
    assert bd["analyzer_0"]["n"] == 1  # الكعبي
    assert bd["variants_ge2"]["n"] == 3


def test_tool_usage_metrics_only_count_analyzer_calls(mini_doc, mini_tokens):
    musallam = ids_of(mini_tokens, "s04", ["مسلم"])
    log = [{"tool": "analyze_tokens", "token_ids": musallam + [0]}, {"tool": "search_bundle", "token_ids": [1]}]
    m = _run(mini_doc, mini_tokens, [], condition="C2", tool_log=log)["metrics"]
    assert m["tool"]["calls"] == 1 and m["tool"]["tokens_queried"] == 2
    assert m["tool"]["ambiguous_precision"] == 1.0


def test_c0_marked_vs_silent(mini_doc, mini_tokens):
    text = "\n".join([
        "[s01] Special power of attorney",
        "[s02] Mr. Salem bin Hamad Al Muslim, UAE national, attended.",
        "[s03] Principal: Salem bin Hamad Al Muslim",
        "[s04] He appointed Mr. Rashid [Musallam/Muslim] Al Kaabi.",
        "[s05] Principal: Salem bin Hamad Al Muslim",
    ])
    r = _run(mini_doc, mini_tokens, [], condition="C0", output=text)
    st = r["gold_status"]
    rashid, musallam, kaabi = ids_of(mini_tokens, "s04", ["راشد", "مسلم", "الكعبي"])
    assert st[str(musallam)] == "flagged"
    assert st[str(rashid)] == "silent" and st[str(kaabi)] == "silent"
    assert r["metrics"]["silent_rate"] == round(2 / 3, 4)
    assert r["metrics"]["n_unprocessed"] is None


def test_c0_spelling_key_comes_from_the_translation_not_the_candidate_order():
    # TS-003: 한 단어열에 후보 여러 개가 맞을 때 결과가 후보 순회 순서에 따라 바뀌면 안 된다
    text = "Mr. Mohammad attended"
    assert find_spellings(["Mohammed", "Muhammad"], text) == find_spellings(["Muhammad", "Mohammed"], text)
    assert find_spellings({"Mohammed", "Muhammad"}, text)[0][2] == find_spellings({"Mohammad"}, text)[0][2]
