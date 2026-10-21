"""가이드 3단계: 라벨 칸에서 고유명사를 뽑는다. 사람·회사·기관 라벨을 같은 규칙으로 다룬다."""

import pytest

from tashkeel_check.bundle.extractor import english_fields, extract_names, split_fields
from tashkeel_check.bundle.schemas import Document, Segment


def _doc(*texts, entity_id="e1", translated=None):
    return Document(
        document_id="d1",
        document_type="contract",
        segments=[
            Segment(segment_id=f"s{i:02d}", entity_id=entity_id, text=t, translated_name=translated)
            for i, t in enumerate(texts, start=1)
        ],
    )


def test_single_name_field():
    ms = extract_names(_doc("الاسم: مسلم", translated="Muslim"))
    assert len(ms) == 1
    m = ms[0]
    assert (m.arabic_name, m.translated_name, m.entity_type, m.entity_id) == ("مسلم", "Muslim", "person", "e1")
    assert m.mention_id == "d1:s01:1" and m.source == "label" and m.extraction_error is None


def test_multiple_fields_return_list_in_order():
    ms = extract_names(_doc("الاسم: مسلم", "الجهة: وزارة التجارة", "اسم الشركة: شركة الخليج"))
    assert [(m.arabic_name, m.entity_type) for m in ms] == [
        ("مسلم", "person"),
        ("وزارة التجارة", "organization"),
        ("شركة الخليج", "organization"),
    ]


def test_no_label_returns_empty():
    assert extract_names(_doc("حضر السيد سالم بن حمد", "Dear Sir,")) == []


def test_pipe_separated_fields_split_arabic_and_english():
    fields = split_fields("الاسم: مسلم | Name: Musallam")
    assert [(f.label, f.value, f.script) for f in fields] == [("الاسم", "مسلم", "ar"), ("Name", "Musallam", "latin")]
    ms = extract_names(_doc("الاسم: مسلم | Name: Musallam"))
    assert [m.arabic_name for m in ms] == ["مسلم"]
    assert [f.value for f in english_fields("الاسم: مسلم | Name: Musallam")] == ["Musallam"]


@pytest.mark.parametrize(
    "text",
    ["Company Name: Gulf Trading Co. | اسم الشركة: شركة الخليج للتجارة", "COMPANY: Gulf Trading | الشركة: شركة الخليج"],
)
def test_company_labels_are_case_insensitive_and_order_free(text):
    ms = extract_names(_doc(text))
    assert len(ms) == 1 and ms[0].entity_type == "organization" and ms[0].arabic_name.startswith("شركة")
    assert len(english_fields(text)) == 1


def test_unknown_label_is_ignored_but_known_label_in_same_line_is_kept():
    ms = extract_names(_doc("رقم الهوية: 784-1990 | الاسم: فاطمة أحمد"))
    assert [m.arabic_name for m in ms] == ["فاطمة أحمد"]


def test_empty_or_non_arabic_value_records_extraction_error():
    ms = extract_names(_doc("الاسم: ", "الاسم: 12345"))
    assert [m.extraction_error for m in ms] == ["empty_value", "value_not_arabic"]


def test_entity_type_from_bundle_overrides_label_type():
    ms = extract_names(_doc("الاسم: شركة الخليج"), entity_types={"e1": "organization"})
    assert ms[0].entity_type == "organization"


def test_arabic_key_normalizes_marks_and_alef():
    ms = extract_names(_doc("الاسم: أَحْمَد"))
    assert ms[0].arabic_name == "أَحْمَد" and ms[0].arabic_key == "احمد"
