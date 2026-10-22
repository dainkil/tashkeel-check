"""회사 문서 보관함의 저장 형식과 메모리 저장소(ADR-022).

한 고객이 전에 올린 서류를 구간 단위 구절로 남긴다. 아랍어가 있고, 그 구간이나 다음 구간에 라틴 문자가 있는
구간만 남긴다(영문 표기를 찾을 수 없는 구절은 제안에 쓸 수 없다). 조회는 언제나 고객 범위 안에서만 한다.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from ..text import Segment, has_latin, normalize_key

AR_RE = re.compile("[ء-ي]")
LATIN_SPAN_RE = re.compile(r"[A-Za-z][A-Za-z'’\- ]*[A-Za-z]")  # rag/bundle.py와 같은 정의
MAX_TEXT = 600  # 구절 하나에 남기는 글자 수 상한(긴 구간은 잘라 둔다)


def hit_id(document_id: str, segment_id: str) -> str:
    """LLM이 구절을 고를 때 쓰는 짧은 ID. 출처를 지어내지 못하게 문서 ID 대신 이것만 보여 준다."""
    return hashlib.sha1(f"{document_id}:{segment_id}".encode()).hexdigest()[:10]


def text_sha256(segments: list[Segment]) -> str:
    """db.insert_document와 같은 방식(구간 텍스트를 줄바꿈으로 이은 것)."""
    return hashlib.sha256("\n".join(s["text"] for s in segments).encode("utf-8")).hexdigest()


class ArchivePassage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hit_id: str
    customer_id: str
    document_id: str
    document_label: str
    document_sha256: str
    segment_id: str
    text: str  # 구간 원문
    window: str  # 구간 + 다음 구간. 영문 표기를 찾고 검증하는 범위
    text_key: str  # normalize_key(text)
    latin_spans: list[str]
    embedding: list[float] | None = None
    embedding_model: str | None = None
    created_at: datetime


class ArchiveDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: str
    document_id: str
    document_label: str
    document_sha256: str
    n_passages: int
    created_at: datetime


def build_passages(
    customer_id: str, document_id: str, label: str, sha256: str, segments: list[Segment], created_at: datetime
) -> list[ArchivePassage]:
    out: list[ArchivePassage] = []
    for i, seg in enumerate(segments):
        text = seg["text"][:MAX_TEXT]
        if not AR_RE.search(text):
            continue
        nxt = segments[i + 1]["text"][:MAX_TEXT] if i + 1 < len(segments) else ""
        window = f"{text} {nxt}".strip()
        if not has_latin(window):
            continue
        out.append(
            ArchivePassage(
                hit_id=hit_id(document_id, seg["segment_id"]),
                customer_id=customer_id,
                document_id=document_id,
                document_label=label,
                document_sha256=sha256,
                segment_id=seg["segment_id"],
                text=text,
                window=window,
                text_key=normalize_key(text),
                latin_spans=[m.group(0).strip() for m in LATIN_SPAN_RE.finditer(window)],
                created_at=created_at,
            )
        )
    return out


class ArchiveStore(Protocol):
    def add(self, doc: ArchiveDocument, passages: list[ArchivePassage]) -> None: ...

    def candidates(self, customer_id: str, words: list[str]) -> list[ArchivePassage]:
        """구간 키에 이름의 모든 단어가 들어 있는 구절(대략 거르기). 단어 단위 확인은 search가 한다."""
        ...

    def get_passage(self, customer_id: str, hit_id: str) -> ArchivePassage | None: ...

    def list_documents(self, customer_id: str, limit: int = 200) -> list[ArchiveDocument]: ...

    def delete_document(self, customer_id: str, document_id: str) -> bool: ...


class InMemoryArchiveStore:
    """테스트와 DB 없는 실행용. 서버를 다시 띄우면 비어 있다. 고객마다 최근 문서 keep개만 둔다."""

    def __init__(self, keep: int = 500) -> None:
        self.keep = keep
        self._docs: dict[str, dict[str, ArchiveDocument]] = {}
        self._passages: dict[str, dict[str, ArchivePassage]] = {}

    def add(self, doc: ArchiveDocument, passages: list[ArchivePassage]) -> None:
        docs = self._docs.setdefault(doc.customer_id, {})
        rows = self._passages.setdefault(doc.customer_id, {})
        self.delete_document(doc.customer_id, doc.document_id)
        docs[doc.document_id] = doc
        for p in passages:
            rows[p.hit_id] = p
        while len(docs) > self.keep:
            oldest = min(docs.values(), key=lambda d: d.created_at)
            self.delete_document(doc.customer_id, oldest.document_id)

    def candidates(self, customer_id: str, words: list[str]) -> list[ArchivePassage]:
        rows = self._passages.get(customer_id, {}).values()
        return [p for p in rows if all(w in p.text_key for w in words)]

    def get_passage(self, customer_id: str, hit_id: str) -> ArchivePassage | None:
        return self._passages.get(customer_id, {}).get(hit_id)

    def list_documents(self, customer_id: str, limit: int = 200) -> list[ArchiveDocument]:
        rows = sorted(self._docs.get(customer_id, {}).values(), key=lambda d: d.created_at, reverse=True)
        return rows[:limit]

    def delete_document(self, customer_id: str, document_id: str) -> bool:
        docs = self._docs.get(customer_id, {})
        if docs.pop(document_id, None) is None:
            return False
        rows = self._passages.get(customer_id, {})
        for key in [k for k, p in rows.items() if p.document_id == document_id]:
            del rows[key]
        return True


def now() -> datetime:
    return datetime.now(UTC)
