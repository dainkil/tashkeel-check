"""서류 묶음 검색 틀(단계 2). 같은 이름이 묶음의 다른 서류에 어떻게 적혀 있는지 찾는다.

검색은 세 가지를 합친다. 결과마다 출처(파일, parent, 줄)가 따라온다.
1. 아랍어 철자 정확 일치: 같은 줄이나 다음 줄의 라틴 문자 표기를 근거 후보로 돌려준다(이중 언어 서류).
2. 로마자 후보의 유사 일치: match_spelling(모음을 살린 비교).
3. 벡터 검색: Child 조각으로 찾고 Parent 원문을 돌려준다(참고 사이트 Parent–Child, 계약서처럼 조건이 중요한 문서).

이름은 임베딩 유사도만으로 잘 잡히지 않으므로 1·2가 주 경로이고 3은 보조다.
임베딩은 OpenAI 키가 있으면 다국어 OpenAI 임베딩, 없으면 골격과 같은 연습용 문자 n-gram 임베딩을 쓴다.
"""

from __future__ import annotations

import os
import re
import uuid
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.tools import BaseTool, tool
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..romanize import spelling_in_text
from ..text import Token, has_latin, normalize_key

if TYPE_CHECKING:
    from langchain_qdrant import QdrantVectorStore

LATIN_SPAN_RE = re.compile(r"[A-Za-z][A-Za-z'’\- ]*[A-Za-z]")


class PracticeEmbeddings(Embeddings):
    """연습용(골격 rag_beginner_todo와 같은 방식). 의미를 이해하는 임베딩이 아니다."""

    def __init__(self) -> None:
        from sklearn.feature_extraction.text import HashingVectorizer

        self.vectorizer = HashingVectorizer(analyzer="char", ngram_range=(2, 3), n_features=512, alternate_sign=False)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.vectorizer.transform(texts).toarray().tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


def default_embeddings(model: str = "text-embedding-3-small") -> tuple[Embeddings, str]:
    if os.getenv("OPENAI_API_KEY"):
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=model), f"openai:{model}"
    return PracticeEmbeddings(), "practice-char-ngram"


@dataclass
class BundleHit:
    method: str  # arabic_exact | romanized | vector
    source: str  # 파일 이름
    parent_id: str
    line_no: int | None
    text: str
    latin_candidates: list[str]
    score: float | None = None
    document_id: str | None = None  # from_documents로 만든 색인에서만 채워진다(인용 검증용)
    segment_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class BundleIndex:
    def __init__(
        self,
        parent_size: int = 800,
        child_size: int = 200,
        child_overlap: int = 30,
        embeddings: Embeddings | None = None,
        embedding_label: str | None = None,
    ):
        self.parent_splitter = RecursiveCharacterTextSplitter(chunk_size=parent_size, chunk_overlap=0)
        self.child_splitter = RecursiveCharacterTextSplitter(chunk_size=child_size, chunk_overlap=child_overlap)
        if embeddings is None:
            embeddings, embedding_label = default_embeddings()
        self.embeddings = embeddings
        self.embedding_label = embedding_label or type(embeddings).__name__
        self.parents: dict[str, Document] = {}
        self.store: QdrantVectorStore | None = None

    @classmethod
    def from_dir(cls, bundle_dir: str | Path, **kwargs: Any) -> BundleIndex:
        docs = [
            Document(page_content=p.read_text(encoding="utf-8"), metadata={"source": p.name})
            for p in sorted(Path(bundle_dir).iterdir())
            if p.suffix in {".txt", ".md"}
        ]
        index = cls(**kwargs)
        index.add(docs)
        return index

    @classmethod
    def from_documents(cls, documents: Any, entity_id: str | None = None, **kwargs: Any) -> BundleIndex:
        """묶음 서류(bundle.schemas.Document)를 구간 단위로 색인한다. entity_id를 주면 그 대상의 구간만 넣는다.

        같은 아랍어 표기가 다른 대상에 있어도 섞이지 않게 하려는 것이다(ADR-018). 결과는 후보 힌트일 뿐
        근거가 아니다. 근거는 bundle.evidence.search_evidence가 대상 ID로 찾고 검증한다."""
        docs = [
            Document(
                page_content=seg.text,
                metadata={"source": doc.document_id, "document_id": doc.document_id, "segment_id": seg.segment_id},
            )
            for doc in documents
            for seg in doc.segments
            if entity_id is None or seg.entity_id == entity_id
        ]
        index = cls(**kwargs)
        index.add(docs)
        return index

    def add(self, docs: list[Document]) -> None:
        from langchain_qdrant import QdrantVectorStore

        children: list[Document] = []
        for doc in docs:
            for parent in self.parent_splitter.split_documents([doc]):
                pid = uuid.uuid4().hex[:12]
                parent.metadata["parent_id"] = pid
                self.parents[pid] = parent
                for child in self.child_splitter.split_documents([parent]):
                    child.metadata["parent_id"] = pid
                    children.append(child)
        if children:
            self.store = QdrantVectorStore.from_documents(
                children, self.embeddings, location=":memory:", collection_name=f"bundle_{uuid.uuid4().hex[:6]}"
            )

    def _lines(self) -> Iterator[tuple[str, str, int, str, list[str]]]:
        for pid, parent in self.parents.items():
            lines = parent.page_content.splitlines()
            for i, line in enumerate(lines):
                yield pid, parent.metadata["source"], i, line, lines

    def _hit(self, method: str, pid: str, source: str, line_no: int | None, text: str, latin: list[str], score=None):  # type: ignore[no-untyped-def]
        meta = self.parents[pid].metadata
        return BundleHit(
            method, source, pid, line_no, text, latin, score, meta.get("document_id"), meta.get("segment_id")
        )

    def search(self, arabic: str, romanized: list[str], k: int = 4) -> list[BundleHit]:
        hits: list[BundleHit] = []
        key = normalize_key(arabic)
        for pid, source, i, line, lines in self._lines():
            if key and key in normalize_key(line):
                window = " ".join(lines[i : i + 2])
                latin = [m.group(0).strip() for m in LATIN_SPAN_RE.finditer(window)] if has_latin(window) else []
                hits.append(self._hit("arabic_exact", pid, source, i, line, latin))
            spans = [m.group(0).strip() for m in LATIN_SPAN_RE.finditer(line)]
            matched = [s for s in spans for r in romanized if r and spelling_in_text(r, s)]
            if matched:
                hits.append(self._hit("romanized", pid, source, i, line, sorted(set(matched))))
        if self.store is not None:
            query = " ".join([arabic, *romanized]).strip()
            seen = set()
            for child, score in self.store.similarity_search_with_score(query, k=k):
                pid = child.metadata["parent_id"]
                if pid in seen:
                    continue
                seen.add(pid)
                parent = self.parents[pid]
                hits.append(
                    self._hit("vector", pid, parent.metadata["source"], None, parent.page_content, [], float(score))
                )
        return hits


def make_bundle_search_tool(index: BundleIndex) -> Callable[[list[Token], list[dict]], BaseTool]:
    """그래프의 extra_tool_factories에 넣는 팩토리를 돌려준다. 문서마다 토큰 표가 달라 팩토리로 만든다."""

    def factory(tokens: list[Token], log: list[dict]) -> BaseTool:
        by_id = {t["id"]: t for t in tokens}

        @tool("search_bundle")
        def search_bundle(token_ids: list[int], romanized_candidates: list[str]) -> list[dict]:
            """Search the client's reference bundle (passport copies, registry extracts, earlier English letters)
            for the Arabic name at these token ids and for the romanized candidates. Every hit names its source file."""
            arabic = " ".join(by_id[t]["text"] for t in token_ids if t in by_id)
            hits = index.search(arabic, romanized_candidates)
            log.append({"tool": "search_bundle", "token_ids": list(token_ids), "hits": len(hits)})
            return [h.to_dict() for h in hits]

        return search_bundle

    return factory
