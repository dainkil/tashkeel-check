"""MCP 서버에 한 번 연결해 재사용하는 동기 클라이언트. stdio 서버(분석기) 또는 메모리 전송(회사 기록 서버, ADR-022).

그래프 노드가 동기라 전용 스레드의 이벤트 루프 위에서 fastmcp.Client를 돌리고, 호출은 잠금으로 하나씩 보낸다.
일시 오류(타임아웃)만 지수 백오프로 재시도하고, 서버가 죽으면 ConfigError를 낸다. in-process로 대체하지 않는다.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import contextlib
import json
import os
import sys
import threading
import time
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from fastmcp import Client
from fastmcp.client.transports import ClientTransport, StdioTransport
from mcp.types import CONNECTION_CLOSED

from ..errors import ConfigError

T = TypeVar("T")

_TIMEOUT_ERRORS: tuple[type[BaseException], ...] = (TimeoutError, asyncio.TimeoutError, concurrent.futures.TimeoutError)


def with_retry(fn: Callable[[], T], retries: int = 3, base_delay: float = 0.3) -> tuple[T, int]:
    """타임아웃만 재시도한다(지수 백오프). 다른 오류는 그대로 올린다. (결과, 재시도 횟수)를 돌려준다."""
    attempt = 0
    while True:
        attempt += 1
        try:
            return fn(), attempt - 1
        except _TIMEOUT_ERRORS:
            if attempt >= retries:
                raise
            time.sleep(base_delay * (3 ** (attempt - 1)))


def default_server_command(data_dir: str | os.PathLike[str] | None = None) -> tuple[str, list[str], dict[str, str]]:
    """같은 인터프리터로 `python -m tashkeel_check.mcp.server`를 띄운다."""
    env = {**os.environ, "FASTMCP_LOG_LEVEL": "ERROR"}
    if data_dir is not None:
        env["DATA_DIR"] = str(data_dir)
    return sys.executable, ["-m", "tashkeel_check.mcp.server"], env


class MCPClient:
    def __init__(
        self,
        command: str,
        args: list[str],
        env: dict[str, str] | None = None,
        timeout: float = 60.0,
        retries: int = 3,
        base_delay: float = 0.3,
    ) -> None:
        self._init(StdioTransport(command=command, args=args, env=env), timeout, retries, base_delay)

    @classmethod
    def from_transport(
        cls, transport: ClientTransport, timeout: float = 60.0, retries: int = 3, base_delay: float = 0.3
    ) -> MCPClient:
        """이미 만든 전송으로 연결한다. 서비스는 회사 기록 서버를 같은 프로세스의 FastMCPTransport로 붙인다."""
        client = cls.__new__(cls)
        client._init(transport, timeout, retries, base_delay)
        return client

    def _init(self, transport: ClientTransport, timeout: float, retries: int, base_delay: float) -> None:
        self._transport = transport
        self._timeout = timeout
        self._retries = retries
        self._base_delay = base_delay
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._client: Client | None = None
        self.healthy = False
        self.last_error: str | None = None
        self.retry_count = 0
        self.calls = 0  # call_tool 횟수(서비스가 작업별 MCP 호출 수를 셀 때 쓴다)

    # -- 수명 --
    def start(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        self._thread = threading.Thread(target=loop.run_forever, name="mcp-client", daemon=True)
        self._thread.start()
        client = Client(self._transport, timeout=self._timeout)
        try:
            self._submit(client.__aenter__())
            self._submit(client.list_tools())  # 살아 있는지 확인(ping은 서버 구현에 따라 없을 수 있다)
        except Exception as exc:
            self._shutdown_loop()
            raise ConfigError(f"MCP 서버를 띄우지 못했습니다: {type(exc).__name__}: {exc}") from exc
        self._client = client
        self.healthy = True

    def stop(self) -> None:
        if self._client is not None and self._loop is not None:
            with contextlib.suppress(Exception):  # 종료 중 오류는 삼킨다
                self._submit(self._client.__aexit__(None, None, None))
            self._client = None
        self._shutdown_loop()
        self.healthy = False

    def _shutdown_loop(self) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
            if self._thread is not None:
                self._thread.join(timeout=5)
            self._loop = None
            self._thread = None

    def _submit(self, coro: Coroutine[Any, Any, T]) -> T:
        assert self._loop is not None
        fut: concurrent.futures.Future[T] = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result(timeout=self._timeout + 5)

    # -- 호출 --
    def _call(self, make: Callable[[Client], Coroutine[Any, Any, T]]) -> T:
        if self._client is None:
            raise ConfigError("MCP 클라이언트가 시작되지 않았습니다")
        client = self._client
        with self._lock:
            try:
                result, retried = with_retry(lambda: self._submit(make(client)), self._retries, self._base_delay)
            except _TIMEOUT_ERRORS as exc:
                self.healthy = False
                self.last_error = f"timeout: {exc}"
                raise ConfigError(f"MCP 서버가 응답하지 않습니다: {exc}") from exc
            except Exception as exc:
                # 툴·리소스 오류(ToolError/MCPError)는 서버가 살아 있는 것이고, 연결 끊김은 죽은 것이다
                name = type(exc).__name__
                closed = getattr(getattr(exc, "error", None), "code", None) == CONNECTION_CLOSED
                if name in ("ToolError", "MCPError", "McpError") and not closed:
                    raise
                self.healthy = False
                self.last_error = f"{name}: {exc}"
                raise ConfigError(f"MCP 서버 연결이 끊겼습니다: {name}: {exc}") from exc
        self.retry_count += retried
        return result

    def ping(self) -> bool:
        """서버가 살아 있고 응답하는지. 실패하면 healthy를 끈다."""
        try:
            self._call(lambda c: c.list_tools())
            return True
        except ConfigError:
            return False

    def call_tool(self, name: str, arguments: dict[str, Any], meta: dict[str, Any] | None = None) -> Any:
        """meta는 MCP 요청의 `_meta`로 간다(LLM이 보지 않는 값, 예: 회사 기록 서버의 작업 범위 토큰)."""
        self.calls += 1
        result = self._call(lambda c: c.call_tool(name, arguments, meta=meta))
        if result.data is not None:
            return result.data
        if result.structured_content is not None:
            return result.structured_content.get("result", result.structured_content)
        text = result.content[0].text if result.content else "null"  # type: ignore[union-attr]
        return json.loads(text)

    def read_resource(self, uri: str) -> str:
        contents = self._call(lambda c: c.read_resource(uri))
        return str(getattr(contents[0], "text", ""))

    def read_json_resource(self, uri: str) -> Any:
        return json.loads(self.read_resource(uri))

    def get_prompt(self, name: str, arguments: dict[str, Any]) -> str:
        result = self._call(lambda c: c.get_prompt(name, arguments))
        content = result.messages[0].content
        return str(getattr(content, "text", content))

    def list_resource_templates(self) -> list[str]:
        templates = self._call(lambda c: c.list_resource_templates())
        return [str(t.uri_template) for t in templates]

    def list_tools(self) -> list[str]:
        return [t.name for t in self._call(lambda c: c.list_tools())]

    def list_prompts(self) -> list[str]:
        return [p.name for p in self._call(lambda c: c.list_prompts())]
