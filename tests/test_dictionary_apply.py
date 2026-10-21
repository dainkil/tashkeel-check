"""단일 문서 결과에 회사 사전 덧씌우기(ADR-021). LLM 없음."""

from __future__ import annotations

from tashkeel_check.bundle.dictionary import DOCUMENT_SCOPE, DictionaryEntry, InMemoryDictionary
from tashkeel_check.config import Settings
from tashkeel_check.dictionary_apply import apply_dictionary
from tashkeel_check.fake import OUTPUT_TOOL, FakeAgentModel, tool_call
from tashkeel_check.runner import run_document
from tashkeel_check.text import normalize_key

from .conftest import fake_analyze, ids_of


def _result(mini_doc, mini_tokens, items):
    translation = [{"segment_id": s["segment_id"], "english": "x"} for s in mini_doc["segments"]]
    reply = tool_call(OUTPUT_TOOL, {"translation": translation, "items": items})
    model = FakeAgentModel(responder=lambda messages, bound: reply)
    return run_document(mini_doc, "C1", model, Settings(), analyze_fn=fake_analyze)


def _item(token_ids, decision, adopted=None, evidence=None):
    return {
        "token_ids": token_ids,
        "type": "proper_noun",
        "candidates": [{"reading": None, "romanized": adopted or "Muslim", "source": "llm"}],
        "decision": decision,
        "adopted": adopted,
        "reason": "test",
        "confidence": None,
        "evidence": evidence,
    }


def _entry(customer, arabic, english, entity_id=DOCUMENT_SCOPE):
    return DictionaryEntry(
        customer_id=customer,
        entity_id=entity_id,
        arabic_key=normalize_key(arabic),
        arabic_name=arabic,
        english_name=english,
    )


def test_hold_becomes_dictionary_adopt_and_other_customer_is_ignored(mini_doc, mini_tokens):
    agent = ids_of(mini_tokens, "s04", ["مسلم"])
    res = _result(mini_doc, mini_tokens, [_item(agent, "hold")])
    d = InMemoryDictionary()
    d.register(_entry("acme", "مسلم", "Musallam"))
    out = apply_dictionary(res, d, "acme")
    assert [o.status for o in out] == ["dictionary_adopt"]
    assert out[0].english == "Musallam" and out[0].token_ids == agent and out[0].entry_id
    assert apply_dictionary(res, d, "other") == []
    assert apply_dictionary(res, d, None) == [] and apply_dictionary(res, None, "acme") == []


def test_document_evidence_that_disagrees_with_dictionary_is_conflict(mini_doc, mini_tokens):
    principal = ids_of(mini_tokens, "s02", ["المسلم"])
    ev = {"segment_id": "s03", "quote": "Al Muslim"}
    res = _result(mini_doc, mini_tokens, [_item(principal, "evidence_adopt", "Al Muslim", ev)])
    item = next(i for i in res.items if i.type == "proper_noun")
    assert item.final_decision == "evidence_adopt"
    d = InMemoryDictionary()
    d.register(_entry("acme", "المسلم", "Al Musallam"))
    out = apply_dictionary(res, d, "acme")
    assert [o.status for o in out] == ["conflict"] and out[0].document_spelling == "Al Muslim"
    d.register(_entry("acme", "المسلم", "al muslim"))  # 대소문자만 다르면 같은 표기
    assert [o.status for o in apply_dictionary(res, d, "acme")] == ["agree"]


def test_entity_scoped_entries_do_not_apply_to_documents(mini_doc, mini_tokens):
    agent = ids_of(mini_tokens, "s04", ["مسلم"])
    res = _result(mini_doc, mini_tokens, [_item(agent, "hold")])
    d = InMemoryDictionary()
    d.register(_entry("acme", "مسلم", "Musallam", entity_id="partner_1"))  # 묶음 경로의 대상 ID 항목
    assert apply_dictionary(res, d, "acme") == []


def test_in_memory_dictionary_list_and_delete():
    d = InMemoryDictionary()
    a = d.register(_entry("acme", "مسلم", "Muslim"))
    b = d.register(_entry("acme", "سالم", "Salem"))
    d.register(_entry("zeta", "سالم", "Salim"))
    assert {e.id for e in d.list_entries("acme")} == {a.id, b.id}
    again = d.register(_entry("acme", "مسلم", "Musallam"))
    assert again.id == a.id and d.lookup_verified_name("acme", DOCUMENT_SCOPE, "مسلم").english_name == "Musallam"
    assert d.delete(a.id, "zeta") is False and d.delete(a.id, "acme") is True
    assert [e.id for e in d.list_entries("acme")] == [b.id]


def test_name_text_strips_repeated_occurrences(mini_doc, mini_tokens):
    from tashkeel_check.dictionary_apply import name_text

    first = ids_of(mini_tokens, "s02", ["المسلم"])
    second = ids_of(mini_tokens, "s05", ["المسلم"])
    res = _result(mini_doc, mini_tokens, [_item(first + second, "hold")])
    item = next(i for i in res.items if i.type == "proper_noun")
    assert item.arabic == "المسلم المسلم" and name_text(item) == "المسلم"
    d = InMemoryDictionary()
    d.register(_entry("acme", "المسلم", "Al Musallam"))  # 한 번 나온 문서에서 등록한 표기
    out = apply_dictionary(res, d, "acme")
    assert [o.status for o in out] == ["dictionary_adopt"] and out[0].arabic == "المسلم"
    two = _result(mini_doc, mini_tokens, [_item(ids_of(mini_tokens, "s02", ["سالم", "حمد"]) * 2, "hold")])
    assert name_text(next(i for i in two.items if i.type == "proper_noun")) == "سالم حمد"
