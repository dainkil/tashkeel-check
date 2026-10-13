"""단계 2 틀: 묶음 검색이 출처와 함께 결과를 내는지만 본다(검색 품질은 재지 않는다)."""

from tashkeel_check.rag import BundleIndex, make_bundle_search_tool
from tashkeel_check.rag.bundle import PracticeEmbeddings
from tashkeel_check.text import segment_text, tokenize


def _index(tmp_path):
    (tmp_path / "id_excerpt.txt").write_text("SYNTHETIC\nالاسم: راشد مسلم الكعبي\nName: Rashid Musallam Al Kaabi\n", encoding="utf-8")
    (tmp_path / "letter.txt").write_text("SYNTHETIC\nDear Mr. Rashid Musallam Al Kaabi,\nThank you.\n", encoding="utf-8")
    return BundleIndex.from_dir(tmp_path, embeddings=PracticeEmbeddings(), embedding_label="practice")


def test_arabic_exact_match_returns_bilingual_latin_line(tmp_path):
    hits = _index(tmp_path).search("مسلم", ["Musallam", "Muslim"])
    exact = [h for h in hits if h.method == "arabic_exact"]
    assert exact and exact[0].source == "id_excerpt.txt"
    assert any("Musallam" in c for c in exact[0].latin_candidates)


def test_romanized_match_keeps_vowels(tmp_path):
    hits = _index(tmp_path).search("", ["Musallam"])
    assert {h.source for h in hits if h.method == "romanized"} == {"id_excerpt.txt", "letter.txt"}
    assert not [h for h in _index(tmp_path).search("", ["Muslim"]) if h.method == "romanized"]


def test_vector_hits_carry_parent_source(tmp_path):
    hits = [h for h in _index(tmp_path).search("الكعبي", ["Al Kaabi"]) if h.method == "vector"]
    assert hits and all(h.source in {"id_excerpt.txt", "letter.txt"} and h.parent_id for h in hits)


def test_search_tool_factory_uses_token_ids(tmp_path):
    tokens = tokenize(segment_text("وكّل السيد راشد مسلم الكعبي"))
    log = []
    tool = make_bundle_search_tool(_index(tmp_path))(tokens, log)
    out = tool.invoke({"token_ids": [3], "romanized_candidates": ["Musallam"]})
    assert out and log[0]["tool"] == "search_bundle"
