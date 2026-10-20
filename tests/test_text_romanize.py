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


def test_match_spelling_v1_spelling_conventions():
    # EXP-001 dev에서 v0가 놓친 영문 표기 관례 (ADR-015)
    assert match_spelling("Abdul Aziz", "'abd al-'aziiz")
    assert match_spelling("Abdelaziz", "'abd al-'aziiz")
    assert match_spelling("Abdurrahman", "'abd al-rahman")
    assert match_spelling("Abdullah", romanize("عَبْد اللّٰه"))
    assert match_spelling("Al Hafith", "al-hafiz")  # ظ·ذ·ث·ض·ز의 th·dh·z·d
    assert match_spelling("Dhaif", "dayf")
    assert match_spelling("Tarek", "tariq")  # q·k는 엄격 일치에서도 같다
    assert match_spelling("Ahmed", "ahmad") and match_spelling("Yousef", "yuusuf")  # 영문 e는 a·i·u 어느 것도 된다
    assert match_spelling("Al Touqi", "al-tawqiyy")  # 영문 o·ou는 u 또는 aw
    assert match_spelling("Hamadeh", "hamada") and match_spelling("Lujaina", "lujaynah")
    assert match_spelling("Al Sayah", "al-sayyah") and match_spelling("Bakry", "bakrii")
    assert match_spelling("Al Zaabi", "al-za'abiyy")


def test_match_spelling_v1_rejects_vowel_differences():
    # v0는 5자 이상이면 편집 거리 1을 같은 이름으로 봐서 다른 독법을 일치로 셌다 (ADR-015)
    assert not match_spelling("Hajjaj", "hujaj")
    assert not match_spelling("Al Bashri", "al-bashariyy")
    assert not match_spelling("Rostam", "rustum")
    assert not match_spelling("Jamaan", "jum'an")
    assert not match_spelling("Obadah", "'abbadah")  # o→aw에 자음 한 글자 허용을 겹치지 않는다
    assert not match_spelling("Gazzaz", "qazzaz")
    assert match_spelling("Gazzaz", "qazzaz", dialect=True)


def test_spelling_in_text_finds_multiword_span():
    assert spelling_in_text("Hamad Al Muslim", "Principal: Salem bin Hamad Al Muslim")
    assert not spelling_in_text("Musallam", "Principal: Salem bin Hamad Al Muslim")
