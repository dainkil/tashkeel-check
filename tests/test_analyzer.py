import pytest

from tashkeel_check.analyzer import analyze_tokens, strip_case_ending, summarize, view_for_llm
from tashkeel_check.text import segment_text, tokenize

from .conftest import fake_analyze


def test_strip_case_ending_removes_case_marks_but_keeps_shadda():
    assert strip_case_ending("وَكالَةٌ") == "وَكالَة"
    assert strip_case_ending("مُسَلَّمُ") == "مُسَلَّم"
    assert strip_case_ending("كِتاباً") == "كِتاب"
    assert strip_case_ending("كِتابًا") == "كِتاب"
    assert strip_case_ending("رَبٌّ") == "رَبّ"


def test_summarize_groups_case_variants_and_flags_ambiguity():
    analyses = [
        {"diac": "مُسْلِمٌ", "lex": "مُسْلِم", "pos": "noun", "gloss": "Muslim"},
        {"diac": "مُسْلِمَ", "lex": "مُسْلِم", "pos": "noun", "gloss": "Muslim"},
        {"diac": "مُسَلَّمٌ", "lex": "مُسَلَّم", "pos": "adj", "gloss": "delivered"},
    ]
    s = summarize(0, "مسلم", analyses)
    assert s["analysis_count"] == 3 and s["raw_distinct_diac"] == 3
    assert {c["romanized"] for c in s["candidates"]} == {"muslim", "musallam"}
    assert s["ambiguous"] is True and s["has_noun_prop"] is False


def test_case_endings_alone_are_not_ambiguity():
    s = summarize(0, "رشيد", [{"diac": "رَشِيدٌ", "pos": "noun_prop"}, {"diac": "رَشِيدَ", "pos": "noun_prop"}])
    assert s["ambiguous"] is False and s["has_noun_prop"] is True


def test_analyze_tokens_skips_latin_and_records_zero_analyses():
    toks = tokenize(segment_text("حضر المسلم\nSalem"))
    res = analyze_tokens(toks, fake_analyze)
    assert set(res) == {0, 1}
    assert res[1]["analysis_count"] == 0 and res[1]["candidates"] == []


def test_view_for_llm_reports_truncation():
    s = summarize(0, "x", [{"diac": f"x{i}"} for i in range(5)])
    v = view_for_llm(s, max_candidates=2)
    assert len(v["candidates"]) == 2 and v["candidates_truncated"] == 3


@pytest.mark.camel
def test_camel_analyzer_on_known_words():
    toks = tokenize(segment_text("مسلم رشيد القبيسي"))
    res = analyze_tokens(toks)
    assert res[0]["ambiguous"] is True  # مُسْلِم / مُسَلَّم
    assert {c["romanized"] for c in res[0]["candidates"]} >= {"muslim", "musallam"}
    assert res[2]["analysis_count"] == 0  # 가문명은 사전에 없을 수 있다
