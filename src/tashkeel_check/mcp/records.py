"""회사 기록 MCP 서버와 그 툴(ADR-022, 조건 M2).

서버 툴 `search_company_records`는 한 고객의 회사 사전(사람이 확정한 표기)과 문서 보관함(전에 올린 서류의 구절)을
찾는다. 서비스는 Runtime의 사전·보관함을 그대로 쓰는 서버를 하나 만들어 같은 프로세스의 메모리 전송으로 붙인다.

고객 범위는 도구 인자로 받지 않는다. 작업마다 발급하고 끝나면 없애는 범위 토큰(`ScopeRegistry`)을 MCP 요청의
`_meta`로 받고, 토큰이 없거나 모르는 값이면 거부한다. 쓰기·확정 도구는 두지 않는다(사전 등록은 사람만, ADR-010).

LLM이 보는 툴은 토큰 ID 묶음만 받는다. 아랍어 이름과 주변 문맥은 래퍼가 토큰 표에서 만든다(아랍어를 다시 쓰지 않게).
"""

from __future__ import annotations

import secrets
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.client.transports import FastMCPTransport
from fastmcp.exceptions import ToolError
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel

from ..archive.search import MAX_NAMES, CompanyArchive, search_records
from ..bundle.dictionary import DictionaryLookup
from ..dictionary_apply import collapse_repeats
from ..errors import ConfigError
from ..text import Segment, Token
from .client import MCPClient

RECORDS_TOOL = "search_company_records"
CONTEXT_CHARS = 400

RECORDS_TOOL_DOC = (
    "Look up the client's own records for proper nouns. Pass one group of token ids per name. "
    "For each name the result has either a spelling that a person at the client already confirmed (dictionary), "
    "or passages (hits) from the client's earlier documents that contain the same Arabic spelling, each with a hit_id "
    "and the Latin-script text near it. The same spelling can belong to a different person, company or agency. "
    "Records are never evidence for this document."
)


@dataclass(frozen=True)
class RecordsScope:
    customer_id: str
    document_id: str | None  # 이번 서류. 보관함 결과에서 뺀다
    sha256: str | None  # 같은 파일을 다시 올린 경우도 뺀다


class ScopeRegistry:
    """작업별 범위 토큰. 128비트 무작위 값이고 프로세스 메모리에만 있다."""

    def __init__(self) -> None:
        self._scopes: dict[str, RecordsScope] = {}
        self._lock = threading.Lock()

    def issue(self, customer_id: str, document_id: str | None, sha256: str | None) -> str:
        token = secrets.token_hex(16)
        with self._lock:
            self._scopes[token] = RecordsScope(customer_id, document_id, sha256)
        return token

    def resolve(self, token: Any) -> RecordsScope | None:
        if not isinstance(token, str):
            return None
        with self._lock:
            return self._scopes.get(token)

    def revoke(self, token: str | None) -> None:
        if token is None:
            return
        with self._lock:
            self._scopes.pop(token, None)

    def __len__(self) -> int:
        return len(self._scopes)


class NameQuery(BaseModel):
    token_ids: list[int]
    arabic: str
    context: str = ""


def build_records_server(
    archive: CompanyArchive, dictionary: DictionaryLookup | None, scopes: ScopeRegistry
) -> FastMCP:
    mcp = FastMCP("tashkeel-records", instructions="Read-only lookup of one client's confirmed names and archive.")

    @mcp.tool(name=RECORDS_TOOL, description=RECORDS_TOOL_DOC)
    def search_company_records(names: list[NameQuery], ctx: Context) -> list[dict]:
        meta = getattr(ctx.request_context, "meta", None) or {}
        scope = scopes.resolve(dict(meta).get("scope"))
        if scope is None:
            raise ToolError("records scope token is missing, unknown or revoked")
        queries = [n.model_dump() for n in names]
        return search_records(archive, dictionary, scope.customer_id, queries, scope.document_id, scope.sha256)

    return mcp


def start_records_client(server: FastMCP) -> MCPClient:
    client = MCPClient.from_transport(FastMCPTransport(server))
    client.start()  # 실패 → ConfigError
    return client


@dataclass
class RecordsContext:
    """툴 하나를 만드는 데 필요한 것. 역할(번역·검증)마다 따로 만들어 툴 기록이 섞이지 않게 한다."""

    tokens: list[Token]
    segments: list[Segment]
    scope: str | None
    role: str
    log: list[dict] = field(default_factory=list)


RecordsToolFactory = Callable[[RecordsContext], BaseTool]


def _context(segments: list[Segment], segment_id: str) -> str:
    idx = next((i for i, s in enumerate(segments) if s["segment_id"] == segment_id), None)
    if idx is None:
        return ""
    lo, hi = max(0, idx - 1), min(len(segments), idx + 2)
    return " ".join(s["text"] for s in segments[lo:hi])[:CONTEXT_CHARS]


def name_queries(tokens: list[Token], segments: list[Segment], names: list[list[int]]) -> list[dict]:
    by_id = {t["id"]: t for t in tokens}
    out = []
    for ids in names[:MAX_NAMES]:
        ar = [by_id[i] for i in ids if isinstance(i, int) and i in by_id and by_id[i]["script"] == "ar"]
        if not ar:
            continue
        out.append(
            {
                "token_ids": [t["id"] for t in ar],
                "arabic": collapse_repeats(" ".join(t["text"] for t in ar)),
                "context": _context(segments, ar[0]["segment_id"]),
            }
        )
    return out


def make_records_tool_factory(client: MCPClient) -> RecordsToolFactory:
    def factory(ctx: RecordsContext) -> BaseTool:
        @tool(RECORDS_TOOL, description=RECORDS_TOOL_DOC)
        def search_company_records(names: list[list[int]]) -> list[dict]:
            queries = name_queries(ctx.tokens, ctx.segments, names)
            entry: dict[str, Any] = {"tool": RECORDS_TOOL, "role": ctx.role, "names": len(queries), "via": "mcp"}
            rows: list[dict] = []
            if queries and ctx.scope is not None:
                try:
                    rows = list(client.call_tool(RECORDS_TOOL, {"names": queries}, meta={"scope": ctx.scope}) or [])
                except ConfigError:
                    raise  # 서버가 죽었다. 작업 실패로 기록된다
                except Exception as exc:  # 범위 거부 등 툴 오류는 LLM에게 알리고 계속한다
                    entry["error"] = f"{type(exc).__name__}: {exc}"
                    ctx.log.append(entry)
                    return [{"error": "records lookup failed"}]
            entry["dictionary"] = sum(1 for r in rows if r.get("dictionary"))
            entry["hit_ids"] = [h["hit_id"] for r in rows for h in r.get("hits", [])]
            ctx.log.append(entry)
            return rows

        return search_company_records

    return factory
