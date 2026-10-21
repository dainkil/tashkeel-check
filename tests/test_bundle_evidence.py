"""가이드 4·5단계: 같은 대상 ID의 다른 서류에서만 근거를 찾고, 인용을 원문과 대조한다."""

from tashkeel_check.bundle.evidence import search_evidence, validate_evidence, validated
from tashkeel_check.bundle.extractor import extract_names
from tashkeel_check.bundle.schemas import Bundle, BundleEvidence, Document, Segment


def _bundle(*docs):
    return Bundle(bundle_id="b", documents=list(docs))


def _doc(doc_id, *segs, doc_type="x"):
    return Document(
        document_id=doc_id,
        document_type=doc_type,
        segments=[Segment(segment_id=f"s{i:02d}", entity_id=e, text=t) for i, (e, t) in enumerate(segs, start=1)],
    )


CONTRACT = _doc("contract", ("e1", "الاسم: مسلم"), ("org1", "اسم الشركة: شركة الخليج"))
ID_E1 = _doc("id1", ("e1", "الاسم: مسلم | Name: Musallam"))
ID_E2_SAME_ARABIC = _doc("id2", ("e2", "الاسم: مسلم | Name: Muslim"))
CR_ORG1 = _doc("cr", ("org1", "Company Name: Gulf Trading | اسم الشركة: شركة الخليج"))


def _mention(bundle, doc_id, idx=0):
    return extract_names(bundle.document(doc_id))[idx]


def test_evidence_comes_from_other_documents_with_same_entity_only():
    b = _bundle(CONTRACT, ID_E1, ID_E2_SAME_ARABIC, CR_ORG1)
    ev = search_evidence(b, _mention(b, "contract", 0))
    assert [(e.document_id, e.english_name) for e in ev] == [("id1", "Musallam")]
    assert ev[0].quote == "الاسم: مسلم | Name: Musallam" and ev[0].segment_id == "s01"


def test_same_arabic_name_different_entity_is_not_linked():
    b = _bundle(CONTRACT, ID_E2_SAME_ARABIC)
    assert search_evidence(b, _mention(b, "contract", 0)) == []


def test_organization_evidence_uses_same_rule():
    b = _bundle(CONTRACT, ID_E1, CR_ORG1)
    ev = search_evidence(b, _mention(b, "contract", 1))
    assert [(e.document_id, e.english_name) for e in ev] == [("cr", "Gulf Trading")]


def test_mention_without_entity_id_gets_no_evidence():
    b = _bundle(_doc("c", (None, "الاسم: مسلم")), ID_E1)
    assert search_evidence(b, _mention(b, "c")) == []


def test_own_document_is_not_evidence():
    b = _bundle(_doc("c", ("e1", "الاسم: مسلم"), ("e1", "Name: Musallam")))
    assert search_evidence(b, _mention(b, "c")) == []


def test_validate_rejects_missing_document_segment_quote_and_name():
    b = _bundle(CONTRACT, ID_E1)
    ok = BundleEvidence(
        document_id="id1", segment_id="s01", quote="الاسم: مسلم | Name: Musallam", english_name="Musallam"
    )
    assert validate_evidence(b, ok) == (True, None)
    assert validate_evidence(b, ok.model_copy(update={"document_id": "nope"})) == (False, "document_not_found")
    assert validate_evidence(b, ok.model_copy(update={"segment_id": "s09"})) == (False, "segment_not_found")
    assert validate_evidence(b, ok.model_copy(update={"quote": "Name: Muslim"})) == (False, "quote_not_in_segment")
    assert validate_evidence(b, ok.model_copy(update={"english_name": "Muslim"})) == (False, "name_not_in_quote")
    assert validate_evidence(b, ok.model_copy(update={"quote": "  "})) == (False, "empty_quote")


def test_validate_ignores_case_and_whitespace_but_not_spelling():
    b = _bundle(ID_E1)
    ev = BundleEvidence(document_id="id1", segment_id="s01", quote="name:   MUSALLAM", english_name="musallam")
    assert validate_evidence(b, ev) == (True, None)


def test_validated_marks_each_evidence():
    b = _bundle(CONTRACT, ID_E1)
    evs = validated(
        b,
        search_evidence(b, _mention(b, "contract", 0))
        + [BundleEvidence(document_id="id1", segment_id="s01", quote="Name: Fake", english_name="Fake")],
    )
    assert [(e.valid, e.failure) for e in evs] == [(True, None), (False, "quote_not_in_segment")]
