"""모음 표기된 아랍어를 ASCII 로마자로 옮기고, 영문 표기끼리 같은 이름인지 판정한다.

규칙 버전은 MATCHER_VERSION으로 기록한다. v1은 EXP-001 개발용 표본에서 고쳐 고정한 규칙이다(ADR-015).
모음을 살려 비교한다. 자음만 비교하면 Muslim과 Musallam이 같아진다.
"""

from __future__ import annotations

import re
from functools import lru_cache

from .text import dediac, nfc

MATCHER_VERSION = "v1"

FATHA, DAMMA, KASRA, SUKUN, SHADDA, DAGGER = "َ", "ُ", "ِ", "ْ", "ّ", "ٰ"
TANWEEN = {"ً": "an", "ٌ": "un", "ٍ": "in"}
VOWEL_MARKS = {FATHA, DAMMA, KASRA, SHADDA, *TANWEEN}
CONSONANTS = {
    "ب": "b",
    "ت": "t",
    "ث": "th",
    "ج": "j",
    "ح": "h",
    "خ": "kh",
    "د": "d",
    "ذ": "dh",
    "ر": "r",
    "ز": "z",
    "س": "s",
    "ش": "sh",
    "ص": "s",
    "ض": "d",
    "ط": "t",
    "ظ": "z",
    "ع": "'",
    "غ": "gh",
    "ف": "f",
    "ق": "q",
    "ك": "k",
    "ل": "l",
    "م": "m",
    "ن": "n",
    "ه": "h",
    "ء": "'",
    "ؤ": "'",
    "ئ": "'",
}


def _drop_letters(word: str, n: int) -> str:
    """앞에서 글자 n개(딸린 기호 포함)를 뗀다."""
    seen = 0
    for i, ch in enumerate(word):
        if dediac(ch):
            if seen == n:
                return word[i:]
            seen += 1
    return ""


def _romanize_word(word: str) -> str:
    prefix = ""
    base = word
    if dediac(word).startswith("ال") and len(dediac(word)) > 3:
        prefix, base = "al-", _drop_letters(word, 2)
    out: list[str] = []
    last_cons, last_cons_idx = "", -1

    def cons(value: str) -> None:
        nonlocal last_cons, last_cons_idx
        last_cons, last_cons_idx = value, len(out)
        out.append(value)

    for i, ch in enumerate(base):
        nxt = base[i + 1] if i + 1 < len(base) else ""
        prev = out[-1] if out else ""
        if ch == FATHA:
            out.append("a")
        elif ch == DAMMA:
            out.append("u")
        elif ch == KASRA:
            out.append("i")
        elif ch in TANWEEN:
            out.append(TANWEEN[ch])
        elif ch == DAGGER:
            out.append("a")
        elif ch == SHADDA:
            # NFC에서는 모음 기호가 샷다보다 앞에 온다. 겹자음은 자음 바로 뒤에 넣는다.
            if last_cons_idx >= 0:
                out.insert(last_cons_idx + 1, last_cons)
                last_cons_idx += 1
        elif ch == SUKUN:
            continue
        elif ch == "ا":
            out.append("" if i == 0 and nxt in VOWEL_MARKS else "a")
        elif ch == "آ":
            out.append("aa")
        elif ch == "أ":
            out.append("" if i == 0 else "'")
        elif ch == "إ":
            out.append("" if nxt == KASRA else "i")
        elif ch == "و":
            if nxt in VOWEL_MARKS or i == 0:
                cons("w")
            else:
                out.append("u" if prev.endswith("u") else "w")
        elif ch == "ي":
            if nxt in VOWEL_MARKS or i == 0:
                cons("y")
            else:
                out.append("i" if prev.endswith("i") else "y")
        elif ch == "ى":
            out.append("a")
        elif ch == "ة":
            if nxt in VOWEL_MARKS:
                cons("t")
            else:
                out.append("" if prev.endswith("a") else "a")
        elif ch in CONSONANTS:
            cons(CONSONANTS[ch])
    return prefix + "".join(out)


def romanize(diac: str) -> str:
    """모음 표기된 아랍어 → 소문자 ASCII 로마자. 예: مُسَلَّم → musallam."""
    return " ".join(_romanize_word(w) for w in nfc(diac).split())


def romanize_display(diac: str) -> str:
    """보여 주기용. 예: النُعَيْمِيّ → Al-Nu'aymiyy."""
    words = []
    for w in re.sub(r"([aiu])\1", r"\1", romanize(diac)).split():
        if w.startswith("al-"):
            words.append("Al-" + w[3:].capitalize())
        else:
            words.append(w.capitalize())
    return " ".join(words)


ARTICLES = {"al", "el", "ul", "aal"}
VOWELS = set("aiu")
# 영문 표기에만 나오는 모음 글자(아랍어 로마자는 a·i·u만 쓴다). 첫 값이 대표형이다
EN_VOWELS = {"E": ("i", "a", "u"), "O": ("u", "aw")}  # Rashed·Ahmed·Yousef, Omar·Nofal
MAX_VARIANTS = 256
MIN_TOLERANT_LEN = 4
SEMIVOWEL_SUBS = {frozenset("yi"), frozenset("wu")}


def _abd(word: str) -> str:
    """붙여 쓴 Abdul·Abdel·Abdur 등을 abd로 줄인다. 아랍어 로마자는 'abd al-X로 단어가 나뉘어 해당하지 않는다."""
    if not word.startswith("abd") or len(word) <= 3:
        return word
    rest = re.sub(r"^(?:ou|oo|[aeiou])l", "", word[3:], count=1)
    if rest == word[3:]:  # 태양 문자 동화: Abdur Rahman, Abdurrahman
        rest = re.sub(r"^[aeiou](?=sh|th|dh|[rsntdz])", "", rest, count=1)
    return "abd" + rest


def _base(spelling: str) -> str:
    # 함자·아인(')은 지운다. 영문은 Zaabi·Saad처럼 아인 양옆 모음을 aa로 쓰는 일이 많다
    s = re.sub(r"[’'`ʿʾ.]", "", spelling.lower())
    words = [w for w in re.split(r"[\s\-]+", s) if w and w not in ARTICLES]
    out: list[str] = []
    for w in words:
        w = _abd(w)
        if out and out[-1] == "abd" and re.match(r"(?:al|el|ul)..", w):  # Abd Elrahman
            w = w[2:]
        out.append(w)
    s = "".join(out)
    return s.replace("ee", "i").replace("oo", "u").replace("ou", "O").replace("o", "O").replace("e", "E")


def _expand(s: str) -> list[str]:
    """E·O 자리마다 가능한 모음을 넣은 변형들. 첫 변형이 대표형이다."""
    out = [""]
    for ch in s:
        choices = EN_VOWELS.get(ch, (ch,))
        out = [o + c for o in out for c in choices][:MAX_VARIANTS]
    return out


def _fold(s: str) -> str:
    s = s.replace("dh", "d").replace("th", "d").replace("z", "d")  # ث·ذ·ظ·ض·ز의 영문 표기(th·dh·z·d)를 한 부류로
    s = re.sub(r"(.)\1+", r"\1", s)  # 겹자음·장모음(Sayyah·Sayah)을 먼저 접고 이중모음을 맞춘다
    s = re.sub(r"iy+$", "i", s.replace("ay", "ai"))
    s = re.sub(r"ah$", "a", s)  # 타 마르부타의 영문 표기(Lujainah·Lujaina, Hamadeh)
    return re.sub(r"(.)\1+", r"\1", s)


def _with_q(forms: list[str], dialect: bool) -> list[str]:
    out = list(forms)
    for v in forms:
        out.append(v.replace("q", "k"))  # Tariq·Tarek, Qasim·Kassim
        if dialect:  # 걸프 방언에서 ق를 g로 읽는 표기(예: Gurg)
            out.append(v.replace("q", "g"))
    return list(dict.fromkeys(out))


@lru_cache(maxsize=65536)
def _variants(spelling: str, dialect: bool) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(전체 정규형, 대표형). 대표형은 e→i, o→u로만 펼친 것이고 한 글자 허용은 대표형끼리만 쓴다."""
    base = _base(spelling)
    if not base:
        return (), ()
    bases = [base]
    if base.startswith("al") and len(base) > 5:  # AlQubaisi처럼 붙여 쓴 관사
        bases.append(base[2:])
    expanded = [_expand(b) for b in bases]
    full = _with_q([_fold(v) for vs in expanded for v in vs], dialect)
    core = _with_q([_fold(vs[0]) for vs in expanded], dialect)
    return tuple(full), tuple(core)


def normalize_latin(spelling: str, dialect: bool = False) -> set[str]:
    """비교용 정규형 집합. 관사·하이픈·Abdul 붙임을 걷고, 영문 모음 e·o는 가능한 아랍어 모음으로 펼친다."""
    return set(_variants(spelling, dialect)[0])


def canonical_latin(spelling: str) -> str:
    """대표 정규형 하나(e→i, o→u). 같은 이름을 같은 값으로 묶을 때 쓴다."""
    core = _variants(spelling, False)[1]
    return core[0] if core else ""


def _one_edit_ok(x: str, y: str) -> bool:
    """모음(a·i·u)은 그대로 두고 자음 하나를 더하거나 빼거나, y↔i·w↔u 하나만 바꾼 차이인지."""
    if abs(len(x) - len(y)) > 1 or min(len(x), len(y)) < MIN_TOLERANT_LEN:
        return False
    if len(x) == len(y):
        diffs = [frozenset(p) for p in zip(x, y, strict=True) if p[0] != p[1]]
        return len(diffs) == 1 and diffs[0] in SEMIVOWEL_SUBS
    short, long_ = sorted((x, y), key=len)
    return any(long_[i] not in VOWELS and long_[:i] + long_[i + 1 :] == short for i in range(len(long_)))


def match_spelling(a: str, b: str, dialect: bool = False) -> bool:
    """두 표기가 같은 독법의 표기 변이인지. 정규형이 같거나 자음 쪽 한 글자 차이만 허용한다.

    모음이 다르면(Harab·Harib, Hamad·Hamd, Muslim·Musallam) 다른 독법이다. v0의 편집 거리 1은 이런 쌍을 같다고 봤다.
    """
    (xs, xcore), (ys, ycore) = _variants(a, dialect), _variants(b, dialect)
    if set(xs) & set(ys):
        return True
    # 펼친 변형(o→aw 등)에 한 글자 허용을 겹치면 모음이 바뀐다(Obadah가 'Abbadah와 맞음)
    return any(_one_edit_ok(x, y) for x in xcore for y in ycore)


def spelling_in_text(spelling: str, text: str, dialect: bool = False) -> bool:
    """text 안에 spelling과 일치하는 연속 단어열이 있는지."""
    words = re.findall(r"[A-Za-z][A-Za-z'’\-]*", text)
    max_n = max(1, len(spelling.split()) + 2)
    for n in range(1, max_n + 1):
        for i in range(len(words) - n + 1):
            if match_spelling(spelling, " ".join(words[i : i + n]), dialect):
                return True
    return False
