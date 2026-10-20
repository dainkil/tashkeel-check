from tashkeel_check.data.names import align


def test_align_with_connector_and_article():
    assert align("راشد بن حميد النعيمي", "Rashid Bin Humaid Al Nuaimi") == [
        ("راشد", "Rashid", "given"),
        ("حميد", "Humaid", "middle"),
        ("النعيمي", "Al Nuaimi", "family"),
    ]


def test_align_hyphenated_article_and_compound_units():
    assert align("سعيد رشيد القبيسي", "Saeed Rashed Al-Qubaisi")[2] == ("القبيسي", "Al Qubaisi", "family")
    assert align("راشد عبد الله النعيمي", "Rashid Abdullah Al Noaimi")[1] == ("عبد الله", "Abdullah", "middle")
    assert align("محمد بن راشد آل مكتوم", "Mohammed bin Rashid Al Maktoum")[2] == ("آل مكتوم", "Al Maktoum", "family")


def test_align_strips_honorifics():
    assert align("الشيخ سعيد سالم", "Sheikh Saeed Salem") == [("سعيد", "Saeed", "given"), ("سالم", "Salem", "family")]


def test_align_returns_none_when_units_differ():
    assert align("راشد بن محمد آل مكتوم", "Prince Rashid bin Mohammed of Dubai") is None
    assert align("رجاء القرق", "H.E. Dr Raja Easa Al Gurg") is None


def test_align_rejects_implausible_pairs_and_non_ascii_spellings():
    assert align("جابر الصباح", "Jaber al Ahmad") is None  # الصباح ↔ al Ahmad: 첫 글자가 맞지 않는 부분 이름 별칭
    assert align("حسن مقبول", "Hassan Makabūla") is None  # 여권 MRZ는 A~Z만 쓴다
    assert align("رجاء القرق", "Raja Al Gurg") == [("رجاء", "Raja", "given"), ("القرق", "Al Gurg", "family")]
    assert align("محمد مقبول", "M Maqbool") is None  # 머리글자


def test_align_v1_requires_arabic_script_and_matching_prefixes():
    assert align("Khaleghian", "Manager") is None  # Wikidata 아랍어 레이블이 라틴 문자인 경우
    assert align("إبراهيم الحمادي", "Abu Aws Al Hammadi") is None  # أبو 없는 이름 ↔ Abu 별칭
    assert align("عبد العزيز الحمادي", "Aziz Al Hammadi") is None  # Abdul을 뺀 별칭
    assert align("حبيب عبدالنبي مكي", "Habib Abdul Nabi Macki")[1] == ("عبدالنبي", "Abdul Nabi", "middle")
