"""회사 문서 보관함(ADR-022): 구절 만들기, 단어 단위 이름 일치, 고객 분리, 이번 서류 빼기, 순서, 제안 확인.

LLM 없이 코드만 본다. Postgres 저장소는 db 마커.
"""

from __future__ import annotations

import os

import pytest

from tashkeel_check.archive import CompanyArchive, InMemoryArchiveStore, build_passages, name_in_text, name_words
from tashkeel_check.archive.search import search_records
from tashkeel_check.archive.store import now, text_sha256
from tashkeel_check.bundle.dictionary import DOCUMENT_SCOPE, DictionaryEntry, InMemoryDictionary
from tashkeel_check.rag.bundle import PracticeEmbeddings
from tashkeel_check.text import normalize_key, segment_text

LEASE = "عقد إيجار سكني\nالمؤجر: نوال الحربي (Nawal Al-Harbi)، مديرة شركة الريان\nالمستأجر: شركة النخلة\n"
INVOICE = "فاتورة\nالسيدة نوال الحربي، معلمة في مدرسة الرياض\nNoual Al Harbi\n"


def _archive() -> CompanyArchive:
    return CompanyArchive(InMemoryArchiveStore(), PracticeEmbeddings(), "practice")


def test_passages_keep_only_arabic_segments_with_latin_nearby():
    segs = segment_text(LEASE)
    rows = build_passages("acme", "d1", "lease.txt", text_sha256(segs), segs, now())
    # s01은 다음 구간(s02)에 라틴 문자가 있어 남고, s03은 라틴 문자가 없어 빠진다
    assert [p.segment_id for p in rows] == ["s01", "s02"]
    assert rows[1].latin_spans == ["Nawal Al-Harbi"]
    assert rows[0].hit_id != rows[1].hit_id and len(rows[0].hit_id) == 10


@pytest.mark.parametrize(
    ("name", "text", "hit"),
    [
        ("نوال الحربي", "المؤجر: نوال الحربي (Nawal)", True),
        ("نوال", "ونوال حاضرة", True),  # 한 글자 접두 و
        ("نوال", "نوالي حاضر", False),  # 다른 단어의 일부
        ("نوال الحربي", "نوال بنت محمد الحربي", False),  # 연속하지 않음
        ("شركة الريان", "مديرة شركة الريان.", True),
    ],
)
def test_name_in_text_is_word_based(name, text, hit):
    assert name_in_text(name_words(name), normalize_key(text)) is hit


def test_customers_never_see_each_other_and_current_document_is_excluded():
    a = _archive()
    lease = segment_text(LEASE)
    a.index_document("acme", "d1", "lease.txt", lease)
    assert [p.document_id for p in a.find("acme", "نوال", None, None)] == ["d1"]
    assert a.find("other", "نوال", None, None) == []
    assert a.find("acme", "نوال", "d1", None) == []  # 이번 서류
    assert a.find("acme", "نوال", "d9", text_sha256(lease)) == []  # 같은 파일을 다른 ID로 다시 올림
    hid = a.find("acme", "نوال", None, None)[0].hit_id
    assert a.get_passage("other", hid) is None


def test_short_names_are_not_searched():
    a = _archive()
    a.index_document("acme", "d1", "x.txt", segment_text("في الرياض\nIn Riyadh\n"))
    assert a.find("acme", "في", None, None) == []


def test_hits_are_ranked_by_context_similarity_then_recency():
    a = _archive()
    a.index_document("acme", "lease", "lease.txt", segment_text(LEASE))
    a.index_document("acme", "invoice", "invoice.txt", segment_text(INVOICE))
    names = [{"token_ids": [1], "arabic": "نوال الحربي", "context": "المؤجر نوال الحربي مديرة شركة الريان"}]
    rows = search_records(a, None, "acme", names, None, None)
    docs = [h["document"] for h in rows[0]["hits"]]
    assert docs[0] == "lease.txt" and set(docs) == {"lease.txt", "invoice.txt"}
    assert rows[0]["hits"][0]["similarity"] > rows[0]["hits"][1]["similarity"]


def test_confirmed_dictionary_name_short_circuits_archive():
    a = _archive()
    a.index_document("acme", "d1", "lease.txt", segment_text(LEASE))
    d = InMemoryDictionary()
    d.register(
        DictionaryEntry(
            customer_id="acme",
            entity_id=DOCUMENT_SCOPE,
            arabic_key=normalize_key("نوال الحربي"),
            arabic_name="نوال الحربي",
            english_name="Nawal Al-Harbi",
        )
    )
    rows = search_records(a, d, "acme", [{"token_ids": [1, 2], "arabic": "نوال الحربي"}], None, None)
    assert rows[0]["dictionary"]["english"] == "Nawal Al-Harbi" and rows[0]["hits"] == []
    other = search_records(a, d, "other", [{"token_ids": [1, 2], "arabic": "نوال الحربي"}], None, None)
    assert other[0]["dictionary"] is None and other[0]["hits"] == []


def test_verify_pick_checks_customer_document_name_and_letter_for_letter_spelling():
    a = _archive()
    a.index_document("acme", "d1", "lease.txt", segment_text(LEASE))
    hid = a.find("acme", "نوال الحربي", None, None)[0].hit_id
    assert a.verify_pick("acme", hid, "نوال الحربي", "Nawal Al-Harbi", "d2", None) is not None
    assert a.verify_pick("acme", hid, "نوال", "Nawal", "d2", None) is not None  # 이름 일부만
    assert a.verify_pick("acme", hid, "نوال الحربي", "Nawal Al-Harby", "d2", None) is None  # 글자가 다름
    assert a.verify_pick("acme", hid, "سالم", "Nawal", "d2", None) is None  # 그 이름이 구절에 없음
    assert a.verify_pick("acme", hid, "نوال", "Nawal", "d1", None) is None  # 이번 서류 자신
    assert a.verify_pick("other", hid, "نوال", "Nawal", "d2", None) is None  # 다른 고객
    assert a.verify_pick("acme", "0000000000", "نوال", "Nawal", "d2", None) is None  # 지어낸 구절


def test_delete_document_removes_its_passages_and_reindex_replaces():
    a = _archive()
    a.index_document("acme", "d1", "lease.txt", segment_text(LEASE))
    a.index_document("acme", "d1", "lease.txt", segment_text(LEASE))
    assert [d.n_passages for d in a.list_documents("acme")] == [2]
    assert a.delete_document("acme", "d1") is True
    assert a.find("acme", "نوال", None, None) == [] and a.list_documents("acme") == []
    assert a.delete_document("acme", "d1") is False


@pytest.mark.db
def test_db_archive_store_matches_memory_behaviour():
    from tashkeel_check.web.archive import DbArchiveStore
    from tashkeel_check.web.db import Database, new_id

    db = Database(os.environ["DATABASE_URL"])
    db.create_all()
    cust_a, cust_b, doc = f"a_{new_id()[:8]}", f"b_{new_id()[:8]}", new_id()
    a = CompanyArchive(DbArchiveStore(db), PracticeEmbeddings(), "practice")
    assert a.index_document(cust_a, doc, "lease.txt", segment_text(LEASE)) == 2
    found = a.find(cust_a, "نوال الحربي", None, None)
    assert found and {p.document_id for p in found} == {doc}
    assert found[0].embedding and found[0].embedding_model == "practice"
    assert a.find(cust_b, "نوال الحربي", None, None) == []
    assert a.verify_pick(cust_a, found[-1].hit_id, "نوال الحربي", "Nawal Al-Harbi", "other", None) is not None
    assert [d.document_id for d in a.list_documents(cust_a)] == [doc]
    assert a.delete_document(cust_b, doc) is False and a.delete_document(cust_a, doc) is True
    assert a.find(cust_a, "نوال", None, None) == []
