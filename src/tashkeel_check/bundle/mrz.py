"""여권 기계판독영역(MRZ, TD3 첫 줄)에서 영문 이름을 읽는다.

`P<SAUAL<QAHTANI<<FATMA<AHMED<<<…`(44자)에서 성은 `<<` 앞, 이름은 뒤다. 낱말 사이는 `<`다.
돌려주는 표기는 "이름 성" 순서의 대문자다(`FATMA AHMED AL QAHTANI`). 확정 비교는 대소문자를 무시하므로
서류 영문 칸(`Fatma Ahmed Al Qahtani`)과 정확 일치로 맞는다. 검사 숫자는 보지 않는다(둘째 줄은 쓰지 않는다).
"""

from __future__ import annotations

import re

MRZ_LINE1_RE = re.compile(r"^P[A-Z<][A-Z]{3}[A-Z<]{39}$")


def is_mrz_line(text: str) -> bool:
    return MRZ_LINE1_RE.match(text.strip()) is not None


def mrz_name(text: str) -> str | None:
    """MRZ 첫 줄이면 "이름 성"을, 아니면 None을 돌려준다."""
    line = text.strip()
    if not is_mrz_line(line):
        return None
    surname, _, given = line[5:].partition("<<")
    parts = [" ".join(p.replace("<", " ").split()) for p in (given, surname)]
    return " ".join(p for p in parts if p) or None


def mrz_line1(surname: str, given_names: str, country: str = "SAU") -> str:
    """합성 여권용 MRZ 첫 줄. 이름에서 영문자 이외는 `<`로 바꾸고 44자로 채운다."""

    def enc(s: str) -> str:
        return re.sub(r"[^A-Z]", "<", s.upper().strip())

    body = f"{enc(surname)}<<{enc(given_names)}"
    return (f"P<{country.upper()[:3]}{body}" + "<" * 44)[:44]
