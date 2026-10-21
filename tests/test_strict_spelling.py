"""엄격 철자(romanize.strict_*)와 근거 검사 규칙 v2(ADR-017)."""

import pytest

from tashkeel_check.reconcile import verify_evidence
from tashkeel_check.romanize import (
    latin_words,
    parse_mrz,
    strict_equal,
    strict_in_text,
    strict_key,
    strict_words_in_quote,
)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("Al-Hashimi", "AL HASHIMI"),
        ("Al Hashimi", "Alhashimi"),
        ("Saleh bin Ahmed", "SALEH AHMED"),
        ("Sa'd", "Sa’d"),
        ("Abd Allah", "ABD<ALLAH"),
    ],
)
def test_strict_ignores_case_spaces_hyphens_apostrophes_mrz_and_connectors(a, b):
    assert strict_equal(a, b)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("Hamad", "Hamed"),
        ("Hamad", "Hammad"),
        ("El Hashimi", "Al Hashimi"),
        ("Al Hashimi", "Hashimi"),
        ("Saad", "Sa'd"),
    ],
)
def test_strict_keeps_vowels_doubled_letters_and_articles(a, b):
    assert not strict_equal(a, b)


def test_mrz_name_line():
    assert parse_mrz("P<AREAL<HASHIMI<<AHMED<SALEH<<<<<<") == ["AL", "HASHIMI", "AHMED", "SALEH"]
    assert parse_mrz("Principal: Ahmed") is None
    assert latin_words("Email: s.alfawzan@example.com") == ["Email", "s", "alfawzan", "example", "com"]
    assert strict_key("P<SAUAL<AJMI<<KHALED<SALMAN<<<") == "alajmikhaledsalman"


def test_words_in_quote_ignores_order_but_not_letters():
    assert strict_words_in_quote("Salem Al Muslim", "AL MUSLIM, Salem")
    assert strict_words_in_quote("Al Hashimi", "P<AREALHASHIMI<<AHMED<<<<")
    assert strict_words_in_quote("Al Fawzan", "Surname: AL FAWZAN / Given names: SALEH")
    assert not strict_words_in_quote("Salim", "Salem Al Muslim")
    assert not strict_words_in_quote("Salem Salem", "Salem Al Muslim")  # 인용의 한 단어를 두 번 쓰지 않는다
    assert strict_in_text("Al Fawzan", "Mr. Saleh Al-Fawzan of Dubai")


def test_evidence_rule_v2_accepts_passport_forms_and_rejects_vowel_changes():
    seg = {"s03": "Surname: AL MUSLIM / Given names: SALEM HAMAD"}
    item = {"evidence": {"segment_id": "s03", "quote": "AL MUSLIM / Given names: SALEM"}, "adopted": "Salem Al Muslim"}
    assert verify_evidence(item, seg, "v2") == (True, "")
    assert verify_evidence(item, seg, "v1") == (False, "adopted_not_in_quote")  # v1은 연속 단어열만 본다
    assert verify_evidence({**item, "adopted": "Salim"}, seg, "v2") == (False, "adopted_not_in_quote")
    assert verify_evidence({**item, "adopted": "Salim"}, seg, "v1") == (True, "")  # v1은 Salem≈Salim
