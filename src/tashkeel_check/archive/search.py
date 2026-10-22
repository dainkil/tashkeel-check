"""보관함 검색(RAG)과 제안 검증(ADR-022). LLM 없이 코드가 한다.

찾기: (고객, 정규화 아랍어 이름)이 단어 단위로 들어 있는 구절을 먼저 고르고, 이번 서류에서 그 이름 주변 문맥과
임베딩이 비슷한 순서로 놓는다. 이름은 임베딩만으로 잘 잡히지 않으므로 아랍어 일치가 주 경로이고, 임베딩은
같은 대상인지 판단할 문맥(직함·근무처·주소)이 비슷한 구절을 앞에 놓는 데만 쓴다.
같은 철자라고 같은 대상은 아니다(ADR-018). 그래서 결과는 근거가 아니라 "보관함 제안" 재료이고, 확정은 사람이 한다.
"""

from __future__ import annotations

import logging
import math
import re
from typing import Any

from langchain_core.embeddings import Embeddings

from ..bundle.dictionary import DOCUMENT_SCOPE, DictionaryLookup
from ..romanize import strict_words_in_quote
from ..text import AR_LETTERS, Segment, normalize_key
from .store import ArchiveDocument, ArchivePassage, ArchiveStore, build_passages, now, text_sha256

logger = logging.getLogger(__name__)

AR_WORD_RE = re.compile(f"[{AR_LETTERS}]+")
PROCLITICS = "وبلفك"  # 이름 앞에 붙는 한 글자 접두(و·ب·ل·ف·ك)
MIN_NAME_CHARS = 3  # 이보다 짧은 이름(공백 제외)은 찾지 않는다(흔한 짧은 단어가 마구 걸린다)
MAX_NAMES = 40  # 한 번 호출에 찾는 이름 수 상한
MAX_HITS = 4  # 이름 하나에 돌려주는 구절 수 상한
MAX_HIT_TEXT = 500


def name_words(arabic: str) -> list[str]:
    return AR_WORD_RE.findall(normalize_key(arabic))


def name_in_text(words: list[str], text_key: str) -> bool:
    """이름 단어열이 구절 안에 단어 단위로 연속해 있는지. 첫 단어 앞의 한 글자 접두(و 등)는 허용한다."""
    if not words:
        return False
    tw = AR_WORD_RE.findall(text_key)
    n = len(words)
    for i in range(len(tw) - n + 1):
        first = tw[i]
        head_ok = first == words[0] or (
            len(first) == len(words[0]) + 1 and first[0] in PROCLITICS and first[1:] == words[0]
        )
        if head_ok and tw[i + 1 : i + n] == words[1:]:
            return True
    return False


def make_embeddings(llm_backend: str, model: str) -> tuple[Embeddings, str]:
    """실제 모델 서비스는 OpenAI 임베딩(보관함 글이 OpenAI로 간다, LLM 호출과 같은 경계), 가짜 모델은 연습용 n-gram."""
    if llm_backend == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=model), f"openai:{model}"
    from ..rag.bundle import PracticeEmbeddings

    return PracticeEmbeddings(), "practice-char-ngram"


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class CompanyArchive:
    """저장소(메모리·DB) + 임베딩. 서비스 Runtime이 하나 만들어 MCP 서버와 덧씌움이 같이 쓴다."""

    def __init__(
        self, store: ArchiveStore, embeddings: Embeddings | None = None, embedding_label: str | None = None
    ) -> None:
        self.store = store
        self.embeddings = embeddings
        self.embedding_label = embedding_label or (type(embeddings).__name__ if embeddings else None)

    def _embed(self, texts: list[str]) -> list[list[float]] | None:
        if self.embeddings is None or not texts:
            return None
        try:
            return self.embeddings.embed_documents(texts)
        except Exception as exc:  # 임베딩이 실패해도 보관·검색은 한다(순서만 최근 순)
            logger.warning("보관함 임베딩 실패: %s", exc)
            return None

    # -- 쓰기 --
    def index_document(
        self, customer_id: str, document_id: str, label: str, segments: list[Segment], sha256: str | None = None
    ) -> int:
        sha = sha256 or text_sha256(segments)
        created = now()
        passages = build_passages(customer_id, document_id, label, sha, segments, created)
        vectors = self._embed([p.text for p in passages])
        if vectors is not None:
            passages = [
                p.model_copy(update={"embedding": v, "embedding_model": self.embedding_label})
                for p, v in zip(passages, vectors, strict=True)
            ]
        doc = ArchiveDocument(
            customer_id=customer_id,
            document_id=document_id,
            document_label=label,
            document_sha256=sha,
            n_passages=len(passages),
            created_at=created,
        )
        self.store.add(doc, passages)
        return len(passages)

    def list_documents(self, customer_id: str, limit: int = 200) -> list[ArchiveDocument]:
        return self.store.list_documents(customer_id, limit)

    def delete_document(self, customer_id: str, document_id: str) -> bool:
        return self.store.delete_document(customer_id, document_id)

    # -- 읽기 --
    def find(
        self, customer_id: str, arabic: str, exclude_document_id: str | None, exclude_sha256: str | None
    ) -> list[ArchivePassage]:
        words = name_words(arabic)
        if sum(len(w) for w in words) < MIN_NAME_CHARS:
            return []
        rows = self.store.candidates(customer_id, words)
        return [
            p
            for p in rows
            if p.customer_id == customer_id
            and p.document_id != exclude_document_id
            and (exclude_sha256 is None or p.document_sha256 != exclude_sha256)
            and name_in_text(words, p.text_key)
        ]

    def get_passage(self, customer_id: str, hit_id: str) -> ArchivePassage | None:
        p = self.store.get_passage(customer_id, hit_id)
        return p if p is not None and p.customer_id == customer_id else None

    def verify_pick(
        self,
        customer_id: str,
        hit_id: str,
        arabic: str,
        spelling: str,
        exclude_document_id: str | None,
        exclude_sha256: str | None,
    ) -> ArchivePassage | None:
        """제안을 화면에 내기 전 코드 확인: 같은 고객의 다른 서류 구절이고, 이름이 그 구절에 있고,
        철자가 구절 안 라틴 문자와 글자 그대로 같다(근거 검사 v2 규칙)."""
        p = self.get_passage(customer_id, hit_id)
        if p is None or p.document_id == exclude_document_id:
            return None
        if exclude_sha256 is not None and p.document_sha256 == exclude_sha256:
            return None
        if not name_in_text(name_words(arabic), p.text_key):
            return None
        if not spelling.strip() or not strict_words_in_quote(spelling, p.window):
            return None
        return p


def search_records(
    archive: CompanyArchive,
    dictionary: DictionaryLookup | None,
    customer_id: str,
    names: list[dict[str, Any]],
    exclude_document_id: str | None,
    exclude_sha256: str | None,
) -> list[dict[str, Any]]:
    """names: [{token_ids, arabic, context}]. 이름마다 사람이 확정한 사전 표기가 있으면 그것만, 없으면 보관함 구절."""
    out: list[dict[str, Any]] = []
    pending: list[tuple[dict[str, Any], str, list[ArchivePassage]]] = []
    for q in names[:MAX_NAMES]:
        arabic = str(q.get("arabic") or "")
        row: dict[str, Any] = {"token_ids": list(q.get("token_ids") or []), "arabic": arabic, "dictionary": None}
        entry = (
            dictionary.lookup_verified_name(customer_id, DOCUMENT_SCOPE, normalize_key(arabic)) if dictionary else None
        )
        if entry is not None:
            row["dictionary"] = {"english": entry.english_name, "entry_id": entry.id}
            row["hits"] = []
            row["note"] = "confirmed by a person at the client; the system applies it"
            out.append(row)
            continue
        found = archive.find(customer_id, arabic, exclude_document_id, exclude_sha256)
        row["hits"] = []
        out.append(row)
        if found:
            pending.append((row, str(q.get("context") or arabic), found))
    vectors = (
        archive._embed([ctx for _, ctx, _ in pending]) if any(p.embedding for _, _, f in pending for p in f) else None
    )
    for i, (row, _, found) in enumerate(pending):
        q_vec = vectors[i] if vectors is not None else None
        scored = []
        for p in found:
            sim = _cosine(q_vec, p.embedding) if q_vec is not None and p.embedding else None
            scored.append((sim if sim is not None else -1.0, p.created_at.timestamp(), p, sim))
        scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
        row["hits"] = [
            {
                "hit_id": p.hit_id,
                "document": p.document_label,
                "date": p.created_at.date().isoformat(),
                "text": p.window[:MAX_HIT_TEXT],
                "latin_candidates": p.latin_spans,
                "similarity": None if sim is None else round(sim, 3),
            }
            for _, _, p, sim in scored[:MAX_HITS]
        ]
    return out
