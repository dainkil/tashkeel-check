"""입력 정규화, 구간 분할, 토큰 ID 부여.

원문은 바꾸지 않는다. 비교용 키(normalize_key)는 사본에서만 만든다.
"""

from __future__ import annotations

import re
import unicodedata
from typing import TypedDict

AR_LETTERS = "ء-غف-يٱ-ۓۺ-ۿ"
AR_MARKS = "ً-ٰٟ"
TATWEEL = "ـ"

TOKEN_RE = re.compile(
    rf"(?P<ar>[{AR_LETTERS}][{AR_LETTERS}{AR_MARKS}{TATWEEL}]*)"
    r"|(?P<latin>[A-Za-z](?:[A-Za-z'’.\-]*[A-Za-z])?)"
    r"|(?P<num>[0-9٠-٩]+(?:[/\-.][0-9٠-٩]+)*)"
)
MARKS_RE = re.compile(rf"[{AR_MARKS}{TATWEEL}]")
ALEF_RE = re.compile("[آأإٱ]")
LATIN_RE = re.compile(r"[A-Za-z]")


class Segment(TypedDict):
    segment_id: str
    text: str


class Token(TypedDict):
    id: int
    segment_id: str
    text: str
    start: int  # 구간 텍스트 안의 문자 위치
    end: int
    script: str  # "ar" | "latin" | "num"


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def dediac(text: str) -> str:
    return MARKS_RE.sub("", text)


def normalize_key(text: str) -> str:
    """같은 이름인지 묶을 때 쓰는 키. 모음 기호·타트윌 제거, 알리프·타 마르부타·알리프 막수라 통일."""
    s = dediac(nfc(text))
    s = ALEF_RE.sub("ا", s)
    s = s.replace("ة", "ه").replace("ى", "ي")
    return " ".join(s.split())


def has_latin(text: str) -> bool:
    return bool(LATIN_RE.search(text))


def segment_text(text: str) -> list[Segment]:
    """빈 줄이 아닌 줄을 한 구간으로 본다."""
    lines = [line.strip() for line in nfc(text).splitlines()]
    return [Segment(segment_id=f"s{i:02d}", text=line) for i, line in enumerate((ln for ln in lines if ln), start=1)]


def tokenize(segments: list[Segment]) -> list[Token]:
    tokens: list[Token] = []
    for seg in segments:
        for m in TOKEN_RE.finditer(seg["text"]):
            tokens.append(
                Token(
                    id=len(tokens),
                    segment_id=seg["segment_id"],
                    text=m.group(0),
                    start=m.start(),
                    end=m.end(),
                    script=m.lastgroup or "ar",
                )
            )
    return tokens


def tokens_in_span(tokens: list[Token], segment_id: str, start: int, end: int) -> list[int]:
    return [t["id"] for t in tokens if t["segment_id"] == segment_id and t["start"] >= start and t["end"] <= end]


def render_plain(segments: list[Segment]) -> str:
    return "\n".join(f"[{s['segment_id']}] {s['text']}" for s in segments)


def render_token_table(segments: list[Segment], tokens: list[Token]) -> str:
    """LLM이 아랍어를 다시 쓰지 않고 ID로 지목하도록 아랍어 토큰 표를 만든다."""
    lines = []
    for seg in segments:
        ids = [f"{t['id']}={t['text']}" for t in tokens if t["segment_id"] == seg["segment_id"] and t["script"] == "ar"]
        if ids:
            lines.append(f"{seg['segment_id']}: " + "  ".join(ids))
    return "\n".join(lines)
