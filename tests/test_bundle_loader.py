"""가이드 1·2단계: 묶음 읽기와 구조 검증. 파일 없음과 형식 오류를 구분한다."""

import json

import pytest
from pydantic import ValidationError

from tashkeel_check.bundle import Bundle, BundleNotFound, InvalidBundle, load_bundle, parse_bundle
from tashkeel_check.bundle.loader import split_bundle_gold
from tashkeel_check.bundle.schemas import ReviewItem
from tashkeel_check.errors import InputError

SAMPLE = {
    "bundle_id": "b1",
    "documents": [
        {
            "document_id": "contract_001",
            "document_type": "contract",
            "segments": [{"segment_id": "s01", "entity_id": "e1", "text": "الاسم: مسلم", "translated_name": "Muslim"}],
        },
        {
            "document_id": "id_001",
            "document_type": "identity",
            "segments": [{"segment_id": "s01", "entity_id": "e1", "text": "الاسم: مسلم | Name: Musallam"}],
        },
    ],
}


def test_load_bundle_reads_arabic_intact(tmp_path):
    p = tmp_path / "b.json"
    p.write_text(json.dumps(SAMPLE, ensure_ascii=False), encoding="utf-8")
    b = load_bundle(p)
    assert [d.document_id for d in b.documents] == ["contract_001", "id_001"]
    assert b.documents[0].segments[0].text == "الاسم: مسلم"


def test_missing_file_and_bad_json_are_different_errors(tmp_path):
    with pytest.raises(BundleNotFound):
        load_bundle(tmp_path / "nope.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(InvalidBundle) as exc:
        load_bundle(bad)
    assert "JSON" in str(exc.value)
    assert not issubclass(BundleNotFound, InvalidBundle)
    assert issubclass(BundleNotFound, InputError) and issubclass(InvalidBundle, InputError)


def test_structure_errors_are_invalid_bundle(tmp_path):
    with pytest.raises(InvalidBundle):
        parse_bundle({"bundle_id": "b", "documents": []})
    with pytest.raises(InvalidBundle):
        parse_bundle({"bundle_id": "b", "documents": [{"document_id": "d", "segments": []}]})
    with pytest.raises(InvalidBundle):
        parse_bundle([])
    dup = json.loads(json.dumps(SAMPLE))
    dup["documents"][1]["document_id"] = "contract_001"
    with pytest.raises(InvalidBundle) as exc:
        parse_bundle(dup)
    assert "duplicate document_id" in str(exc.value)


def test_gold_is_stripped_from_input():
    obj = dict(SAMPLE, gold={"review_items": []})
    bundle, gold = split_bundle_gold(obj)
    assert gold == {"review_items": []}
    assert "gold" not in bundle.model_dump()
    assert parse_bundle(obj).bundle_id == "b1"


def test_review_item_rejects_unknown_status_and_wrong_types():
    base = dict(
        mention_id="m",
        document_id="d",
        segment_id="s",
        entity_id="e",
        entity_type="person",
        arabic_name="مسلم",
        translated_name=None,
        evidence=[],
        reason="no_evidence",
    )
    with pytest.raises(ValidationError):
        ReviewItem(status="maybe", **base)
    with pytest.raises(ValidationError):
        ReviewItem(status="pending", **dict(base, evidence="none"))
    with pytest.raises(ValidationError):
        Bundle(bundle_id="b", documents=[], extra_field=1)
