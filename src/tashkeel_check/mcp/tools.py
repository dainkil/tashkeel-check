"""MCP 서버의 analyze_tokens를 그래프의 C2 툴로 감싼다(USE_MCP_TOOLS=true일 때 서비스 경로에서만).

LLM이 보는 툴 이름·인자·설명은 in-process 툴(tools.make_analyze_tool)과 같다. 다른 것은 분석이 어디서 도는가뿐이고,
툴 로그에 `via: "mcp"`를 남긴다. 서버가 죽으면 ConfigError가 나고 클라이언트의 healthy가 꺼진다(작업 실패로 기록).
"""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool

from ..analyzer import TokenAnalysis
from ..graph import AnalyzeToolFactory
from ..text import Token
from .client import MCPClient

# tools.make_analyze_tool의 설명과 글자 단위로 같아야 한다(LLM 입력 동일, tests/test_mcp.py가 확인).
ANALYZE_TOOL_DOC = (
    "Return candidate readings for Arabic token ids from an independent morphological analyzer (CAMeL Tools).\n"
    "\n"
    "        Each result has analysis_count (0 means the analyzer does not know the word, often a name),\n"
    "        ambiguous (two or more distinct readings) and candidates with reading, romanized, pos and gloss.\n"
    "        "
)


def make_mcp_analyze_tool_factory(client: MCPClient) -> AnalyzeToolFactory:
    def factory(
        tokens: list[Token], analyses: dict[int, TokenAnalysis], log: list[dict], max_candidates: int
    ) -> BaseTool:
        payload = [{"id": t["id"], "text": t["text"], "script": t["script"]} for t in tokens]

        @tool("analyze_tokens", description=ANALYZE_TOOL_DOC.strip())
        def analyze_tokens(token_ids: list[int]) -> list[dict]:
            results = client.call_tool(
                "analyze_tokens", {"tokens": payload, "token_ids": list(token_ids), "max_candidates": max_candidates}
            )
            rows: list[dict] = list(results or [])
            errors = sum(1 for r in rows if "error" in r)
            log.append({"tool": "analyze_tokens", "token_ids": list(token_ids), "errors": errors, "via": "mcp"})
            return rows

        return analyze_tokens

    return factory
