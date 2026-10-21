"""서류 묶음 검수(단계 2, 가이드 1~8단계).

한 묶음(bundle) 안의 여러 서류에서 같은 대상 ID(entity_id)가 붙은 다른 서류의 영문 칸을 근거로 찾아,
인용을 검증하고, 정확히 일치할 때만 확정한다. 대상은 사람·회사·기관·그 밖의 명명된 당사자 모두이고
종류에 따라 규칙이 달라지지 않는다. 단일 문서 경로(graph·reconcile)는 바꾸지 않는다(ADR-018).
"""

from .loader import BundleNotFound, InvalidBundle, load_bundle, parse_bundle
from .pipeline import review_bundle
from .schemas import Bundle, BundleEvidence, Document, NameMention, ReviewItem, Segment

__all__ = [
    "Bundle",
    "BundleEvidence",
    "BundleNotFound",
    "Document",
    "InvalidBundle",
    "NameMention",
    "ReviewItem",
    "Segment",
    "load_bundle",
    "parse_bundle",
    "review_bundle",
]
