"""아랍어 전체 이름과 영문 표기를 이름 단위로 정렬한다. EXP-001과 합성 문서 생성기가 같이 쓴다.

정렬 규칙(계획 6.1절): بن/بنت ↔ bin/bint, ال+X ↔ Al X, عبد/أبو/آل + X는 한 단위.
단위 수나 연결어 위치가 다르면 정렬하지 않고 None을 돌려준다.
v1(EXP-001 개발용 표본에서 고침, ADR-015): 아랍어 단위는 아랍 문자만, عبد·أبو 접두는 양쪽이 같이 있어야 한다.
"""

from __future__ import annotations

import re

from ..text import normalize_key

ALIGN_VERSION = "v1"

AR_HONORIFICS = {
    normalize_key(w)
    for w in ["الشيخ", "الشيخة", "الأمير", "الأميرة", "الدكتور", "الدكتورة", "د", "سمو", "معالي", "السيد", "السيدة"]
}
AR_CONNECTORS = {normalize_key(w) for w in ["بن", "بنت", "ابن"]}
AR_JOIN_NEXT = {normalize_key(w) for w in ["عبد", "أبو", "آل"]}
EN_HONORIFICS = {
    "he",
    "hh",
    "hrh",
    "dr",
    "sheikh",
    "shaikh",
    "sheikha",
    "shaikha",
    "prince",
    "princess",
    "mr",
    "mrs",
    "ms",
    "eng",
    "his",
    "her",
    "highness",
    "excellency",
    "sir",
}
EN_CONNECTORS = {"bin", "bint", "ibn", "bent", "ben"}
EN_ARTICLES = {"al", "el", "ul"}
EN_JOIN_NEXT = {"abdul", "abdel", "abd", "abdal", "abu", "abou"} | EN_ARTICLES


def ar_units(full: str) -> list[tuple[str, str]]:
    """[(단위, 종류)] 종류는 name | conn."""
    words = re.sub(r"\(.*?\)", " ", full).split()
    words = [w for w in words if normalize_key(w) not in AR_HONORIFICS]
    units: list[tuple[str, str]] = []
    i = 0
    while i < len(words):
        key = normalize_key(words[i])
        if key in AR_JOIN_NEXT and i + 1 < len(words):
            units.append((f"{words[i]} {words[i + 1]}", "name"))
            i += 2
        elif key in AR_CONNECTORS:
            units.append((words[i], "conn"))
            i += 1
        else:
            units.append((words[i], "name"))
            i += 1
    return units


def en_units(full: str) -> list[tuple[str, str]]:
    s = re.sub(r"\(.*?\)", " ", full)
    s = re.split(r"\s+of\s+", s, maxsplit=1)[0]
    words = [w for w in re.split(r"[\s\-]+", s) if w]
    words = [w for w in words if w.lower().replace(".", "").strip(",") not in EN_HONORIFICS and w.strip(".,")]
    units: list[tuple[str, str]] = []
    i = 0
    while i < len(words):
        low = words[i].lower().strip(".,")
        if low in EN_JOIN_NEXT and i + 1 < len(words) and words[i + 1].lower() not in EN_CONNECTORS:
            units.append((f"{words[i]} {words[i + 1]}".strip(".,"), "name"))
            i += 2
        elif low in EN_CONNECTORS:
            units.append((words[i].strip(".,"), "conn"))
            i += 1
        else:
            units.append((words[i].strip(".,"), "name"))
            i += 1
    return units


ASCII_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z' ]*$")
# Wikidata 아랍어 레이블에 라틴 문자가 섞인 경우(Khaleghian)를 거른다
ARABIC_UNIT_RE = re.compile(r"^[\u0600-\u06FF ]+$")
AR_ABD, AR_ABU = normalize_key("عبد"), normalize_key("أبو")
EN_ABD, EN_ABU = {"abd", "abdul", "abdel", "abdal"}, {"abu", "abou"}
# 첫 글자 대응: 아랍어 첫 글자(관사 뒤)를 나타낼 수 있는 라틴 첫 글자. 별칭이 부분 이름일 때 생기는 엉뚱한 짝을 거른다.
FIRST_LETTER = {
    "ا": "aeiou",
    "أ": "aeiou",
    "إ": "aeiou",
    "آ": "aeiou",
    "ع": "aeiou",
    "ء": "aeiou",
    "ب": "bp",
    "ت": "t",
    "ث": "tsd",
    "ج": "jgy",
    "ح": "h",
    "خ": "kh",
    "د": "d",
    "ذ": "dtz",
    "ر": "r",
    "ز": "z",
    "س": "sc",
    "ش": "sc",
    "ص": "s",
    "ض": "d",
    "ط": "t",
    "ظ": "zdt",
    "غ": "g",
    "ف": "f",
    "ق": "qkg",
    "ك": "kc",
    "ل": "l",
    "م": "m",
    "ن": "n",
    "ه": "h",
    "و": "wou",
    "ي": "yie",
}


def _strip_article_ar(unit: str) -> str:
    key = normalize_key(unit)
    for prefix in ("ال ", "ال"):  # "آل X"는 normalize_key에서 "ال X"가 된다
        if key.startswith(prefix) and len(key) > len(prefix) + 1:
            return key[len(prefix) :]
    return key


def _strip_article_en(unit: str) -> str:
    words = unit.split()
    if len(words) > 1 and words[0].lower() in EN_ARTICLES:
        words = words[1:]
    return " ".join(words)


def _prefix_consistent(ar_unit: str, en_unit: str) -> bool:
    """عبد X ↔ Abdul X, أبو X ↔ Abu X처럼 접두가 양쪽에 같이 있는지.

    별칭이 접두를 빼거나(Aziz) 다른 이름(Abu Aws)일 때를 거른다."""
    ar_key, en_low = normalize_key(ar_unit), en_unit.lower()
    ar_first, en_first = ar_key.split()[0], en_low.split()[0]
    if ar_first == AR_ABD or en_first in EN_ABD:  # 아랍어는 عبدالنبي처럼 붙여 쓰기도 한다
        return ar_key.startswith(AR_ABD) and en_low.startswith("abd")
    if ar_first == AR_ABU or en_first in EN_ABU:
        return ar_key.startswith(AR_ABU) and en_low.startswith(("ab", "bu", "bo"))
    return True


def plausible_pair(ar_unit: str, en_unit: str) -> bool:
    """아랍어 단위가 아랍 문자이고, 영문 단위가 두 글자 이상의 ASCII 이름이며, 첫 글자와 접두가 대응하는지."""
    if not ARABIC_UNIT_RE.match(ar_unit) or not ASCII_NAME_RE.match(en_unit):
        return False
    if not _prefix_consistent(ar_unit, en_unit):
        return False
    ar, en = _strip_article_ar(ar_unit), _strip_article_en(en_unit).lower()
    if not ar or len(en.replace(" ", "").replace("'", "")) < 2:  # 머리글자(M 등)는 표기가 아니다
        return False
    return en[0] in FIRST_LETTER.get(ar[0], en[0])


def align(ar_full: str, en_full: str) -> list[tuple[str, str, str]] | None:
    """[(아랍어 단위, 영문 단위, 위치)] 위치는 given | middle | family. 정렬 실패 시 None.

    단위 수·연결어 위치가 다르거나, 짝 하나라도 첫 글자 대응·ASCII 조건을 못 맞추면 정렬하지 않는다.
    """
    ar, en = ar_units(ar_full), en_units(en_full)
    if not ar or len(ar) != len(en) or [k for _, k in ar] != [k for _, k in en]:
        return None
    if not all(plausible_pair(a, e) for (a, k), (e, _) in zip(ar, en, strict=True) if k == "name"):
        return None
    name_idx = [i for i, (_, k) in enumerate(ar) if k == "name"]
    pairs = []
    for rank, i in enumerate(name_idx):
        if rank == 0:
            pos = "given"
        elif rank == len(name_idx) - 1:
            pos = "family"
        else:
            pos = "middle"
        pairs.append((ar[i][0], en[i][0], pos))
    return pairs
