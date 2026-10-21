"""묶음의 LLM 검수(가이드 9단계): 서류마다 단일 문서 작업(JobManager)을 돌리고, 끝나면 묶음 판정에 합류시킨다.

라벨 칸이 없는 문장의 고유명사는 LLM(C1~C3)이 뽑는다. 그 항목 가운데 대상 ID가 붙은 구간의 것만 근거 검색을 탄다.
API 호출 실패는 `model_error`로 기록하고 이름 미검출과 구분한다(ADR-016 `is_api_failure`).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ..bundle.pipeline import bundle_mentions, mentions_from_result, merge_mentions, model_error_item, review_mentions
from ..bundle.schemas import Bundle, ReviewItem
from ..experiments.exp002 import is_api_failure
from ..text import Segment, tokenize
from .bundles import BundleStore, Dictionary
from .db import new_id
from .jobs import JobManager


@dataclass
class BundleReview:
    id: str
    bundle: Bundle
    condition: str
    job_ids: dict[str, str]  # document_id → job_id
    skipped: list[str]  # 아랍어 토큰이 없어 LLM을 부르지 않은 서류
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: str = "running"  # running | done
    items: list[ReviewItem] | None = None
    errors: dict[str, str] = field(default_factory=dict)  # document_id → 오류


class BundleReviewManager:
    def __init__(self, jobs: JobManager, store: BundleStore, dictionary: Dictionary, keep: int = 200) -> None:
        self.jobs = jobs
        self.store = store
        self.dictionary = dictionary
        self.keep = keep
        self._reviews: dict[str, BundleReview] = {}
        self._lock = threading.Lock()

    def start(self, bundle: Bundle, condition: str) -> BundleReview:
        job_ids: dict[str, str] = {}
        skipped: list[str] = []
        for doc in bundle.documents:
            segments = [Segment(segment_id=s.segment_id, text=s.text) for s in doc.segments if s.text.strip()]
            if not any(t["script"] == "ar" for t in tokenize(segments)):
                skipped.append(doc.document_id)
                continue
            doc_in = {
                "doc_id": doc.document_id,
                "synthetic": bundle.synthetic,
                "segments": segments,
                "meta": {"source": "bundle", "bundle_id": bundle.bundle_id, "document_type": doc.document_type},
            }
            job_ids[doc.document_id] = self.jobs.submit(doc_in, condition, "bundle").id  # DB 불통 → ConfigError
        rec = BundleReview(id=new_id(), bundle=bundle, condition=condition, job_ids=job_ids, skipped=skipped)
        with self._lock:
            self._reviews[rec.id] = rec
            for old in list(self._reviews)[: -self.keep]:
                self._reviews.pop(old, None)
        self._refresh(rec)
        return rec

    def get(self, review_id: str) -> BundleReview | None:
        rec = self._reviews.get(review_id)
        if rec is not None:
            self._refresh(rec)
        return rec

    def _refresh(self, rec: BundleReview) -> None:
        if rec.status == "done":
            return
        jobs = {doc_id: self.jobs.get(job_id) for doc_id, job_id in rec.job_ids.items()}
        if any(j is None or j.status not in ("done", "failed") for j in jobs.values()):
            return
        with self._lock:
            if rec.status == "done":
                return
            bundle = rec.bundle
            llm = []
            errors: list[ReviewItem] = []
            for doc in bundle.documents:
                job = jobs.get(doc.document_id)
                if job is None:
                    continue
                if job.status == "failed" or job.result is None:
                    rec.errors[doc.document_id] = job.error or "failed"
                    errors.append(model_error_item(doc, job.error or "failed"))
                elif is_api_failure(job.result.metrics):
                    last = (job.result.metrics.get("errors") or ["API error"])[-1]
                    rec.errors[doc.document_id] = last
                    errors.append(model_error_item(doc, last))
                else:
                    llm += mentions_from_result(job.result, doc, bundle.entities)
            mentions = merge_mentions(bundle, bundle_mentions(bundle), llm)
            rec.items = review_mentions(bundle, mentions, self.dictionary) + errors
            rec.status = "done"
            self.store.save(bundle, rec.items)

    def summary(self, rec: BundleReview) -> dict[str, Any]:
        jobs = [self.jobs.get(j) for j in rec.job_ids.values()]
        return {
            "review_id": rec.id,
            "bundle_id": rec.bundle.bundle_id,
            "condition": rec.condition,
            "status": rec.status,
            "created_at": rec.created_at.isoformat(),
            "jobs": {doc_id: job_id for doc_id, job_id in rec.job_ids.items()},
            "job_status": {j.doc["doc_id"]: j.status for j in jobs if j is not None},
            "skipped": rec.skipped,
            "errors": rec.errors,
        }
