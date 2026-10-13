"""LLM이 호출하는 툴. 단계 1에는 analyze_tokens 하나뿐이다(C2에서만 묶는다).

툴은 analyze 노드가 이미 계산한 결과를 돌려준다. 그래서 조건과 무관하게 분석 결과가 같고,
C2에서 달라지는 것은 LLM이 무엇을 조회했는가뿐이다.
"""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool

from .analyzer import TokenAnalysis, view_for_llm
from .text import Token


def make_analyze_tool(
    tokens: list[Token],
    analyses: dict[int, TokenAnalysis],
    log: list[dict],
    max_candidates: int,
) -> BaseTool:
    by_id = {t["id"]: t for t in tokens}

    @tool("analyze_tokens")
    def analyze_tokens(token_ids: list[int]) -> list[dict]:
        """Return candidate readings for Arabic token ids from an independent morphological analyzer (CAMeL Tools).

        Each result has analysis_count (0 means the analyzer does not know the word, often a name),
        ambiguous (two or more distinct readings) and candidates with reading, romanized, pos and gloss.
        """
        results: list[dict] = []
        errors = 0
        for tid in token_ids:
            if tid not in by_id:
                results.append({"token_id": tid, "error": "unknown token id"})
                errors += 1
            elif tid not in analyses:
                results.append({"token_id": tid, "error": "not an Arabic token"})
                errors += 1
            else:
                results.append(view_for_llm(analyses[tid], max_candidates))
        log.append({"tool": "analyze_tokens", "token_ids": list(token_ids), "errors": errors})
        return results

    return analyze_tokens
