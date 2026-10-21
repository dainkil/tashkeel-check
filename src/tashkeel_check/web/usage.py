"""사용량 기록과 조회(ADR-019). 작업이 끝날 때 한 줄, 라벨 경로 묶음 검수에도 한 줄(토큰 0).

집계는 메모리와 DB가 같은 `summarize()`를 쓴다(기간 안의 줄을 가져와 파이썬에서 더한다).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

from .db import Database

UsageKind = Literal["document", "bundle_document", "bundle_label"]


class UsageRecord(BaseModel):
    customer_id: str | None = None
    kind: UsageKind
    job_id: str | None = None
    bundle_id: str | None = None
    review_id: str | None = None
    condition: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    llm_calls: int = 0
    n_segments: int = 0
    n_arabic_tokens: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UsageStore(Protocol):
    def record(self, rec: UsageRecord) -> None: ...
    def summary(self, customer_id: str | None, start: datetime, end: datetime) -> dict[str, Any]: ...


def summarize(rows: list[UsageRecord], start: datetime, end: datetime) -> dict[str, Any]:
    totals = {
        "jobs": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "llm_calls": 0,
        "segments": 0,
        "arabic_tokens": 0,
    }
    by_day: dict[str, dict[str, int]] = {}
    by_kind: dict[str, dict[str, int]] = {}
    for r in rows:
        totals["jobs"] += 1
        totals["input_tokens"] += r.input_tokens
        totals["output_tokens"] += r.output_tokens
        totals["total_tokens"] += r.total_tokens
        totals["llm_calls"] += r.llm_calls
        totals["segments"] += r.n_segments
        totals["arabic_tokens"] += r.n_arabic_tokens
        day = r.created_at.astimezone(UTC).date().isoformat()
        d = by_day.setdefault(day, {"jobs": 0, "total_tokens": 0})
        d["jobs"] += 1
        d["total_tokens"] += r.total_tokens
        k = by_kind.setdefault(r.kind, {"jobs": 0, "total_tokens": 0})
        k["jobs"] += 1
        k["total_tokens"] += r.total_tokens
    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "totals": totals,
        "by_day": [{"day": d, **v} for d, v in sorted(by_day.items())],
        "by_kind": [{"kind": k, **v} for k, v in sorted(by_kind.items())],
    }


class MemoryUsageStore:
    def __init__(self) -> None:
        self._rows: list[UsageRecord] = []

    def record(self, rec: UsageRecord) -> None:
        self._rows.append(rec)

    def summary(self, customer_id: str | None, start: datetime, end: datetime) -> dict[str, Any]:
        rows = [
            r
            for r in self._rows
            if (customer_id is None or r.customer_id == customer_id) and start <= r.created_at < end
        ]
        return summarize(rows, start, end)


class DbUsageStore:
    def __init__(self, db: Database) -> None:
        self.db = db

    def record(self, rec: UsageRecord) -> None:
        self.db.insert_usage(rec.model_dump(mode="python"))

    def summary(self, customer_id: str | None, start: datetime, end: datetime) -> dict[str, Any]:
        rows = [UsageRecord.model_validate(r) for r in self.db.usage_rows(customer_id, start, end)]
        return summarize(rows, start, end)
