"""모음 표기된 아랍어를 ASCII 로마자로 옮기고, 영문 표기끼리 같은 이름인지 판정한다.

규칙 버전은 MATCHER_VERSION으로 기록한다. v0는 EXP-001 개발용 표본에서 고친 뒤 고정할 초안이다.
모음을 살려 비교한다. 자음만 비교하면 Muslim과 Musallam이 같아진다.
"""

from __future__ import annotations

import re

from .text import dediac, nfc

MATCHER_VERSION = "v0"

FATHA, DAMMA, KASRA, SUKUN, SHADDA, DAGGER = "َ", "ُ", "ِ", "ْ", "ّ", "ٰ"
TANWEEN = {"ً": "an", "ٌ": "un", "ٍ": "in"}
VOWEL_MARKS = {FATHA, DAMMA, KASRA, SHADDA, *TANWEEN}
CONSONANTS = {
    "ب": "b", "ت": "t", "ث": "th", "ج": "j", "ح": "h", "خ": "kh", "د": "d", "ذ": "dh",
    "ر": "r", "ز": "z", "س": "s", "ش": "sh", "ص": "s", "ض": "d", "ط": "t", "ظ": "z",
    "ع": "'", "غ": "gh", "ف": "f", "ق": "q", "ك": "k", "ل": "l", "م": "m", "ن": "n",
    "ه": "h", "ء": "'", "ؤ": "'", "ئ": "'",
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


_FOLDS = [("ou", "u"), ("oo", "u"), ("ee", "i"), ("ei", "i"), ("ay", "ai"), ("ey", "ai"), ("e", "i"), ("o", "u")]


def _fold(s: str) -> str:
    for a, b in _FOLDS:
        s = s.replace(a, b)
    s = re.sub(r"iy+$", "i", s)
    return re.sub(r"(.)\1+", r"\1", s)


def normalize_latin(spelling: str, dialect: bool = False) -> set[str]:
    """비교용 정규형 집합. 관사(Al/El)·하이픈·아포스트로피를 걷고 모음 표기 차이를 접는다."""
    s = re.sub(r"[’'`ʿʾ.]", "", spelling.lower())
    words = [w for w in re.split(r"[\s\-]+", s) if w and w not in ("al", "el", "ul")]
    joined = "".join(words)
    if not joined:
        return set()
    variants = {_fold(joined)}
    if joined.startswith("al") and len(joined) > 5:  # AlQubaisi처럼 붙여 쓴 관사
        variants.add(_fold(joined[2:]))
    if dialect:  # 걸프 방언에서 ق를 g로 읽는 표기(예: Gurg)
        variants |= {v.replace("q", "g") for v in variants}
    return variants


def _levenshtein(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def match_spelling(a: str, b: str, dialect: bool = False) -> bool:
    """두 표기가 같은 이름의 표기 변이인지. 정규형이 같거나, 5자 이상에서 편집 거리 1 이하."""
    for x in normalize_latin(a, dialect):
        for y in normalize_latin(b, dialect):
            if x == y:
                return True
            if min(len(x), len(y)) >= 5 and _levenshtein(x, y) <= 1:
                return True
    return False


def spelling_in_text(spelling: str, text: str, dialect: bool = False) -> bool:
    """text 안에 spelling과 일치하는 연속 단어열이 있는지."""
    words = re.findall(r"[A-Za-z][A-Za-z'’\-]*", text)
    max_n = max(1, len(spelling.split()) + 2)
    for n in range(1, max_n + 1):
        for i in range(len(words) - n + 1):
            if match_spelling(spelling, " ".join(words[i : i + n]), dialect):
                return True
    return False
