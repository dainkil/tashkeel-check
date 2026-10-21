"""문서 하나를 한 조건으로 실행한다. LangSmith 추적 메타데이터도 여기서 붙인다."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree

from . import __version__
from .analyzer import AnalyzeFn, analyzer_version
from .config import Settings, has_openai_key, tracing_enabled
from .errors import ConfigError
from .fake import FakeAgentModel, Responder
from .graph import AnalyzeToolFactory, ToolFactory, build_graph
from .prompts import prompt_hash
from .results import ReviewResult
from .romanize import MATCHER_VERSION

TRACE_KEYS = [
    "n_ambiguous_tokens",
    "decisions",
    "n_unprocessed",
    "n_unprocessed_names",
    "n_proper_noun_tokens_without_analyzer_candidates",
    "n_evidence_failed",
    "n_over_flag_tokens",
    "silent_rate",
    "unsupported_adopt_rate",
    "hold_rate",
    "hold_candidate_hit_rate",
    "usage",
    "attempts",
]


def load_doc(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def split_gold(doc: dict) -> tuple[dict, dict | None]:
    """gold는 그래프의 대조 단계에만 넘긴다. 프롬프트에 쓰는 입력에서는 뗀다."""
    doc_in = {k: v for k, v in doc.items() if k != "gold"}
    return doc_in, doc.get("gold")


def make_model(settings: Settings, fake: bool = False, responder: Responder | None = None) -> BaseChatModel:
    if fake:
        return FakeAgentModel(responder=responder)
    if not has_openai_key():
        raise ConfigError("OPENAI_API_KEY가 없습니다. .env에 키를 넣거나 --fake(연습 모드)로 실행하세요.")
    kwargs: dict[str, Any] = {}
    if settings.temperature is not None:
        kwargs["temperature"] = settings.temperature
    return init_chat_model(settings.model, **kwargs)


def model_label(model: BaseChatModel, settings: Settings) -> str:
    if isinstance(model, FakeAgentModel):
        return "fake-agent"
    return getattr(model, "model_name", None) or getattr(model, "model", None) or settings.model


NodeCallback = Callable[[str, dict], None]


class Reviewer:
    """모델·설정·추가 툴을 묶어 그래프를 한 번만 빌드하고, 문서마다 다시 쓴다.

    실행 상태는 invoke마다 새로 만들므로 같은 Reviewer로 여러 문서를 돌려도 결과가 섞이지 않는다.
    서비스(단계 1.5)는 기동할 때 하나를 만들어 둔다.
    analyze_tool_factory는 C2의 analyze_tokens를 MCP 툴로 바꿀 때만 준다.
    """

    def __init__(
        self,
        model: BaseChatModel,
        settings: Settings,
        analyze_fn: AnalyzeFn | None = None,
        extra_tool_factories: list[ToolFactory] | None = None,
        analyze_tool_factory: AnalyzeToolFactory | None = None,
    ) -> None:
        self.model = model
        self.settings = settings
        self.bundle_search = bool(extra_tool_factories)
        self.graph = build_graph(model, settings, analyze_fn, extra_tool_factories, analyze_tool_factory)

    def _meta(self, doc: dict, condition: str, repeat: int) -> dict:
        return {
            "doc_id": doc["doc_id"],
            "condition": condition,
            "repeat": repeat,
            "model": model_label(self.model, self.settings),
            "model_setting": self.settings.model,
            "temperature": self.settings.temperature,
            "prompt_version": self.settings.prompt_version,
            "prompt_hash": prompt_hash(condition, self.settings.prompt_version),
            "matcher_version": MATCHER_VERSION,
            "analyzer": analyzer_version(),
            "package_version": __version__,
            "synthetic": bool(doc.get("synthetic")),
            "doc_meta": doc.get("meta", {}),
            "bundle_search": self.bundle_search,
            "tracing": tracing_enabled(),
            "high_confidence": self.settings.high_confidence,
        }

    @traceable(
        name="tashkeel_run",
        run_type="chain",
        process_inputs=lambda inputs: {k: v for k, v in inputs.items() if k != "self"},
    )
    def run(
        self,
        doc: dict,
        condition: str,
        out_dir: str | Path | None = None,
        repeat: int = 0,
        on_node: NodeCallback | None = None,
    ) -> ReviewResult:
        """on_node(노드 이름, 그 노드의 갱신분)는 노드가 끝날 때마다 불린다(단계 1.5 진행 표시). 결과는 같다."""
        doc_in, gold = split_gold(doc)
        meta = self._meta(doc, condition, repeat)
        state = {
            "doc_id": doc["doc_id"],
            "condition": condition,
            "segments": doc_in["segments"],
            "gold": gold,
            "out_dir": str(out_dir) if out_dir else None,
            "meta": meta,
        }
        config: RunnableConfig = {
            "recursion_limit": 50,
            "run_name": f"{doc['doc_id']}:{condition}:r{repeat}",
            "tags": [condition, doc["doc_id"]],
            "metadata": {k: meta[k] for k in ("doc_id", "condition", "repeat", "model", "prompt_hash")},
        }
        if on_node is None:
            final = self.graph.invoke(state, config=config)
        else:
            final = {}
            for update in self.graph.stream(state, config=config, stream_mode="updates"):
                for node, delta in update.items():
                    on_node(node, delta)
                    final.update(delta)
        result: ReviewResult = final["result"]
        run_tree = get_current_run_tree()
        if run_tree is not None:  # 추적이 켜져 있을 때만
            run_tree.add_metadata({f"m_{k}": result.metrics.get(k) for k in TRACE_KEYS})
        return result


def run_document(
    doc: dict,
    condition: str,
    model: BaseChatModel,
    settings: Settings,
    out_dir: str | Path | None = None,
    repeat: int = 0,
    analyze_fn: AnalyzeFn | None = None,
    extra_tool_factories: list[ToolFactory] | None = None,
) -> ReviewResult:
    """한 번 실행할 때 쓰는 편의 함수. 여러 문서를 돌릴 때는 Reviewer를 한 번 만들어 다시 쓴다."""
    reviewer = Reviewer(model, settings, analyze_fn, extra_tool_factories)
    return reviewer.run(doc, condition, out_dir=out_dir, repeat=repeat)
