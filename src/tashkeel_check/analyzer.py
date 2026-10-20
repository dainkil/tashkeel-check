"""CAMeL Tools 형태소 분석기 래퍼. LLM과 독립된 독법 후보 신호.

분석기를 쓸 수 없으면 AnalyzerUnavailable을 낸다. LLM이나 다른 방법으로 대신 채우지 않는다(ADR-004).
"""

from __future__ import annotations

import unicodedata
from collections.abc import Callable
from functools import lru_cache
from typing import TYPE_CHECKING, TypedDict

from .romanize import romanize, romanize_display
from .text import Token, dediac

if TYPE_CHECKING:
    from camel_tools.morphology.analyzer import Analyzer

DB_NAME = "calima-msa-r13"
CASE_MARKS = {"ً", "ٌ", "ٍ", "َ", "ُ", "ِ", "ْ"}  # 탄윈 3종, 파트하, 담마, 카스라, 수쿤
FATHATAN = "ً"


class AnalyzerUnavailable(RuntimeError):
    pass


class Candidate(TypedDict):
    diac: str  # 격어미·탄윈을 뺀 모음 표기
    romanized: str
    display: str
    lemmas: list[str]
    pos: list[str]
    gloss: str


class TokenAnalysis(TypedDict):
    token_id: int
    surface: str
    analysis_count: int  # 원시 분석 수(0 포함)
    raw_distinct_diac: int  # 격어미를 빼기 전 서로 다른 모음 표기 수
    candidates: list[Candidate]  # 격어미를 뺀 표기 기준으로 묶은 후보
    ambiguous: bool  # 묶은 후보가 둘 이상
    has_noun_prop: bool


def _is_mark(ch: str) -> bool:
    return unicodedata.category(ch) == "Mn"


def strip_case_ending(diac: str) -> str:
    """끝 글자의 격어미·탄윈·수쿤을 뗀다. 샷다는 남긴다. 목적격 비한정의 알리프(ـًا)도 뗀다."""
    s = unicodedata.normalize("NFC", diac)
    if s.endswith(FATHATAN + "ا"):
        s = s[:-2]
    i = len(s)
    while i > 0 and _is_mark(s[i - 1]):
        i -= 1
    base, marks = s[:i], s[i:]
    removed_fathatan = FATHATAN in marks
    kept = "".join(m for m in marks if m not in CASE_MARKS)
    if removed_fathatan and base.endswith("ا") and len(dediac(base)) > 1:
        base = base[:-1]
    return base + kept


@lru_cache(maxsize=1)
def _camel_analyzer() -> Analyzer:
    try:
        from camel_tools.morphology.analyzer import Analyzer
        from camel_tools.morphology.database import MorphologyDB

        return Analyzer(MorphologyDB.builtin_db())
    except Exception as exc:  # 설치·데이터 누락 모두 여기로 온다
        raise AnalyzerUnavailable(
            "CAMeL Tools 분석기를 불러오지 못했습니다. `uv run camel_data -i morphology-db-msa-r13`로 "
            f"DB를 설치했는지 확인하세요. 원인: {exc!r}"
        ) from exc


def camel_analyze(surface: str) -> list[dict]:
    return _camel_analyzer().analyze(surface)


def analyzer_version() -> dict:
    try:
        import camel_tools

        version = getattr(camel_tools, "__version__", None)
        if version is None:
            from importlib.metadata import version as _v

            version = _v("camel-tools")
    except Exception:
        version = None
    return {"tool": "camel-tools", "version": version, "db": DB_NAME, "backoff": "NONE"}


def summarize(token_id: int, surface: str, analyses: list[dict]) -> TokenAnalysis:
    groups: dict[str, list[dict]] = {}
    for a in analyses:
        groups.setdefault(strip_case_ending(a.get("diac", "")), []).append(a)
    candidates: list[Candidate] = []
    for form, members in groups.items():
        candidates.append(
            Candidate(
                diac=form,
                romanized=romanize(form),
                display=romanize_display(form),
                lemmas=sorted({dediac(m.get("lex", "")) for m in members if m.get("lex")}),
                pos=sorted({m.get("pos", "") for m in members if m.get("pos")}),
                gloss=next((m.get("gloss", "") for m in members if m.get("gloss")), ""),
            )
        )
    return TokenAnalysis(
        token_id=token_id,
        surface=surface,
        analysis_count=len(analyses),
        raw_distinct_diac=len({a.get("diac", "") for a in analyses}),
        candidates=candidates,
        ambiguous=len(candidates) >= 2,
        has_noun_prop=any(a.get("pos") == "noun_prop" for a in analyses),
    )


AnalyzeFn = Callable[[str], list[dict]]


def analyze_tokens(tokens: list[Token], analyze_fn: AnalyzeFn | None = None) -> dict[int, TokenAnalysis]:
    """아랍어 토큰을 모두 분석한다. analyze_fn은 테스트에서 분석기를 바꿔 끼울 때만 쓴다."""
    fn = analyze_fn or camel_analyze
    cache: dict[str, list[dict]] = {}
    out: dict[int, TokenAnalysis] = {}
    for t in tokens:
        if t["script"] != "ar":
            continue
        surface = dediac(t["text"])
        if surface not in cache:
            cache[surface] = fn(surface)
        out[t["id"]] = summarize(t["id"], t["text"], cache[surface])
    return out


def view_for_llm(a: TokenAnalysis, max_candidates: int) -> dict:
    """LLM에게 보여 줄 축약형. 후보 수가 상한을 넘으면 잘린 개수를 같이 알린다."""
    cands = a["candidates"][:max_candidates]
    return {
        "token_id": a["token_id"],
        "surface": a["surface"],
        "analysis_count": a["analysis_count"],
        "ambiguous": a["ambiguous"],
        "candidates": [
            {"reading": c["diac"], "romanized": c["display"], "pos": c["pos"], "gloss": c["gloss"]} for c in cands
        ],
        "candidates_truncated": max(0, len(a["candidates"]) - max_candidates),
    }
