"""검수 작업 실행: 스레드에서 그래프를 돌리고, 노드 진행을 이벤트로 흘리며, 결과를 DB와 results/에 남긴다.

그래프 노드가 동기라 ThreadPoolExecutor로 돌린다(큐 서버 없음, docs/roadmap.md 2.1절). 토큰 스트리밍은 없다.
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..errors import ConfigError, InputError, TashkeelError
from ..mcp.client import MCPClient
from ..results import ReviewResult
from ..runner import Reviewer
from ..text import tokenize
from .db import Database, new_id
from .usage import MemoryUsageStore, UsageRecord, UsageStore

logger = logging.getLogger(__name__)

NODES = ("load", "analyze", "agent", "validate", "reconcile", "export")


@dataclass
class JobRecord:
    id: str
    doc: dict
    source: str  # paste | sample
    condition: str
    customer_id: str | None = None  # 인증된 요청이면 키의 고객(ADR-019)
    status: str = "queued"  # queued | running | done | failed
    node: str | None = None
    attempts: int = 0
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    document_id: str | None = None
    run_id: str | None = None
    out_dir: str | None = None
    result: ReviewResult | None = None
    events: list[dict] = field(default_factory=list)
    cond: threading.Condition = field(default_factory=threading.Condition)

    def summary(self) -> dict[str, Any]:
        return {
            "job_id": self.id,
            "doc_id": self.doc["doc_id"],
            "source": self.source,
            "condition": self.condition,
            "customer_id": self.customer_id,
            "status": self.status,
            "node": self.node,
            "attempts": self.attempts,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "document_id": self.document_id,
            "run_id": self.run_id,
            "out_dir": self.out_dir,
        }

    def emit(self, event: str, **data: Any) -> None:
        with self.cond:
            self.events.append({"event": event, "job_id": self.id, "t": round(time.time(), 3), **data})
            self.cond.notify_all()


class JobManager:
    def __init__(
        self,
        reviewer: Reviewer,
        results_dir: Path,
        db: Database | None = None,
        mcp: MCPClient | None = None,
        max_workers: int = 1,
        keep: int = 200,
        usage: UsageStore | None = None,
    ) -> None:
        self.reviewer = reviewer
        self.results_dir = Path(results_dir)
        self.db = db
        self.mcp = mcp
        self.keep = keep
        self.usage: UsageStore = usage if usage is not None else MemoryUsageStore()
        self._jobs: dict[str, JobRecord] = {}
        self._order: list[str] = []
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="review")

    # -- 조회 --
    def get(self, job_id: str) -> JobRecord | None:
        return self._jobs.get(job_id)

    def recent(self, limit: int, customer_id: str | None = None) -> list[dict]:
        with self._lock:
            ids = list(reversed(self._order))
        rows = [self._jobs[i] for i in ids if i in self._jobs]
        if customer_id is not None:
            rows = [j for j in rows if j.customer_id == customer_id]
        return [j.summary() for j in rows[:limit]]

    def db_ok(self) -> bool | None:
        """None: DB 없음, True/False: 연결 여부."""
        return None if self.db is None else self.db.ping()

    def mcp_ok(self) -> bool | None:
        if self.mcp is None:
            return None
        try:
            return self.mcp.ping()
        except Exception:
            return False

    # -- 생성 --
    def submit(self, doc: dict, condition: str, source: str, customer_id: str | None = None) -> JobRecord:
        """doc는 이미 검증된 입력(구간 1개 이상, 아랍어 토큰 1개 이상, 조건 유효)이다."""
        job = JobRecord(id=new_id(), doc=doc, source=source, condition=condition, customer_id=customer_id)
        if self.db is not None:
            if not self.db.ping():
                raise ConfigError("DB에 연결할 수 없습니다(DATABASE_URL). 검수 작업을 만들지 않습니다.")
            job.document_id = self.db.insert_document(doc, source, [dict(t) for t in tokenize(doc["segments"])])
            self.db.insert_job(job.id, job.document_id, condition, customer_id)
        with self._lock:
            self._jobs[job.id] = job
            self._order.append(job.id)
            for old in self._order[: -self.keep]:
                self._jobs.pop(old, None)
            self._order = self._order[-self.keep :]
        job.emit("queued", condition=condition, doc_id=doc["doc_id"])
        self._pool.submit(self._run, job)
        return job

    # -- 실행 --
    def _db_update(self, job: JobRecord, **fields: Any) -> None:
        if self.db is None:
            return
        try:
            self.db.update_job(job.id, **fields)
        except Exception as exc:  # DB가 중간에 끊겨도 작업은 끝까지 간다(결과 파일은 남는다)
            logger.warning("작업 %s DB 갱신 실패: %s", job.id, exc)

    def _run(self, job: JobRecord) -> None:
        job.status, job.started_at = "running", datetime.now(UTC)
        self._db_update(job, status="running", started_at=job.started_at)
        out_dir = self.results_dir / "web" / job.id
        job.out_dir = str(out_dir)

        def on_node(node: str, delta: dict) -> None:
            job.node = node
            if "attempts" in delta:
                job.attempts = int(delta["attempts"])
            info: dict[str, Any] = {"node": node, "attempts": job.attempts}
            if node == "validate":
                info["valid"] = bool(delta.get("valid"))
                errors = delta.get("errors") or []
                if errors:
                    info["last_error"] = errors[-1]
            if node == "agent" and self.mcp is not None and not self.mcp.healthy:
                info["mcp_error"] = self.mcp.last_error
            job.emit("node", **info)
            self._db_update(job, node=node, attempts=job.attempts)

        mcp_calls_before = self.mcp.calls if self.mcp is not None else 0
        try:
            if self.mcp is not None and not self.mcp.ping():
                raise ConfigError(f"MCP 서버가 응답하지 않습니다: {self.mcp.last_error or 'ping 실패'}")
            result = self.reviewer.run(job.doc, job.condition, out_dir=out_dir, on_node=on_node)
            if self.mcp is not None and not self.mcp.healthy:
                raise ConfigError(f"MCP 서버가 실행 중에 끊겼습니다: {self.mcp.last_error}")
            job.result = result
            if self.db is not None and job.document_id is not None:
                try:
                    job.run_id = self.db.insert_run(job.id, job.document_id, result, job.out_dir)
                except Exception as exc:
                    logger.warning("작업 %s 결과 DB 저장 실패: %s", job.id, exc)
                    job.error = f"결과 파일은 남았지만 DB 저장에 실패했습니다: {exc}"
            job.status = "done"
            job.finished_at = datetime.now(UTC)
            self._db_update(job, status="done", finished_at=job.finished_at, error=job.error)
            self._record_usage(job, result.metrics.get("usage") or {})
            job.emit(
                "done",
                attempts=result.metrics.get("attempts"),
                valid_output=result.metrics.get("valid_output"),
                errors=result.metrics.get("errors", []),
                run_id=job.run_id,
                db_error=job.error,
                mcp_calls=(self.mcp.calls - mcp_calls_before) if self.mcp is not None else None,
            )
        except (TashkeelError, Exception) as exc:
            kind = "input" if isinstance(exc, InputError) else "config" if isinstance(exc, ConfigError) else "internal"
            logger.warning("작업 %s 실패(%s)", job.id, kind, exc_info=not isinstance(exc, TashkeelError))
            job.status, job.error, job.finished_at = "failed", f"{type(exc).__name__}: {exc}", datetime.now(UTC)
            self._db_update(job, status="failed", error=job.error, finished_at=job.finished_at)
            job.emit("error", kind=kind, error=job.error)

    def _record_usage(self, job: JobRecord, usage: dict[str, Any]) -> None:
        try:
            self.usage.record(
                UsageRecord(
                    customer_id=job.customer_id,
                    kind="bundle_document" if job.source == "bundle" else "document",
                    job_id=job.id,
                    bundle_id=(job.doc.get("meta") or {}).get("bundle_id"),
                    condition=job.condition,
                    input_tokens=int(usage.get("input_tokens", 0) or 0),
                    output_tokens=int(usage.get("output_tokens", 0) or 0),
                    total_tokens=int(usage.get("total_tokens", 0) or 0),
                    llm_calls=int(usage.get("llm_calls", 0) or 0),
                    n_segments=len(job.doc["segments"]),
                    n_arabic_tokens=sum(1 for t in tokenize(job.doc["segments"]) if t["script"] == "ar"),
                )
            )
        except Exception as exc:  # 사용량 기록 실패가 작업 결과를 망치지 않는다
            logger.warning("작업 %s 사용량 기록 실패: %s", job.id, exc)

    # -- 이벤트 --
    def iter_events(self, job_id: str, timeout: float = 600.0):  # type: ignore[no-untyped-def]
        """누적 이벤트를 처음부터 재생하고, 작업이 끝날 때까지 새 이벤트를 기다린다."""
        job = self._jobs[job_id]
        i = 0
        deadline = time.time() + timeout
        while True:
            with job.cond:
                while i >= len(job.events):
                    if job.status in ("done", "failed") or time.time() > deadline:
                        return
                    job.cond.wait(timeout=1.0)
                ev = job.events[i]
            i += 1
            yield ev
            if ev["event"] in ("done", "error"):
                return

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
