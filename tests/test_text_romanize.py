from tashkeel_check.romanize import match_spelling, romanize, romanize_display, spelling_in_text
from tashkeel_check.text import normalize_key, render_token_table, segment_text, tokenize


def test_tokenize_ids_offsets_and_scripts():
    segs = segment_text("وكالة خاصة\n\nPrincipal: Salem bin Hamad, No. 12/2026")
    assert [s["segment_id"] for s in segs] == ["s01", "s02"]
    toks = tokenize(segs)
    assert [t["id"] for t in toks] == list(range(len(toks)))
    assert [t["script"] for t in toks][:3] == ["ar", "ar", "latin"]
    assert toks[-1]["text"] == "12/2026" and toks[-1]["script"] == "num"
    for t in toks:
        seg = next(s for s in segs if s["segment_id"] == t["segment_id"])
        assert seg["text"][t["start"] : t["end"]] == t["text"]


def test_token_table_lists_only_arabic():
    segs = segment_text("وكالة خاصة\nPrincipal: Salem")
    table = render_token_table(segs, tokenize(segs))
    assert "0=وكالة" in table and "Salem" not in table


def test_normalize_key_unifies_hamza_and_ta_marbuta():
    assert normalize_key("أحمد") == normalize_key("احمد")
    assert normalize_key("وَكالَةٌ") == normalize_key("وكاله")


def test_romanize_keeps_vowels_and_gemination():
    assert romanize("مُسَلَّم") == "musallam"
    assert romanize("مُسْلِم") == "muslim"
    assert romanize("مُحَمَّد") == "muhammad"
    assert romanize("رَبٌّ") == "rabbun"  # NFC에서 탄윈이 샷다보다 앞에 와도 겹자음이 자음 뒤에 붙는다
    assert romanize_display("رَشِيد") == "Rashid"


def test_match_spelling_variants_and_distinctions():
    assert match_spelling("Rashid", "Rashed")
    assert match_spelling("Saeed", romanize("سَعِيد"))
    assert match_spelling("Mohammed", romanize("مُحَمَّد"))
    assert match_spelling("Al Nuaimi", romanize("النُعَيْمِيّ"))
    assert match_spelling("AlQubaisi", "Al Qubaisi")
    assert not match_spelling("Musallam", "Muslim")
    assert not match_spelling("Hamad", "Hamd")  # 짧은 이름은 편집 거리 1도 다른 이름으로 본다
    assert not match_spelling("Gurg", romanize("القُرْق"))
    assert match_spelling("Gurg", romanize("القُرْق"), dialect=True)


def test_spelling_in_text_finds_multiword_span():
    assert spelling_in_text("Hamad Al Muslim", "Principal: Salem bin Hamad Al Muslim")
    assert not spelling_in_text("Musallam", "Principal: Salem bin Hamad Al Muslim")
