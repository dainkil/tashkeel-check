"""실행 결과의 형식. 산출 파일(export), 단계 1.5 API 응답, DB 저장이 모두 이 형식을 따른다.

결과는 reconcile이 dict로 만들고, 그래프의 export 노드가 여기서 검증한다. 모르는 키가 있으면 오류를 내서
형식이 몰래 바뀌지 않게 한다. 지표(metrics)는 EXP 실행 전에 정의가 바뀔 수 있어 아직 dict로 둔다.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from .schemas import Item

FinalDecision = Literal["adopt", "abstain", "evidence_adopt", "hold", "adopt_unsupported"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CheckedItem(Item):
    """LLM이 낸 항목에 코드 검사 결과를 붙인 것(reconcile.check_items)."""

    model_config = ConfigDict(extra="forbid")

    item_index: int
    valid: bool  # 토큰 ID가 모두 이 문서의 아랍어 토큰인가
    final_decision: FinalDecision  # 강등 규칙(docs/architecture.md 4.5절)을 적용한 처분
    flags: list[str]
    evidence_failure: str | None
    arabic: str
    segment_id: str | None  # valid가 아니면 None


class Unprocessed(_Strict):
    """정답 이름이나 분석기 모호 토큰 가운데 어느 항목에도 덮이지 않은 토큰."""

    token_id: int
    text: str
    segment_id: str
    reason: Literal["gold_name", "ambiguous_word"]


class NameRow(_Strict):
    """확인 대기 목록의 한 줄(proper_nouns.csv). 값은 모두 사람이 읽는 문자열이다."""

    arabic: str
    token_ids: str
    candidates: str
    adopted: str
    decision: str
    evidence: str
    analyzer_counts: str
    flags: str


class SegmentResult(_Strict):
    segment_id: str
    arabic: str
    english: str | None
    items: list[CheckedItem]
    unprocessed: list[Unprocessed]


class RunMeta(_Strict):
    """실행 메타데이터(run_meta.json, docs/evaluation.md 6.3절)."""

    doc_id: str
    condition: str
    repeat: int
    model: str
    model_setting: str
    temperature: float | None
    prompt_version: str
    prompt_hash: str
    matcher_version: str
    analyzer: dict[str, str | None]
    package_version: str
    synthetic: bool
    doc_meta: dict[str, Any]
    bundle_search: bool
    tracing: bool
    high_confidence: float
    elapsed_s: float
    attempts: int
    usage: dict[str, int]
    tool_calls: int


class ReviewResult(_Strict):
    doc_id: str
    condition: str
    segments: list[SegmentResult]
    translation: dict[str, str]
    items: list[CheckedItem]
    unprocessed: list[Unprocessed]
    suspected_missed_names: list[int]
    gold_status: dict[str, str]  # 정답 이름 토큰 ID → 상태. gold가 없으면 비어 있다
    proper_nouns: list[NameRow]
    metrics: dict[str, Any]
    meta: RunMeta
