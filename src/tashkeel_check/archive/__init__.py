"""회사 문서 보관함(ADR-022): 고객이 전에 올린 서류에서 같은 고유명사의 영문 표기를 찾는다."""

from .search import CompanyArchive, name_in_text, name_words, search_records
from .store import ArchiveDocument, ArchivePassage, ArchiveStore, InMemoryArchiveStore, build_passages, hit_id

__all__ = [
    "ArchiveDocument",
    "ArchivePassage",
    "ArchiveStore",
    "CompanyArchive",
    "InMemoryArchiveStore",
    "build_passages",
    "hit_id",
    "name_in_text",
    "name_words",
    "search_records",
]
