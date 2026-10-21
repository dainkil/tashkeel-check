"""여권 MRZ 해독과 성·이름 칸 합성, 그리고 같은 서류 안에서 인쇄 칸이 MRZ보다 우선하는 규칙."""

from __future__ import annotations

from tashkeel_check.bundle.evidence import search_evidence, validate_evidence, validated
from tashkeel_check.bundle.extractor import english_fields
from tashkeel_check.bundle.mrz import is_mrz_line, mrz_line1, mrz_name
from tashkeel_check.bundle.pipeline import bundle_mentions
from tashkeel_check.bundle.rules import decide_status
from tashkeel_check.bundle.schemas import Bundle, BundleEvidence, Document, Segment

LINE1 = "P<SAUAL<QAHTANI<<FATMA<AHMED<<<<<<<<<<<<<<<<"


def test_mrz_roundtrip():
    assert mrz_line1("Al Qahtani", "Fatma Ahmed") == LINE1 and len(LINE1) == 44
    assert mrz_name(LINE1) == "FATMA AHMED AL QAHTANI"
    assert (
        is_mrz_line(LINE1)
        and not is_mrz_line("Name: Fatma")
        and mrz_name("A1234567<0SAU9001015F3501015<<<<<<<<<<<<<<<<") is None
    )


def test_mrz_drops_non_letters_and_truncates():
    # 하이픈은 구분자가 되고, 39자를 넘는 이름은 잘린다. 둘 다 정확 일치가 깨져 대기가 된다(의도)
    assert mrz_name(mrz_line1("Al-Qahtani", "Fatma")) == "FATMA AL QAHTANI"
    long = mrz_line1("Al Hathloul", "Mohamed bin Najm bin Suleiman")
    assert len(long) == 44 and mrz_name(long) == "MOHAMED BIN NAJM BIN SULEI AL HATHLOUL"


def test_english_fields_compose_surname_and_given_names():
    fields = english_fields("Surname: AL QAHTANI | Given Names: FATMA AHMED")
    assert [(f.label, f.value) for f in fields] == [("Given Names + Surname", "FATMA AHMED AL QAHTANI")]
    assert [(f.label, f.value) for f in english_fields(LINE1)] == [("MRZ", "FATMA AHMED AL QAHTANI")]
    assert [f.value for f in english_fields("Surname: AL QAHTANI")] == ["AL QAHTANI"]  # 하나만 있으면 그대로


def _bundle(passport_segments: list[Segment]) -> Bundle:
    return Bundle(
        bundle_id="b",
        documents=[
            Document(
                document_id="register",
                document_type="commercial_register",
                segments=[
                    Segment(
                        segment_id="s01",
                        text="اسم المالك: فاطمة أحمد القحطاني",
                        entity_id="p1",
                        translated_name="Fatma Ahmed Al Qahtani",
                    )
                ],
            ),
            Document(document_id="passport", document_type="passport", segments=passport_segments),
        ],
    )


def test_mrz_only_passport_confirms_by_decoded_name():
    bundle = _bundle([Segment(segment_id="s03", text=LINE1, entity_id="p1")])
    mention = bundle_mentions(bundle)[0]
    evidence = validated(bundle, search_evidence(bundle, mention))
    assert [(e.english_name, e.valid) for e in evidence] == [("FATMA AHMED AL QAHTANI", True)]
    assert decide_status(mention, evidence).status == "confirmed"


def test_printed_field_wins_over_mrz_in_same_document():
    bundle = _bundle(
        [
            Segment(segment_id="s02", text="Surname: AL-QAHTANI | Given Names: FATMA AHMED", entity_id="p1"),
            Segment(segment_id="s03", text=mrz_line1("Al-Qahtani", "Fatma Ahmed"), entity_id="p1"),
        ]
    )
    mention = bundle_mentions(bundle)[0]
    evidence = search_evidence(bundle, mention)
    assert [e.segment_id for e in evidence] == ["s02"]  # MRZ(하이픈이 빠진 꼴)는 같은 서류의 인쇄 칸에 밀린다
    item = decide_status(mention, validated(bundle, evidence))
    assert (item.status, item.reason) == ("pending", "translation_mismatch")  # AL-QAHTANI ≠ Al Qahtani


def test_validate_accepts_decoded_name_but_not_other_names():
    bundle = _bundle([Segment(segment_id="s03", text=LINE1, entity_id="p1")])
    ok = BundleEvidence(document_id="passport", segment_id="s03", quote=LINE1, english_name="Fatma Ahmed Al Qahtani")
    bad = ok.model_copy(update={"english_name": "Fatima Ahmed Al Qahtani"})
    assert validate_evidence(bundle, ok) == (True, None)
    assert validate_evidence(bundle, bad) == (False, "name_not_in_quote")
