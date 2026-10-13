"""에이전트 구조화 출력(C1~C3). 모든 필드를 필수로 두고 값이 없으면 null을 쓰게 한다."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CandidateReading(BaseModel):
    reading: str | None = Field(description="Arabic with vowel marks if known, else null")
    romanized: str = Field(description="Latin-script spelling or transliteration")
    source: Literal["analyzer", "llm"] = Field(description="analyzer if it came from the morphological analyzer")


class Evidence(BaseModel):
    segment_id: str = Field(description="Segment of this document that contains the Latin-script spelling")
    quote: str = Field(description="Exact Latin-script text copied from that segment")


class Item(BaseModel):
    token_ids: list[int] = Field(description="Token ids from the token table; never rewrite Arabic")
    type: Literal["proper_noun", "word"]
    candidates: list[CandidateReading]
    decision: Literal["adopt", "abstain", "evidence_adopt", "hold"] = Field(
        description="word: adopt or abstain. proper_noun: evidence_adopt (needs evidence) or hold"
    )
    adopted: str | None = Field(description="Chosen reading/spelling, null when abstaining or holding")
    reason: str
    confidence: float | None = Field(description="0 to 1, for adopted readings; null otherwise")
    evidence: Evidence | None


class SegmentTranslation(BaseModel):
    segment_id: str
    english: str


class AgentOutput(BaseModel):
    """Translation of every segment plus one item per ambiguous span or proper noun."""

    translation: list[SegmentTranslation]
    items: list[Item]
