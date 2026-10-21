"""가이드 6단계: 판정 규칙 여섯 가지와 사전 규칙. 사람·회사 항목은 같은 함수를 탄다."""

import pytest

from tashkeel_check.bundle.dictionary import DictionaryEntry
from tashkeel_check.bundle.rules import decide_status, near_match, strict_equal
from tashkeel_check.bundle.schemas import BundleEvidence, NameMention


def _m(translated="Musallam", entity_id="e1", etype="person", error=None):
    return NameMention(
        mention_id="m1",
        document_id="contract",
        segment_id="s01",
        entity_id=entity_id,
        entity_type=etype,
        arabic_name="مسلم",
        arabic_key="مسلم",
        translated_name=translated,
        extraction_error=error,
    )


def _ev(name, doc="id1", valid=True, failure=None):
    return BundleEvidence(
        document_id=doc, segment_id="s01", quote=f"Name: {name}", english_name=name, valid=valid, failure=failure
    )


def _entry(name="Musallam"):
    return DictionaryEntry(customer_id="c", entity_id="e1", arabic_key="مسلم", arabic_name="مسلم", english_name=name)


def test_no_evidence_is_pending():
    it = decide_status(_m(), [])
    assert (it.status, it.reason) == ("pending", "no_evidence")


def test_conflicting_spellings_across_documents_is_pending():
    it = decide_status(_m(), [_ev("Musallam"), _ev("Musalam", doc="id2")])
    assert (it.status, it.reason) == ("pending", "cross_document_conflict")
    assert "Musallam" in it.detail and "Musalam" in it.detail


def test_translation_mismatch_is_pending_with_suggestion_only_when_near():
    it = decide_status(_m("Muslim"), [_ev("Musallam")])
    assert (it.status, it.reason, it.suggestion) == ("pending", "translation_mismatch", None)
    it = decide_status(_m("Mohamed"), [_ev("Mohammed")])
    assert (it.status, it.reason, it.suggestion) == ("pending", "translation_mismatch", "Mohammed")


def test_no_translation_is_pending_and_suggests_evidence():
    it = decide_status(_m(None), [_ev("Musallam")])
    assert (it.status, it.reason, it.suggestion) == ("pending", "no_translation", "Musallam")


def test_match_is_confirmed_ignoring_case_and_whitespace():
    it = decide_status(_m("  musallam "), [_ev("Musallam")])
    assert (it.status, it.reason) == ("confirmed", "evidence_match")
    assert it.translated_name == "  musallam "  # 원래 표기 보존


def test_all_evidence_invalid_is_validation_failed():
    it = decide_status(_m(), [_ev("Musallam", valid=False, failure="quote_not_in_segment")])
    assert (it.status, it.reason, it.detail) == ("pending", "validation_failed", "quote_not_in_segment")


def test_invalid_evidence_is_ignored_when_valid_exists():
    it = decide_status(_m(), [_ev("Musallam"), _ev("Other", doc="id2", valid=False, failure="name_not_in_quote")])
    assert (it.status, it.reason) == ("confirmed", "evidence_match")


def test_extraction_error_and_missing_entity_come_first():
    assert decide_status(_m(error="empty_value"), [_ev("Musallam")]).reason == "extraction_failed"
    assert decide_status(_m(entity_id=None), [_ev("Musallam")]).reason == "no_entity_id"


def test_dictionary_confirms_only_without_evidence_and_without_conflict():
    assert decide_status(_m(), [], _entry()).reason == "dictionary_match"
    assert decide_status(_m("Muslim"), [], _entry()).reason == "translation_mismatch"
    assert decide_status(_m(None), [], _entry()).reason == "no_translation"
    conflict = decide_status(_m(), [_ev("Musalam")], _entry("Musallam"))
    assert conflict.reason == "cross_document_conflict" and "dictionary" in conflict.detail
    same = decide_status(_m(), [_ev("Musallam")], _entry("Musallam"))
    assert same.reason == "evidence_match"


@pytest.mark.parametrize("etype", ["person", "organization", "other"])
def test_rules_do_not_depend_on_entity_type(etype):
    assert decide_status(_m(etype=etype), [_ev("Musallam")]).status == "confirmed"
    assert decide_status(_m("X", etype=etype), [_ev("Musallam")]).reason == "translation_mismatch"


def test_strict_equal_and_near_match():
    assert strict_equal("Gulf  Trading Company", "gulf trading company")
    assert not strict_equal("Gulf Trading Co.", "Gulf Trading Company")
    assert near_match("Mohamed", "Mohammed") and not near_match("Muslim", "Musallam")
