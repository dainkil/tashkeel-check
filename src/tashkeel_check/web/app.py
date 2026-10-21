"""FastAPI 앱(단계 1.5, docs/roadmap.md 2.3절 M1.5 부분집합). 단일 문서 범위, 읽기 전용 화면.

구성은 `build_runtime(settings)`가 먼저 만든다(모델·분석기·DB·MCP·Reviewer). 키가 없거나 분석기를 못 띄우면
ConfigError로 기동을 거부한다. `create_app(runtime)`은 엔드포인트만 붙인다. 테스트는 가짜 모델로 runtime을 만든다.
"""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field

from .. import __version__
from ..analyzer import AnalyzeFn, analyzer_version, thread_safe_analyze
from ..bundle import Bundle, parse_bundle, review_bundle
from ..bundle.dictionary import DictionaryEntry, InMemoryDictionary
from ..bundle.schemas import REASON_LABELS, ReviewItem
from ..config import CONDITIONS, Settings, configure_tracing, has_openai_key
from ..errors import ConfigError, InputError
from ..mcp.client import MCPClient, default_server_command
from ..mcp.tools import make_mcp_analyze_tool_factory
from ..runner import Reviewer, load_doc, make_model, model_label, split_gold
from ..text import Segment, normalize_key, segment_text, tokenize
from .bundles import BundleStore, DbBundleStore, DbDictionary, Dictionary, MemoryBundleStore
from .db import Database
from .jobs import NODES, JobManager

logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).parent / "static"
SAMPLE_SPLIT = "dev"  # eval은 최종 평가용이라 화면에 내지 않는다


@dataclass
class Runtime:
    settings: Settings
    model: BaseChatModel
    analyze_fn: AnalyzeFn
    reviewer: Reviewer
    db: Database | None
    mcp: MCPClient | None
    tracing: bool
    bundles: BundleStore
    dictionary: Dictionary

    @property
    def backend(self) -> str:
        return self.settings.llm_backend


def build_runtime(
    settings: Settings,
    model: BaseChatModel | None = None,
    analyze_fn: AnalyzeFn | None = None,
    mcp: MCPClient | None = None,
) -> Runtime:
    """기동에 필요한 것을 전부 만든다. 실패는 ConfigError(CLI 종료 코드 3)."""
    tracing = configure_tracing(settings)
    fn = analyze_fn or thread_safe_analyze()  # 분석기를 못 띄우면 AnalyzerUnavailable(ConfigError)
    if model is None:
        if settings.llm_backend == "openai" and not has_openai_key():
            raise ConfigError("OPENAI_API_KEY가 없습니다. .env에 키를 넣거나 LLM_BACKEND=fake(가짜 모델)로 실행하세요.")
        model = make_model(settings, fake=settings.llm_backend == "fake")
    db = Database(settings.database_url) if settings.database_url else None
    if db is not None and not db.ping():
        logger.warning("DB에 연결할 수 없습니다(DATABASE_URL). 기동은 하지만 검수 작업 생성은 503입니다.")
    client = mcp
    if client is None and settings.use_mcp_tools:
        cmd, args, env = default_server_command(settings.data_dir)
        client = MCPClient(cmd, args, env=env)
        client.start()  # 실패 → ConfigError
    factory = make_mcp_analyze_tool_factory(client) if client is not None else None
    reviewer = Reviewer(model, settings, analyze_fn=fn, analyze_tool_factory=factory)
    bundles: BundleStore = DbBundleStore(db) if db is not None else MemoryBundleStore()
    dictionary: Dictionary = DbDictionary(db) if db is not None else InMemoryDictionary()
    return Runtime(settings, model, fn, reviewer, db, client, tracing, bundles, dictionary)


class SegmentIn(BaseModel):
    segment_id: str
    text: str


class ReviewRequest(BaseModel):
    text: str | None = Field(None, description="빈 줄·줄 단위로 구간을 나눈다")
    segments: list[SegmentIn] | None = None
    condition: str = "C3"
    doc_id: str | None = Field(None, description="합성 dev 문서 id. 주면 text·segments 대신 그 문서를 쓴다")


def _samples_dir(settings: Settings) -> Path:
    return settings.data_dir / "synthetic" / SAMPLE_SPLIT


def _bundle_samples_dir(settings: Settings) -> Path:
    return settings.data_dir / "synthetic" / "bundles" / SAMPLE_SPLIT


class DictionaryCloseRequest(BaseModel):
    bundle_id: str
    mention_id: str
    english_name: str | None = Field(None, description="비우면 항목의 번역 표기를 등록한다")
    verified_by: str = "reviewer"


def _item_json(item: ReviewItem) -> dict[str, Any]:
    body = item.model_dump(mode="json")
    body["reason_label"] = REASON_LABELS[item.reason]
    return body


def _not_found(what: str) -> JSONResponse:
    return JSONResponse({"error": what, "kind": "input"}, status_code=404)


def _list_samples(rt: Runtime) -> list[dict]:
    if rt.mcp is not None:
        rows = rt.mcp.read_json_resource(f"document://synthetic/{SAMPLE_SPLIT}")
        return [dict(r, via="mcp") for r in rows]
    rows = []
    for path in sorted(_samples_dir(rt.settings).glob("*.json")):
        doc = load_doc(path)
        rows.append(
            {"doc_id": doc["doc_id"], "doc_type": doc.get("doc_type"), "evidence_layout": doc.get("evidence_layout")}
        )
    return rows


def _load_sample(rt: Runtime, doc_id: str) -> dict | None:
    path = _samples_dir(rt.settings) / f"{doc_id}.json"
    if not path.is_file() or path.name != f"{doc_id}.json":
        return None
    return load_doc(path)


def _build_doc(rt: Runtime, req: ReviewRequest) -> tuple[dict, str]:
    """입력을 검증해 그래프 입력 문서로 만든다. 400 사유: 빈 입력, 아랍어 토큰 0개, 조건 오류, 없는 샘플."""
    if req.condition not in CONDITIONS:
        raise InputError(f"조건은 {', '.join(CONDITIONS)} 중 하나여야 합니다: {req.condition!r}")
    if req.doc_id:
        doc = _load_sample(rt, req.doc_id)
        if doc is None:
            raise InputError(f"샘플 문서가 없습니다: {req.doc_id!r}")
        return doc, "sample"
    segments: list[Segment]
    if req.segments:
        segments = [Segment(segment_id=s.segment_id, text=s.text.strip()) for s in req.segments if s.text.strip()]
    elif req.text and req.text.strip():
        segments = segment_text(req.text)
    else:
        raise InputError("빈 입력입니다. 아랍어 텍스트를 넣거나 샘플 문서를 고르세요.")
    if not segments:
        raise InputError("빈 입력입니다. 아랍어 텍스트를 넣거나 샘플 문서를 고르세요.")
    if not any(t["script"] == "ar" for t in tokenize(segments)):
        raise InputError("아랍어 토큰이 없습니다. 아랍 문자로 된 문서를 넣으세요.")
    doc = {"doc_id": "paste", "synthetic": False, "segments": segments, "meta": {"source": "paste"}}
    return doc, "paste"


def _sse(event: dict) -> str:
    return f"event: {event['event']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"


def create_app(runtime: Runtime, max_workers: int = 1) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.rt = runtime
        app.state.jobs = JobManager(
            runtime.reviewer, runtime.settings.results_dir, db=runtime.db, mcp=runtime.mcp, max_workers=max_workers
        )
        try:
            yield
        finally:
            app.state.jobs.shutdown()
            if runtime.mcp is not None:
                runtime.mcp.stop()

    app = FastAPI(title="Tashkeel Check", version=__version__, lifespan=lifespan)

    @app.exception_handler(InputError)
    async def _input_error(request: Request, exc: InputError) -> JSONResponse:
        return JSONResponse({"error": str(exc), "kind": "input"}, status_code=400)

    @app.exception_handler(ConfigError)
    async def _config_error(request: Request, exc: ConfigError) -> JSONResponse:
        return JSONResponse({"error": str(exc), "kind": "config"}, status_code=503)

    def jobs(request: Request) -> JobManager:
        jm: JobManager = request.app.state.jobs
        return jm

    @app.get("/health")
    def health(request: Request) -> dict[str, Any]:
        jm = jobs(request)
        return {
            "status": "ok",
            "version": __version__,
            "model": model_label(runtime.model, runtime.settings),
            "backend": runtime.backend,
            "analyzer": analyzer_version(),
            "db": "disabled" if runtime.db is None else jm.db_ok(),
            "mcp": "disabled" if runtime.mcp is None else jm.mcp_ok(),
            "tracing": runtime.tracing,
            "python": sys.version.split()[0],
            "nodes": list(NODES),
        }

    @app.get("/v1/samples")
    def samples() -> list[dict]:
        return _list_samples(runtime)

    @app.get("/v1/samples/{doc_id}")
    def sample(doc_id: str) -> JSONResponse:
        doc = _load_sample(runtime, doc_id)
        if doc is None:
            return JSONResponse({"error": f"샘플 문서가 없습니다: {doc_id!r}", "kind": "input"}, status_code=404)
        doc_in, _ = split_gold(doc)
        public = {k: doc_in[k] for k in ("doc_id", "doc_type", "evidence_layout", "segments", "notice") if k in doc_in}
        return JSONResponse(public)

    @app.post("/v1/reviews", status_code=202)
    def create_review(req: ReviewRequest, request: Request) -> dict[str, Any]:
        doc, source = _build_doc(runtime, req)
        job = jobs(request).submit(doc, req.condition, source)  # DB 불통 → ConfigError → 503
        return {"job_id": job.id, "status": job.status, "condition": job.condition, "doc_id": doc["doc_id"]}

    @app.get("/v1/jobs")
    def list_jobs(request: Request, limit: int = 20) -> list[dict]:
        return jobs(request).recent(max(1, min(limit, 200)))

    @app.get("/v1/jobs/{job_id}")
    def get_job(job_id: str, request: Request) -> JSONResponse:
        job = jobs(request).get(job_id)
        if job is None:
            return JSONResponse({"error": "작업이 없습니다", "kind": "input"}, status_code=404)
        return JSONResponse(job.summary())

    @app.get("/v1/jobs/{job_id}/events", response_model=None)
    def job_events(job_id: str, request: Request) -> StreamingResponse | JSONResponse:
        jm = jobs(request)
        if jm.get(job_id) is None:
            return JSONResponse({"error": "작업이 없습니다", "kind": "input"}, status_code=404)

        def gen() -> Iterator[str]:
            for ev in jm.iter_events(job_id):
                yield _sse(ev)

        return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})

    @app.get("/v1/jobs/{job_id}/result")
    def job_result(job_id: str, request: Request) -> JSONResponse:
        job = jobs(request).get(job_id)
        if job is None:
            return JSONResponse({"error": "작업이 없습니다", "kind": "input"}, status_code=404)
        if job.status == "failed":
            return JSONResponse({"error": job.error, "kind": "failed", "job": job.summary()}, status_code=409)
        if job.result is None:
            pending = {"error": "아직 끝나지 않았습니다", "kind": "pending", "job": job.summary()}
            return JSONResponse(pending, status_code=409)
        body = job.result.model_dump(mode="json")
        body["errors"] = list(job.result.metrics.get("errors", []))
        body["job"] = job.summary()
        return JSONResponse(body)

    # -- 묶음 검수(단계 2, 가이드 8단계). LLM 없이 동기로 돈다 --
    def _require_db_ok(request: Request) -> None:
        if runtime.db is not None and not jobs(request).db_ok():
            raise ConfigError("DB에 연결할 수 없습니다(DATABASE_URL). 묶음 검수를 저장할 수 없습니다.")

    @app.get("/v1/bundles")
    def list_bundles(limit: int = 20) -> list[dict]:
        return runtime.bundles.recent(max(1, min(limit, 200)))

    @app.get("/v1/bundles/samples")
    def bundle_samples() -> list[dict]:
        rows = []
        for path in sorted(_bundle_samples_dir(runtime.settings).glob("*.json")):
            obj = json.loads(path.read_text(encoding="utf-8"))
            gold = obj.get("gold", {})
            rows.append(
                {"bundle_id": obj["bundle_id"], "case": gold.get("case"), "entity_type": gold.get("entity_type")}
            )
        return rows

    @app.get("/v1/bundles/samples/{bundle_id}")
    def bundle_sample(bundle_id: str) -> JSONResponse:
        path = _bundle_samples_dir(runtime.settings) / f"{bundle_id}.json"
        if not path.is_file() or path.name != f"{bundle_id}.json":
            return _not_found(f"샘플 묶음이 없습니다: {bundle_id!r}")
        bundle = parse_bundle(json.loads(path.read_text(encoding="utf-8")))  # gold는 뗀다
        return JSONResponse(bundle.model_dump(mode="json"))

    @app.post("/v1/bundles/review")
    def review_bundle_endpoint(body: dict[str, Any], request: Request) -> dict[str, Any]:
        bundle: Bundle = parse_bundle(body)  # 구조 오류 → InputError → 400
        _require_db_ok(request)  # DB 불통 → 503
        items = review_bundle(bundle, runtime.dictionary)
        runtime.bundles.save(bundle, items)
        return {
            "bundle_id": bundle.bundle_id,
            "counts": {
                "confirmed": sum(1 for i in items if i.status == "confirmed"),
                "pending": sum(1 for i in items if i.status == "pending"),
            },
            "items": [_item_json(i) for i in items],
        }

    @app.get("/v1/bundles/{bundle_id}/items")
    def bundle_items(bundle_id: str) -> JSONResponse:
        items = runtime.bundles.items(bundle_id)
        if items is None:
            return _not_found(f"묶음이 없습니다: {bundle_id!r}")
        return JSONResponse([_item_json(i) for i in items])

    @app.get("/v1/bundles/{bundle_id}/pending")
    def bundle_pending(bundle_id: str) -> JSONResponse:
        items = runtime.bundles.items(bundle_id)
        if items is None:
            return _not_found(f"묶음이 없습니다: {bundle_id!r}")
        return JSONResponse([_item_json(i) for i in items if i.status == "pending"])

    @app.get("/v1/bundles/{bundle_id}")
    def bundle_detail(bundle_id: str) -> JSONResponse:
        bundle = runtime.bundles.get(bundle_id)
        if bundle is None:
            return _not_found(f"묶음이 없습니다: {bundle_id!r}")
        return JSONResponse(bundle.model_dump(mode="json"))

    @app.post("/v1/dictionary", status_code=201)
    def close_pending(req: DictionaryCloseRequest, request: Request) -> JSONResponse:
        """담당자가 확인 대기 항목을 닫으며 표기를 등록한다(ADR-010). 자동 등록은 없다."""
        bundle = runtime.bundles.get(req.bundle_id)
        items = runtime.bundles.items(req.bundle_id)
        if bundle is None or items is None:
            return _not_found(f"묶음이 없습니다: {req.bundle_id!r}")
        item = next((i for i in items if i.mention_id == req.mention_id), None)
        if item is None:
            return _not_found(f"항목이 없습니다: {req.mention_id!r}")
        if not bundle.customer_id:
            raise InputError("customer_id가 없는 묶음은 사전에 등록할 수 없습니다")
        if item.entity_id is None:
            raise InputError("대상 ID가 없는 항목은 사전에 등록할 수 없습니다")
        english = (req.english_name or item.translated_name or "").strip()
        if not english:
            raise InputError("등록할 영문 표기가 없습니다")
        _require_db_ok(request)
        first = next((e for e in item.evidence if e.valid), None)
        entry = runtime.dictionary.register(
            DictionaryEntry(
                customer_id=bundle.customer_id,
                entity_id=item.entity_id,
                entity_type=item.entity_type,
                arabic_key=normalize_key(item.arabic_name),
                arabic_name=item.arabic_name,
                english_name=english,
                evidence_document_id=first.document_id if first else None,
                evidence_segment_id=first.segment_id if first else None,
                evidence_quote=first.quote if first else None,
                verified_by=req.verified_by,
            )
        )
        return JSONResponse(entry.model_dump(mode="json"), status_code=201)

    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
    return app
