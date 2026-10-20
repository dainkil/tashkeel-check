"""조건별 프롬프트. C1을 기준으로 C2는 도구 안내 한 줄, C3는 분석기 결과 블록만 더한다.

정답 라벨(gold)은 여기 들어오지 않는다. 입력은 구간과 토큰뿐이다.
"""

from __future__ import annotations

import hashlib
import json

from .analyzer import TokenAnalysis, view_for_llm
from .errors import InputError
from .text import Segment, Token, render_plain, render_token_table

PROMPT_VERSION = "p0"

C0_SYSTEM = (
    "You are a translator. Translate the Arabic document into English. "
    "Write one line per segment and start each line with its segment label in square brackets, e.g. [s01] ..."
)

C1_SYSTEM = """You translate an Arabic document into English for a reader who cannot read Arabic but is responsible for the document.
Arabic omits short vowels, so one spelling can have several readings. Besides translating, expose every place where you had to choose.

Rules:
1. Translate every segment.
2. For every span whose reading or meaning could go more than one way, add an item of type "word". List the candidate readings, then either adopt one (decision "adopt", with a reason and a confidence from 0 to 1) or abstain (decision "abstain").
3. Add an item of type "proper_noun" for every personal name, family name and company name. Well-known place names may be translated directly. List romanization candidates for each proper noun.
4. You may settle a proper noun's spelling only with evidence: a Latin-script spelling of that same name inside this document. Then use decision "evidence_adopt" and put the segment_id and the exact Latin text in "evidence". Without such evidence use decision "hold". How common a spelling is does not count as evidence.
5. In the translation text, write a held name as its candidate spellings in brackets separated by "/", e.g. [Musallam/Muslim].
6. Refer to Arabic text only by token ids from the TOKENS table. Never rewrite Arabic in token_ids."""

C2_TOOL_LINE = (
    "\n7. You have a tool, analyze_tokens, that returns candidate readings for token ids from an independent "
    "morphological analyzer. Use it whenever it helps."
)

C3_ANALYZER_LINE = (
    "\n7. The ANALYZER block lists results from an independent morphological analyzer for this document. "
    "'ambiguous' tokens have two or more distinct readings. Tokens with analysis_count 0 are unknown to the analyzer, which often means a name."
)


def system_prompt(condition: str) -> str:
    if condition == "C0":
        return C0_SYSTEM
    if condition == "C1":
        return C1_SYSTEM
    if condition == "C2":
        return C1_SYSTEM + C2_TOOL_LINE
    if condition == "C3":
        return C1_SYSTEM + C3_ANALYZER_LINE
    raise InputError(f"unknown condition {condition!r}")


def analyzer_block(analyses: dict[int, TokenAnalysis], max_candidates: int) -> str:
    """C3용. 모호 토큰과 분석 0개 토큰만 싣는다. 나머지는 후보가 하나뿐이라 개수만 알린다."""
    rows = [view_for_llm(a, max_candidates) for a in analyses.values() if a["ambiguous"] or a["analysis_count"] == 0]
    others = len(analyses) - len(rows)
    return (
        "ANALYZER\n"
        + "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
        + (f"\n({others} other tokens have exactly one reading)" if others else "")
    )


def user_message(
    condition: str,
    doc_id: str,
    segments: list[Segment],
    tokens: list[Token],
    analyses: dict[int, TokenAnalysis] | None = None,
    max_candidates: int = 10,
) -> str:
    if condition == "C0":
        return render_plain(segments)
    parts = [f"DOCUMENT {doc_id}", render_plain(segments), "TOKENS", render_token_table(segments, tokens)]
    if condition == "C3":
        parts.append(analyzer_block(analyses or {}, max_candidates))
    return "\n\n".join(parts)


def prompt_hash(condition: str) -> str:
    return hashlib.sha256(f"{PROMPT_VERSION}\n{system_prompt(condition)}".encode()).hexdigest()[:16]
