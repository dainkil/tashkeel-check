"""가이드 6단계 완료 기준: 샘플 묶음의 Muslim/Musallam 차이를 확인 대기로 돌린다."""

from pathlib import Path

from tashkeel_check.bundle import load_bundle, review_bundle
from tashkeel_check.bundle.dictionary import DictionaryEntry, InMemoryDictionary
from tashkeel_check.bundle.pipeline import bundle_mentions
from tashkeel_check.bundle.schemas import Bundle, Document, Segment

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "bundles" / "sample_bundle.json"


def test_sample_bundle_finds_mismatch_and_confirms_match():
    items = review_bundle(load_bundle(SAMPLE))
    by_entity = {it.entity_id: it for it in items}
    assert set(by_entity) == {"person_001", "org_001"}
    assert (by_entity["person_001"].status, by_entity["person_001"].reason) == ("pending", "translation_mismatch")
    assert (by_entity["org_001"].status, by_entity["org_001"].reason) == ("confirmed", "evidence_match")
    assert by_entity["person_001"].evidence[0].document_id == "id_001"


def test_bilingual_source_segments_are_not_review_targets():
    b = load_bundle(SAMPLE)
    assert {m.document_id for m in bundle_mentions(b)} == {"contract_001"}


def test_review_is_deterministic():
    b = load_bundle(SAMPLE)
    assert [i.model_dump() for i in review_bundle(b)] == [i.model_dump() for i in review_bundle(b)]


def test_dictionary_is_scoped_to_customer_and_entity():
    b = Bundle(
        bundle_id="b",
        customer_id="c1",
        documents=[
            Document(
                document_id="d",
                document_type="contract",
                segments=[Segment(segment_id="s01", entity_id="e1", text="الاسم: مسلم", translated_name="Musallam")],
            )
        ],
    )
    d = InMemoryDictionary()
    d.register(
        DictionaryEntry(
            customer_id="c2", entity_id="e1", arabic_key="مسلم", arabic_name="مسلم", english_name="Musallam"
        )
    )
    assert review_bundle(b, d)[0].reason == "no_evidence"  # 다른 고객의 사전은 보지 않는다
    d.register(
        DictionaryEntry(
            customer_id="c1", entity_id="e9", arabic_key="مسلم", arabic_name="مسلم", english_name="Musallam"
        )
    )
    assert review_bundle(b, d)[0].reason == "no_evidence"  # 같은 표기, 다른 대상
    d.register(
        DictionaryEntry(
            customer_id="c1", entity_id="e1", arabic_key="مسلم", arabic_name="مسلم", english_name="Musallam"
        )
    )
    assert review_bundle(b, d)[0].reason == "dictionary_match"
    assert review_bundle(b.model_copy(update={"customer_id": None}), d)[0].reason == "no_evidence"
