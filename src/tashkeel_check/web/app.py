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
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field

from .. import __version__
from ..analyzer import AnalyzeFn, analyzer_version, thread_safe_analyze
from ..archive.search import CompanyArchive, make_embeddings
from ..archive.store import InMemoryArchiveStore
from ..bundle import Bundle, parse_bundle, review_bundle
from ..bundle.dictionary import DOCUMENT_SCOPE, DictionaryEntry, InMemoryDictionary
from ..bundle.draft import build_draft
from ..bundle.schemas import REASON_LABELS, ReviewItem
from ..bundle.upload import bundle_from_uploads
from ..config import CONDITIONS, Settings, configure_tracing, has_openai_key
from ..dictionary_apply import name_text
from ..errors import ConfigError, InputError
from ..mcp.client import MCPClient, default_server_command
from ..mcp.records import ScopeRegistry, build_records_server, make_records_tool_factory, start_records_client
from ..mcp.tools import make_mcp_analyze_tool_factory
from ..ocr import OcrBackend, extract_text, make_backend
from ..runner import Reviewer, load_doc, make_model, model_label, split_gold
from ..text import Segment, normalize_key, segment_text, tokenize
from .archive import DbArchiveStore
from .auth import AuthError, Principal, auth_mode, current_customer
from .bundle_jobs import BundleReviewManager
from .bundles import BundleStore, DbBundleStore, DbDictionary, Dictionary, MemoryBundleStore
from .customers import CustomerStore, DbCustomerStore, MemoryCustomerStore
from .db import Database
from .jobs import NODES, JobManager
from .usage import DbUsageStore, MemoryUsageStore, UsageRecord, UsageStore

logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).parent / "static"
Who = Annotated[Principal, Depends(current_customer)]  # API 키 인증(ADR-019). /health·화면·/docs는 공개
SAMPLE_SPLIT = "dev"  # eval은 최종 평가용이라 화면에 내지 않는다
LOCAL_CUSTOMER = "local"  # 인증을 끈 서버(한 회사가 자체 배포)에서 사전을 묶는 고객(ADR-021)


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
    customers: CustomerStore
    usage: UsageStore
    ocr: OcrBackend
    archive: CompanyArchive  # 회사 문서 보관함(ADR-022)
    scopes: ScopeRegistry  # M2 회사 기록 툴의 작업별 범위 토큰
    records: MCPClient  # 회사 기록 MCP 서버(같은 프로세스, 메모리 전송)

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
    if "evidence_rule" not in settings.model_fields_set:
        # 서비스는 EXP-003에서 잰 근거 검사 v2를 쓴다. `Settings` 기본값(v1)은 골든·EXP-002에 묶여 있어 그대로 둔다
        settings = settings.model_copy(update={"evidence_rule": "v2"})
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
    bundles: BundleStore = DbBundleStore(db) if db is not None else MemoryBundleStore()
    dictionary: Dictionary = DbDictionary(db) if db is not None else InMemoryDictionary()
    customers: CustomerStore = DbCustomerStore(db) if db is not None else MemoryCustomerStore()
    usage: UsageStore = DbUsageStore(db) if db is not None else MemoryUsageStore()
    ocr = make_backend(settings)  # ocrspace인데 키가 없으면 ConfigError
    # 회사 문서 보관함과 회사 기록 MCP 서버(ADR-022). 서버는 이 Runtime의 사전·보관함을 그대로 쓴다
    embeddings, label = make_embeddings(settings.llm_backend, settings.embedding_model)
    archive = CompanyArchive(DbArchiveStore(db) if db is not None else InMemoryArchiveStore(), embeddings, label)
    scopes = ScopeRegistry()
    records = start_records_client(build_records_server(archive, dictionary, scopes))  # 실패 → ConfigError
    reviewer = Reviewer(
        model,
        settings,
        analyze_fn=fn,
        analyze_tool_factory=factory,
        records_tool_factory=make_records_tool_factory(records),
    )
    return Runtime(
        settings,
        model,
        fn,
        reviewer,
        db,
        client,
        tracing,
        bundles,
        dictionary,
        customers,
        usage,
        ocr,
        archive,
        scopes,
        records,
    )


class SegmentIn(BaseModel):
    segment_id: str
    text: str


class ReviewRequest(BaseModel):
    text: str | None = Field(None, description="빈 줄·줄 단위로 구간을 나눈다")
    segments: list[SegmentIn] | None = None
    condition: str | None = None  # 비우면 서버 설정 REVIEW_CONDITION(기본 M2, ADR-022). C1은 EXP-003에서 잰 설정
    doc_id: str | None = Field(None, description="합성 dev 문서 id. 주면 text·segments 대신 그 문서를 쓴다")


def _samples_dir(settings: Settings) -> Path:
    return settings.data_dir / "synthetic" / SAMPLE_SPLIT


def _bundle_samples_dir(settings: Settings) -> Path:
    return settings.data_dir / "synthetic" / "bundles" / SAMPLE_SPLIT


class DictionaryCloseRequest(BaseModel):
    """두 형태: 묶음 항목(bundle_id + mention_id) 또는 단일 문서 항목(job_id + token_ids, ADR-021)."""

    bundle_id: str | None = None
    mention_id: str | None = None
    job_id: str | None = None
    token_ids: list[int] | None = None
    english_name: str | None = Field(None, description="비우면 항목의 번역 표기(묶음) 또는 채택 표기(문서)를 등록한다")
    archive_hit_id: str | None = Field(None, description="보관함 제안을 확정할 때 그 구절의 hit_id(ADR-022)")
    verified_by: str = "reviewer"


def _item_json(item: ReviewItem) -> dict[str, Any]:
    body = item.model_dump(mode="json")
    body["reason_label"] = REASON_LABELS[item.reason]
    return body


def _not_found(what: str) -> JSONResponse:
    return JSONResponse({"error": what, "kind": "input"}, status_code=404)


def _bind_customer(bundle: Bundle, principal: Principal) -> Bundle:
    """인증된 요청의 묶음은 키의 고객에 묶는다. 본문이 다른 고객을 적었으면 400(ADR-019)."""
    if not principal.authenticated:
        return bundle
    if bundle.customer_id and bundle.customer_id != principal.customer_id:
        raise InputError("customer_id가 API 키의 고객과 다릅니다")
    return bundle.model_copy(update={"customer_id": principal.customer_id})


def _parse_window(start: str | None, end: str | None) -> tuple[datetime, datetime]:
    """`from`·`to`(ISO 날짜 또는 일시, to는 제외). 기본은 최근 30일."""

    def parse(v: str, what: str) -> datetime:
        try:
            d = datetime.fromisoformat(v)
        except ValueError as exc:
            raise InputError(f"{what}은(는) ISO 날짜여야 합니다: {v!r}") from exc
        return d if d.tzinfo else d.replace(tzinfo=UTC)

    now = datetime.now(UTC)
    t_end = parse(end, "to") if end else now + timedelta(minutes=1)
    t_start = parse(start, "from") if start else t_end - timedelta(days=30)
    if t_start >= t_end:
        raise InputError("from은 to보다 앞이어야 합니다")
    return t_start, t_end


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


def _service_conditions(settings: Settings) -> tuple[str, ...]:
    """서비스가 받는 조건. M2(기본, ADR-022)와 C0~C3. M1(멀티 에이전트 틀)은 MULTI_AGENT=true일 때만(ADR-019)."""
    return (*CONDITIONS, "M2", "M1") if settings.multi_agent else (*CONDITIONS, "M2")


def _check_condition(settings: Settings, condition: str) -> None:
    allowed = _service_conditions(settings)
    if condition not in allowed:
        hint = "" if settings.multi_agent else " (M1은 MULTI_AGENT=true일 때만)"
        raise InputError(f"조건은 {', '.join(allowed)} 중 하나여야 합니다{hint}: {condition!r}")


def _build_doc(rt: Runtime, req: ReviewRequest) -> tuple[dict, str]:
    """입력을 검증해 그래프 입력 문서로 만든다. 400 사유: 빈 입력, 아랍어 토큰 0개, 조건 오류, 없는 샘플."""
    _check_condition(rt.settings, req.condition or rt.settings.review_condition)
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
            runtime.reviewer,
            runtime.settings.results_dir,
            db=runtime.db,
            mcp=runtime.mcp,
            max_workers=max_workers,
            usage=runtime.usage,
            dictionary=runtime.dictionary,
            default_customer=LOCAL_CUSTOMER,
            archive=runtime.archive,
            scopes=runtime.scopes,
            records=runtime.records,
        )
        app.state.bundle_reviews = BundleReviewManager(app.state.jobs, runtime.bundles, runtime.dictionary)
        try:
            yield
        finally:
            app.state.jobs.shutdown()
            if runtime.mcp is not None:
                runtime.mcp.stop()
            runtime.records.stop()

    app = FastAPI(title="Tashkeel Check", version=__version__, lifespan=lifespan)

    @app.exception_handler(InputError)
    async def _input_error(request: Request, exc: InputError) -> JSONResponse:
        return JSONResponse({"error": str(exc), "kind": "input"}, status_code=400)

    @app.exception_handler(ConfigError)
    async def _config_error(request: Request, exc: ConfigError) -> JSONResponse:
        return JSONResponse({"error": str(exc), "kind": "config"}, status_code=503)

    @app.exception_handler(AuthError)
    async def _auth_error(request: Request, exc: AuthError) -> JSONResponse:
        return JSONResponse({"error": str(exc), "kind": "auth"}, status_code=401)

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
            "auth": auth_mode(runtime.settings, runtime.customers),
            "multi_agent": runtime.settings.multi_agent,
            "conditions": list(_service_conditions(runtime.settings)),
            "default_condition": runtime.settings.review_condition,
            "archive": {
                "store": "db" if runtime.db is not None else "memory",
                "embeddings": runtime.archive.embedding_label,
            },
            "records_mcp": runtime.records.healthy,
            "prompt_version": runtime.settings.prompt_version,
            "ocr": runtime.ocr.name,
            "dictionary_customer": (
                LOCAL_CUSTOMER if auth_mode(runtime.settings, runtime.customers) == "disabled" else None
            ),
        }

    @app.get("/v1/samples")
    def samples(who: Who) -> list[dict]:
        return _list_samples(runtime)

    @app.get("/v1/samples/{doc_id}")
    def sample(doc_id: str, who: Who) -> JSONResponse:
        doc = _load_sample(runtime, doc_id)
        if doc is None:
            return JSONResponse({"error": f"샘플 문서가 없습니다: {doc_id!r}", "kind": "input"}, status_code=404)
        doc_in, _ = split_gold(doc)
        public = {k: doc_in[k] for k in ("doc_id", "doc_type", "evidence_layout", "segments", "notice") if k in doc_in}
        return JSONResponse(public)

    @app.post("/v1/reviews", status_code=202)
    def create_review(req: ReviewRequest, request: Request, who: Who) -> dict[str, Any]:
        doc, source = _build_doc(runtime, req)
        condition = req.condition or runtime.settings.review_condition
        job = jobs(request).submit(doc, condition, source, who.scope)  # DB 불통 → ConfigError → 503
        return {"job_id": job.id, "status": job.status, "condition": job.condition, "doc_id": doc["doc_id"]}

    @app.post("/v1/extract")
    def extract_only(
        who: Who,
        file: Annotated[UploadFile, File(description="서류 파일 1개(.txt/.md/.pdf/이미지)")],
    ) -> dict[str, Any]:
        """파일 → 텍스트만(검수 없음). 텍스트 층이 없는 PDF·이미지는 OCR 백엔드로 간다(ADR-021)."""
        name = file.filename or "upload"
        ex = extract_text(file.file.read(), name, runtime.ocr, runtime.settings.upload_max_bytes)
        return {
            "filename": name,
            "text": ex.text,
            "segments": [dict(sg) for sg in ex.segments],
            "source": ex.source,
            "backend": ex.backend,
            "pages": ex.pages,
            "warnings": ex.warnings,
        }

    @app.post("/v1/reviews/upload", status_code=202)
    def create_review_from_file(
        request: Request,
        who: Who,
        file: Annotated[UploadFile, File(description="서류 파일 1개(.txt/.md/.pdf/이미지)")],
        condition: Annotated[str | None, Form()] = None,
    ) -> dict[str, Any]:
        """파일 하나를 올리면 추출 → 구간 분할 → 검수까지 한 번에(ADR-021). 결과는 `/v1/jobs/{id}/result`.
        조건을 비우면 서버 설정 REVIEW_CONDITION(기본 M2, ADR-022)을 쓴다."""
        condition = condition or runtime.settings.review_condition
        _check_condition(runtime.settings, condition)
        name = file.filename or "upload"
        ex = extract_text(file.file.read(), name, runtime.ocr, runtime.settings.upload_max_bytes)
        doc = {
            "doc_id": Path(name).stem[:64] or "upload",
            "synthetic": False,
            "segments": ex.segments,
            "meta": {"source": "upload", "filename": name, "extract": ex.source, "ocr": ex.backend, "pages": ex.pages},
        }
        job = jobs(request).submit(doc, condition, "upload", who.scope)  # DB 불통 → ConfigError → 503
        return {
            "job_id": job.id,
            "status": job.status,
            "condition": job.condition,
            "doc_id": doc["doc_id"],
            "extracted": {
                "source": ex.source,
                "backend": ex.backend,
                "pages": ex.pages,
                "n_segments": len(ex.segments),
                "warnings": ex.warnings,
            },
        }

    def _job_for(request: Request, job_id: str, who: Principal):  # type: ignore[no-untyped-def]
        job = jobs(request).get(job_id)
        if job is None or (who.authenticated and job.customer_id != who.customer_id):
            return None
        return job

    @app.get("/v1/jobs")
    def list_jobs(request: Request, who: Who, limit: int = 20) -> list[dict]:
        return jobs(request).recent(max(1, min(limit, 200)), who.scope)

    @app.get("/v1/jobs/{job_id}")
    def get_job(job_id: str, request: Request, who: Who) -> JSONResponse:
        job = _job_for(request, job_id, who)
        if job is None:
            return JSONResponse({"error": "작업이 없습니다", "kind": "input"}, status_code=404)
        return JSONResponse(job.summary())

    @app.get("/v1/jobs/{job_id}/events", response_model=None)
    def job_events(job_id: str, request: Request, who: Who) -> StreamingResponse | JSONResponse:
        jm = jobs(request)
        if _job_for(request, job_id, who) is None:
            return JSONResponse({"error": "작업이 없습니다", "kind": "input"}, status_code=404)

        def gen() -> Iterator[str]:
            for ev in jm.iter_events(job_id):
                yield _sse(ev)

        return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})

    @app.get("/v1/jobs/{job_id}/result")
    def job_result(job_id: str, request: Request, who: Who) -> JSONResponse:
        job = _job_for(request, job_id, who)
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
        body["dictionary"] = list(job.dictionary)  # 회사 사전 덧씌움(ADR-021)
        body["archive"] = list(job.archive)  # 보관함 제안 덧씌움(ADR-022)
        body["tokens"] = [dict(t) for t in tokenize(job.doc["segments"])]  # 화면이 토큰 위치로 이름을 표시한다
        body["dictionary_customer"] = jobs(request).dictionary_scope(job.customer_id)
        return JSONResponse(body)

    # -- 묶음 검수(단계 2, 가이드 8단계). LLM 없이 동기로 돈다 --
    def _require_db_ok(request: Request) -> None:
        if runtime.db is not None and not jobs(request).db_ok():
            raise ConfigError("DB에 연결할 수 없습니다(DATABASE_URL). 묶음 검수를 저장할 수 없습니다.")

    @app.get("/v1/bundles")
    def list_bundles(who: Who, limit: int = 20) -> list[dict]:
        return runtime.bundles.recent(max(1, min(limit, 200)), who.scope)

    @app.get("/v1/usage")
    def usage_summary(
        who: Who,
        from_: Annotated[str | None, Query(alias="from")] = None,
        to: str | None = None,
    ) -> dict[str, Any]:
        """고객의 사용량(작업 수·토큰·구간 수)을 기간으로 본다. 인증을 끈 경우 전체."""
        start, end = _parse_window(from_, to)
        body = runtime.usage.summary(who.scope, start, end)
        body["customer_id"] = who.scope
        return body

    @app.get("/v1/bundles/samples")
    def bundle_samples(who: Who) -> list[dict]:
        rows = []
        for path in sorted(_bundle_samples_dir(runtime.settings).glob("*.json")):
            obj = json.loads(path.read_text(encoding="utf-8"))
            gold = obj.get("gold", {})
            rows.append(
                {"bundle_id": obj["bundle_id"], "case": gold.get("case"), "entity_type": gold.get("entity_type")}
            )
        return rows

    @app.get("/v1/bundles/samples/{bundle_id}")
    def bundle_sample(bundle_id: str, who: Who) -> JSONResponse:
        path = _bundle_samples_dir(runtime.settings) / f"{bundle_id}.json"
        if not path.is_file() or path.name != f"{bundle_id}.json":
            return _not_found(f"샘플 묶음이 없습니다: {bundle_id!r}")
        bundle = parse_bundle(json.loads(path.read_text(encoding="utf-8")))  # gold는 뗀다
        return JSONResponse(bundle.model_dump(mode="json"))

    def _review_and_save(bundle: Bundle, request: Request, who: Principal) -> dict[str, Any]:
        bundle = _bind_customer(bundle, who)
        _require_db_ok(request)  # DB 불통 → 503
        items = review_bundle(bundle, runtime.dictionary)
        runtime.bundles.save(bundle, items)
        runtime.usage.record(
            UsageRecord(
                customer_id=who.scope,
                kind="bundle_label",
                bundle_id=bundle.bundle_id,
                n_segments=sum(len(d.segments) for d in bundle.documents),
            )
        )
        return {
            "bundle_id": bundle.bundle_id,
            "documents": [
                {"document_id": d.document_id, "document_type": d.document_type, "segments": len(d.segments)}
                for d in bundle.documents
            ],
            "counts": {
                "confirmed": sum(1 for i in items if i.status == "confirmed"),
                "pending": sum(1 for i in items if i.status == "pending"),
            },
            "items": [_item_json(i) for i in items],
        }

    @app.post("/v1/bundles/review")
    def review_bundle_endpoint(body: dict[str, Any], request: Request, who: Who) -> dict[str, Any]:
        bundle: Bundle = parse_bundle(body)  # 구조 오류 → InputError → 400
        return _review_and_save(bundle, request, who)

    @app.post("/v1/bundles", status_code=201)
    def upload_bundle(
        request: Request,
        who: Who,
        files: Annotated[list[UploadFile], File(description="묶음 JSON 하나, 또는 서류 파일(.json/.txt/.md) 여러 개")],
        bundle_id: Annotated[str | None, Form()] = None,
        customer_id: Annotated[str | None, Form()] = None,
        document_type: Annotated[str, Form()] = "document",
        entities: Annotated[str | None, Form(description='{"대상 ID": "person|organization|other"} JSON')] = None,
    ) -> dict[str, Any]:
        """파일 업로드로 묶음을 만들고 바로 라벨 경로로 검수한다. LLM 경로는 이어서 `/reviews`를 부른다."""
        uploads = [(f.filename or f"file_{i}", f.file.read()) for i, f in enumerate(files, start=1)]
        bundle = bundle_from_uploads(uploads, bundle_id, customer_id, document_type, entities)  # 오류 → 400
        return _review_and_save(bundle, request, who)

    @app.post("/v1/bundles/draft")
    def draft_bundle(
        request: Request,
        who: Who,
        files: Annotated[list[UploadFile], File(description="서류 파일(.json/.txt/.md) 여러 개 또는 묶음 JSON 하나")],
        bundle_id: Annotated[str | None, Form()] = None,
        customer_id: Annotated[str | None, Form()] = None,
        document_type: Annotated[str, Form()] = "document",
    ) -> dict[str, Any]:
        """업로드 초안(ADR-019): 이름 칸과 같은 대상 제안만 돌려준다. 저장하지 않고 entity_id도 넣지 않는다."""
        uploads = [(f.filename or f"file_{i}", f.file.read()) for i, f in enumerate(files, start=1)]
        bundle = _bind_customer(bundle_from_uploads(uploads, bundle_id, customer_id, document_type), who)
        return build_draft(bundle)

    @app.get("/v1/bundles/{bundle_id}/items")
    def bundle_items(bundle_id: str, who: Who) -> JSONResponse:
        items = runtime.bundles.items(bundle_id, who.scope)
        if items is None:
            return _not_found(f"묶음이 없습니다: {bundle_id!r}")
        return JSONResponse([_item_json(i) for i in items])

    @app.get("/v1/bundles/{bundle_id}/pending")
    def bundle_pending(bundle_id: str, who: Who) -> JSONResponse:
        items = runtime.bundles.items(bundle_id, who.scope)
        if items is None:
            return _not_found(f"묶음이 없습니다: {bundle_id!r}")
        return JSONResponse([_item_json(i) for i in items if i.status == "pending"])

    def bundle_reviews(request: Request) -> BundleReviewManager:
        brm: BundleReviewManager = request.app.state.bundle_reviews
        return brm

    @app.post("/v1/bundles/{bundle_id}/reviews", status_code=202)
    def start_bundle_review(bundle_id: str, request: Request, who: Who, condition: str = "C1") -> JSONResponse:
        if condition == "M2":  # 보관함은 이름이 같다고 잇는다. 묶음 경로는 대상 ID로만 잇는다(ADR-018)
            raise InputError("묶음 검수는 M2를 받지 않습니다(C0~C3, MULTI_AGENT=true면 M1)")
        """라벨 칸이 없는 문장의 고유명사를 LLM(C1~C3, 켜면 M1)으로 뽑아 묶음 판정에 합류시킨다. 서류마다 작업 하나."""
        _check_condition(runtime.settings, condition)
        bundle = runtime.bundles.get(bundle_id, who.scope)
        if bundle is None:
            return _not_found(f"묶음이 없습니다: {bundle_id!r}")
        brm = bundle_reviews(request)
        rec = brm.start(bundle, condition)  # DB 불통 → ConfigError → 503
        return JSONResponse(brm.summary(rec), status_code=202)

    def _review_for(request: Request, bundle_id: str, review_id: str, who: Principal):  # type: ignore[no-untyped-def]
        rec = bundle_reviews(request).get(review_id)
        if rec is None or rec.bundle.bundle_id != bundle_id:
            return None
        if who.authenticated and rec.bundle.customer_id != who.customer_id:
            return None
        return rec

    @app.get("/v1/bundles/{bundle_id}/reviews/{review_id}")
    def get_bundle_review(bundle_id: str, review_id: str, request: Request, who: Who) -> JSONResponse:
        brm = bundle_reviews(request)
        rec = _review_for(request, bundle_id, review_id, who)
        if rec is None:
            return _not_found(f"묶음 검수가 없습니다: {review_id!r}")
        body = brm.summary(rec)
        if rec.items is not None:
            body["items"] = [_item_json(i) for i in rec.items]
            body["counts"] = {
                "confirmed": sum(1 for i in rec.items if i.status == "confirmed"),
                "pending": sum(1 for i in rec.items if i.status == "pending"),
            }
        return JSONResponse(body)

    @app.get("/v1/bundles/{bundle_id}/reviews/{review_id}/events", response_model=None)
    def bundle_review_events(
        bundle_id: str, review_id: str, request: Request, who: Who
    ) -> StreamingResponse | JSONResponse:
        """묶음 단위 SSE: start → 서류별 작업 이벤트 → done. 끝난 검수는 누적 이벤트를 재생하고 바로 done을 낸다."""
        brm = bundle_reviews(request)
        if _review_for(request, bundle_id, review_id, who) is None:
            return _not_found(f"묶음 검수가 없습니다: {review_id!r}")

        def gen() -> Iterator[str]:
            for ev in brm.iter_events(review_id):
                yield _sse(ev)

        return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})

    @app.get("/v1/bundles/{bundle_id}")
    def bundle_detail(bundle_id: str, who: Who) -> JSONResponse:
        bundle = runtime.bundles.get(bundle_id, who.scope)
        if bundle is None:
            return _not_found(f"묶음이 없습니다: {bundle_id!r}")
        return JSONResponse(bundle.model_dump(mode="json"))

    def _dictionary_customer(request: Request, who: Principal) -> str:
        scope = jobs(request).dictionary_scope(who.scope)
        if not scope:
            raise InputError("사전을 쓸 고객이 없습니다")
        return scope

    def _close_bundle_item(req: DictionaryCloseRequest, request: Request, who: Who) -> JSONResponse:
        assert req.bundle_id is not None and req.mention_id is not None
        bundle = runtime.bundles.get(req.bundle_id, who.scope)
        items = runtime.bundles.items(req.bundle_id, who.scope)
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

    def _close_document_item(req: DictionaryCloseRequest, request: Request, who: Who) -> JSONResponse:
        """단일 문서 항목을 사람이 확정해 회사 사전에 넣는다(ADR-021). 키는 고객 + "*" + 정규화 아랍어."""
        assert req.job_id is not None
        job = _job_for(request, req.job_id, who)
        if job is None:
            return _not_found("작업이 없습니다")
        if job.result is None:
            raise InputError("아직 끝나지 않은 작업입니다")
        wanted = list(req.token_ids or [])
        if not wanted:
            raise InputError("token_ids가 비어 있습니다")
        item = next((i for i in job.result.items if i.type == "proper_noun" and list(i.token_ids) == wanted), None)
        if item is None:
            raise InputError(f"작업에 그 토큰의 이름 항목이 없습니다: {wanted}")
        suggestion = None
        if req.archive_hit_id:  # 보관함 제안을 확정한다. 근거 서류는 그 지난 서류로 남긴다(ADR-022)
            overlay = next((o for o in job.archive if o["token_ids"] == wanted), None)
            suggestion = next(
                (g for g in (overlay or {}).get("suggestions", []) if g["hit_id"] == req.archive_hit_id), None
            )
            if suggestion is None:
                raise InputError(f"그 이름의 보관함 제안이 없습니다: {req.archive_hit_id!r}")
        english = (req.english_name or (suggestion or {}).get("spelling") or item.adopted or "").strip()
        if not english:
            raise InputError("등록할 영문 표기를 입력하세요")
        customer = _dictionary_customer(request, who)
        _require_db_ok(request)
        ev = item.evidence if item.final_decision == "evidence_adopt" else None
        arabic = name_text(item)
        if suggestion is not None:
            evidence_doc, evidence_seg, evidence_quote = (
                suggestion["document_id"],
                suggestion["segment_id"],
                suggestion["quote"],
            )
        else:
            evidence_doc = job.document_id or job.doc.get("doc_id")
            evidence_seg = ev.segment_id if ev else item.segment_id
            evidence_quote = ev.quote if ev else None
        entry = runtime.dictionary.register(
            DictionaryEntry(
                customer_id=customer,
                entity_id=DOCUMENT_SCOPE,
                entity_type="other",
                arabic_key=normalize_key(arabic),
                arabic_name=arabic,
                english_name=english,
                evidence_document_id=evidence_doc,
                evidence_segment_id=evidence_seg,
                evidence_quote=evidence_quote,
                verified_by=req.verified_by,
            )
        )
        # 같은 작업의 덧씌움도 바로 갱신해 결과 페이지가 다시 읽을 때 반영된다. 사전이 보관함 제안을 이긴다
        job.archive = [o for o in job.archive if o["token_ids"] != wanted]
        job.dictionary = [o for o in job.dictionary if o["token_ids"] != wanted] + [
            {
                "item_index": item.item_index,
                "token_ids": wanted,
                "arabic": arabic,
                "arabic_key": entry.arabic_key,
                "status": "dictionary_adopt",
                "english": english,
                "entry_id": entry.id,
                "document_spelling": item.adopted,
                "detail": "방금 확정" if suggestion is None else f"보관함 제안 확정({suggestion['document_label']})",
            }
        ]
        return JSONResponse(entry.model_dump(mode="json"), status_code=201)

    @app.post("/v1/dictionary", status_code=201)
    def close_pending(req: DictionaryCloseRequest, request: Request, who: Who) -> JSONResponse:
        """담당자가 확인 대기 항목을 닫으며 표기를 등록한다(ADR-010). 자동 등록은 없다."""
        if req.job_id:
            return _close_document_item(req, request, who)
        if req.bundle_id and req.mention_id:
            return _close_bundle_item(req, request, who)
        raise InputError("bundle_id + mention_id 또는 job_id + token_ids가 필요합니다")

    @app.get("/v1/dictionary")
    def list_dictionary(request: Request, who: Who, limit: int = 200) -> dict[str, Any]:
        customer = _dictionary_customer(request, who)
        rows = runtime.dictionary.list_entries(customer, max(1, min(limit, 1000)))
        return {"customer_id": customer, "entries": [e.model_dump(mode="json") for e in rows]}

    @app.delete("/v1/dictionary/{entry_id}")
    def delete_dictionary(entry_id: str, request: Request, who: Who) -> JSONResponse:
        customer = _dictionary_customer(request, who)
        _require_db_ok(request)
        if not runtime.dictionary.delete(entry_id, customer):
            return _not_found(f"사전 항목이 없습니다: {entry_id!r}")
        for job in jobs(request).all_jobs():
            job.dictionary = [o for o in job.dictionary if o.get("entry_id") != entry_id]
        return JSONResponse({"deleted": entry_id})

    # -- 회사 문서 보관함(ADR-022). 업로드·붙여넣기 서류가 검수를 마치면 들어간다 --
    @app.get("/v1/archive")
    def list_archive(request: Request, who: Who, limit: int = 200) -> dict[str, Any]:
        customer = _dictionary_customer(request, who)
        rows = runtime.archive.list_documents(customer, max(1, min(limit, 1000)))
        return {
            "customer_id": customer,
            "embeddings": runtime.archive.embedding_label,
            "documents": [r.model_dump(mode="json") for r in rows],
        }

    @app.delete("/v1/archive/{document_id}")
    def delete_archive(document_id: str, request: Request, who: Who) -> JSONResponse:
        customer = _dictionary_customer(request, who)
        _require_db_ok(request)
        if not runtime.archive.delete_document(customer, document_id):
            return _not_found(f"보관함에 그 서류가 없습니다: {document_id!r}")
        for job in jobs(request).all_jobs():  # 그 서류를 출처로 한 제안은 화면에서 바로 내린다
            kept = []
            for o in job.archive:
                rest = [g for g in o["suggestions"] if g["document_id"] != document_id]
                if rest:
                    kept.append({**o, "suggestions": rest})
            job.archive = kept
        return JSONResponse({"deleted": document_id})

    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
    return app
