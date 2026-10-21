"""명령줄 진입점: `uv run tashkeel <명령>`.

종료 코드: 0 성공, 1 실행 동의 필요(exp002·exp003), 2 입력 오류(InputError, 쓸 수 없는 옵션 조합),
3 설정·환경 오류(ConfigError), 4 중간 정지(exp002·exp003, --resume으로 이어서 실행할 수 있다).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from types import ModuleType

from .config import CONDITIONS, Settings, configure_tracing, load_settings
from .errors import ConfigError, InputError, TashkeelError


def _cmd_run(args: argparse.Namespace, settings: Settings) -> int:
    from .runner import load_doc, make_model, run_document

    tracing = configure_tracing(settings)
    doc = load_doc(args.doc)
    factories = None
    if args.bundle:
        if not settings.enable_bundle_search:
            print("묶음 검색은 단계 2 틀입니다. 쓰려면 .env에 ENABLE_BUNDLE_SEARCH=true를 넣으세요.", file=sys.stderr)
            return 2
        from .rag import BundleIndex, make_bundle_search_tool

        print("[주의] 묶음 검색은 단계 2 틀입니다. 이 결과는 C0~C3 비교에 쓰지 않습니다.", file=sys.stderr)
        factories = [make_bundle_search_tool(BundleIndex.from_dir(args.bundle, parent_size=800))]
    conditions = CONDITIONS if args.condition == "all" else (args.condition,)
    for cond in conditions:
        out = Path(args.out) if args.out else settings.results_dir / "debug" / doc["doc_id"] / cond
        if args.out and len(conditions) > 1:
            out = out / cond
        result = run_document(
            doc,
            cond,
            make_model(settings, fake=args.fake),
            settings,
            out_dir=out,
            repeat=args.repeat,
            extra_tool_factories=factories,
        )
        m = result.metrics
        print(
            json.dumps(
                {
                    "condition": cond,
                    "out": str(out),
                    "valid_output": m["valid_output"],
                    "attempts": m["attempts"],
                    "n_ambiguous_tokens": m.get("n_ambiguous_tokens"),
                    "n_unprocessed_names": m.get("n_unprocessed_names"),
                    "n_unprocessed_ambiguous_words": m.get("n_unprocessed_ambiguous_words"),
                    "silent_rate": m.get("silent_rate"),
                    "hold_rate": m.get("hold_rate"),
                    "tracing": tracing,
                    "mode": "practice (fake model)" if args.fake else settings.model,
                },
                ensure_ascii=False,
            )
        )
    return 0


def _cmd_fetch(args: argparse.Namespace, settings: Settings) -> int:
    from .data.wikidata import build_name_pool, fetch

    # --pool-only: 저장된 스냅숏으로 이름 풀만 다시 만든다(정렬 규칙이 바뀌었을 때, 재조회 없이)
    snap = Path(args.out) / "gcc_persons.json" if args.pool_only else fetch(args.out, endpoint=args.endpoint)
    pool = build_name_pool(snap, Path(args.out) / "name_tokens.json")
    print(f"snapshot: {snap}\nname pool: {pool}")
    return 0


def _cmd_synthetic(args: argparse.Namespace, settings: Settings) -> int:
    from .data.synthetic import generate, make_sample_bundle

    dev = generate(args.pool, args.out, "dev", args.dev or settings.dev_docs, seed=1001)
    ev = generate(args.pool, args.out, "eval", args.eval or settings.eval_docs, seed=2002)
    bundle = make_sample_bundle(dev[0], settings.data_dir / "bundles" / "sample")
    print(f"dev {len(dev)}, eval {len(ev)} docs → {args.out}; sample bundle: {[p.name for p in bundle]}")
    return 0


def _cmd_make_bundles(args: argparse.Namespace, settings: Settings) -> int:
    from .data.bundles import generate_bundles

    made = []
    for split in ("dev", "eval"):
        made += generate_bundles(Path(args.synthetic) / split / f"{split}_001.json", args.out, split)
    print(f"{len(made)} bundles → {args.out}")
    return 0


def _cmd_bundle_search(args: argparse.Namespace, settings: Settings) -> int:
    from .rag import BundleIndex

    index = BundleIndex.from_dir(args.bundle)
    print(f"embeddings: {index.embedding_label}", file=sys.stderr)
    for hit in index.search(args.arabic, args.romanized or []):
        print(json.dumps(hit.to_dict(), ensure_ascii=False))
    return 0


def _cmd_exp001(args: argparse.Namespace, settings: Settings) -> int:
    from .experiments import exp001

    path = exp001.run(
        args.snapshot,
        args.split,
        args.out,
        coverage_threshold=settings.coverage_threshold,
        dev_keys_path=args.dev_keys or None,
    )
    print(path)
    return 0


# 실험 명령 → 기본 문서 폴더(data_dir 아래). 두 실험은 같은 실행 장치(experiments/harness.py)를 쓴다
EXPERIMENT_DOCS = {"exp002": "synthetic", "exp003": "synthetic-hard"}


def _experiment(cmd: str) -> ModuleType:
    from .experiments import exp002, exp003

    return {"exp002": exp002, "exp003": exp003}[cmd]


def _cmd_experiment(args: argparse.Namespace, settings: Settings) -> int:
    from .runner import make_model

    exp = _experiment(args.cmd)
    configure_tracing(settings)
    root = settings.results_dir / args.cmd / args.split
    run_dir, docs, limit, repeats = None, args.docs, args.limit, args.repeats
    if args.workers < 1:
        print("--workers는 1 이상이어야 합니다.", file=sys.stderr)
        return 2
    if args.finalize and args.resume is None:
        print("--finalize는 --resume과 함께 씁니다.", file=sys.stderr)
        return 2
    if args.resume is not None:
        run_dir = exp.latest_run_dir(root) if args.resume == "latest" else Path(args.resume)
        if run_dir is None:
            print(f"이어서 실행할 실행 폴더가 없습니다: {root}", file=sys.stderr)
            return 2
        if args.finalize:
            return _print_summary(exp.write_summary(run_dir))
        plan = exp.load_plan(run_dir)  # 옵션을 주지 않으면 처음 정한 값을 쓴다. 주면 plan.json과 비교한다
        docs, limit, repeats = docs or plan["docs_dir"], limit or len(plan["docs"]), repeats or plan["repeats"]
        if (docs, limit, repeats) != (plan["docs_dir"], len(plan["docs"]), plan["repeats"]):
            print(f"처음 정한 문서·규모와 다릅니다: {run_dir / exp.PLAN_FILE}", file=sys.stderr)
            return 2
    docs_dir = Path(docs or settings.data_dir / EXPERIMENT_DOCS[args.cmd] / args.split)
    n_docs = len(sorted(docs_dir.glob("*.json"))[:limit])
    repeats = repeats or settings.repeats
    n_runs = len(CONDITIONS) * n_docs * repeats
    n_left = n_runs - (len(exp.done_runs(exp.read_ledger(run_dir))) if run_dir else 0)
    if args.fake and args.split != "dev":
        print("연습 모드(--fake)는 dev 문서에만 씁니다. 평가 문서는 실제 실행에 한 번만 씁니다.", file=sys.stderr)
        return 2
    if not args.fake and not args.yes:
        print(
            f"실행 계획: 조건 {len(CONDITIONS)} × 문서 {n_docs} × 반복 {repeats} = {n_runs}회 중 남은 {n_left}회, "
            f"동시 {args.workers}개, 모델 {settings.model}.\n비용이 듭니다. 실행하려면 --yes를 붙이세요."
        )
        return 1
    status = exp.run(
        docs_dir,
        root,
        lambda: make_model(settings, fake=args.fake),
        settings,
        repeats=repeats,
        limit=limit,
        run_dir=run_dir,
        workers=args.workers,
        max_runs=args.max_runs,
        token_budget=args.token_budget,
    )
    if status.summary_path is None:
        label = exp.PAUSE_LABELS.get(status.paused_reason or "", status.paused_reason)
        again = "--fake" if args.fake else "--yes"
        print(f"중간 정지({label}): {status.done}/{status.planned}회 완료. 기록: {status.run_dir}")
        print(
            f"이어서 실행: uv run tashkeel {args.cmd} --split {args.split} --resume {status.run_dir} "
            f"--workers {args.workers} {again}"
        )
        return 4
    return _print_summary(status.summary_path)


def _print_summary(path: Path) -> int:
    report = json.loads(path.read_text(encoding="utf-8"))
    print(path)
    print(json.dumps({k: report["verdict"].get(k) for k in ("decision", "reason")}, ensure_ascii=False))
    if not report.get("complete", True):
        print(f"[주의] 부분 결과: {report['n_runs_done']}/{report['n_runs_planned']}회", file=sys.stderr)
    return 0


def _status_run_dir(args: argparse.Namespace, settings: Settings, cmd: str) -> Path | None:
    root = settings.results_dir / cmd / args.split
    run_dir = Path(args.dir) if args.dir else _experiment(cmd).latest_run_dir(root)
    if run_dir is None:
        print(f"실행 기록이 없습니다: {root}", file=sys.stderr)
    return run_dir


def _cmd_experiment_status(args: argparse.Namespace, settings: Settings) -> int:
    cmd = args.cmd.removesuffix("-status")
    run_dir = _status_run_dir(args, settings, cmd)
    if run_dir is None:
        return 2
    exp = _experiment(cmd)
    s = exp.status(run_dir, settings)
    print(json.dumps(s, ensure_ascii=False) if args.json else exp.format_status(s))
    return 0


def _cmd_exp003_errors(args: argparse.Namespace, settings: Settings) -> int:
    from .experiments import exp003

    run_dir = _status_run_dir(args, settings, "exp003")
    if run_dir is None:
        return 2
    print(exp003.export_errors(run_dir, n_correct_sample=args.sample))
    return 0


def _cmd_exp003_rescore(args: argparse.Namespace, settings: Settings) -> int:
    from .experiments import exp003

    run_dir = _status_run_dir(args, settings, "exp003")
    if run_dir is None:
        return 2
    print(exp003.rescore(run_dir))
    return 0


def _cmd_synthetic_hard(args: argparse.Namespace, settings: Settings) -> int:
    from .data.synthetic_hard import generate

    out = Path(args.out) / args.split
    if any(out.glob("*.json")) and not args.overwrite:
        # eval은 조건 비교에 한 번만 쓰므로 한 번만 만든다. dev를 다시 만들 때만 --overwrite를 쓴다
        print(f"이미 문서가 있습니다: {out}. 다시 만들려면 --overwrite를 붙이세요.", file=sys.stderr)
        return 2
    paths, report = generate(args.pool, args.out, args.split, n=args.n)
    print(
        json.dumps(
            {"docs": len(paths), "out": str(out), **{k: v for k, v in report.items() if k != "quota"}},
            ensure_ascii=False,
        )
    )
    return 0


def _cmd_inspect_gold(args: argparse.Namespace, settings: Settings) -> int:
    from .data.synthetic_hard import describe

    paths = [Path(args.doc)] if args.doc else sorted((Path(args.dir) / args.split).glob("*.json"))
    shown = 0
    for path in paths:
        doc = json.loads(path.read_text(encoding="utf-8"))
        if args.case and args.case not in doc.get("case_types", []):
            continue
        print(describe(doc) + "\n")
        shown += 1
        if shown >= args.n:
            break
    if not shown:
        print("조건에 맞는 문서가 없습니다.", file=sys.stderr)
        return 2
    return 0


def _cmd_serve(args: argparse.Namespace, settings: Settings) -> int:
    """단계 1.5 서비스. 구성(모델·분석기·DB·MCP)을 먼저 만들어 실패하면 기동하지 않는다(종료 코드 3)."""
    import uvicorn

    from .web.app import build_runtime, create_app

    runtime = build_runtime(settings)
    host = args.host or settings.web_host
    port = args.port or settings.web_port
    print(
        f"모델 {runtime.backend}, DB {'있음' if runtime.db else '없음'}, MCP {'켬' if runtime.mcp else '끔'} → "
        f"http://{host}:{port}  (API 문서 /docs, 상태 /health)",
        file=sys.stderr,
    )
    uvicorn.run(create_app(runtime), host=host, port=port, log_level="info")
    return 0


def _parser(settings: Settings) -> argparse.ArgumentParser:
    data, results = settings.data_dir, settings.results_dir
    parser = argparse.ArgumentParser(prog="tashkeel", description="아랍어 문서 모호성 은폐 측정 장치")
    parser.add_argument("-v", "--verbose", action="store_true", help="디버그 로그까지 낸다")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run", help="문서 하나를 실행해 JSON·CSV를 만든다")
    p.add_argument("--doc", required=True)
    p.add_argument("--condition", default="C2", choices=[*CONDITIONS, "all"])
    p.add_argument("--fake", action="store_true", help="API 키 없이 연습 모드(가짜 모델)")
    p.add_argument("--out")
    p.add_argument("--repeat", type=int, default=0)
    p.add_argument("--bundle", help="단계 2 틀: 참고 자료 묶음 폴더를 붙여 search_bundle 툴을 켠다")
    p.set_defaults(func=_cmd_run)

    p = sub.add_parser("fetch-wikidata", help="Wikidata 걸프 인명 스냅숏과 이름 풀을 만든다")
    p.add_argument("--out", default=str(data / "wikidata"))
    p.add_argument(
        "--endpoint", choices=["wdqs", "qlever"], default="wdqs", help="wdqs: Wikidata 공식, qlever: 공개 미러"
    )
    p.add_argument("--pool-only", action="store_true", help="조회하지 않고 저장된 스냅숏으로 이름 풀만 다시 만든다")
    p.set_defaults(func=_cmd_fetch)

    p = sub.add_parser("make-synthetic", help="합성 문서(dev·eval)와 샘플 묶음을 만든다")
    p.add_argument("--pool", default=str(data / "wikidata" / "name_tokens.json"))
    p.add_argument("--out", default=str(data / "synthetic"))
    p.add_argument("--dev", type=int)
    p.add_argument("--eval", type=int)
    p.set_defaults(func=_cmd_synthetic)

    p = sub.add_parser("make-synthetic-hard", help="어려운 합성 문서(synthetic-hard)와 정답(gold 형식 2)을 만든다")
    p.add_argument("--split", choices=["dev", "eval"], required=True)
    p.add_argument("--pool", default=str(data / "wikidata" / "name_tokens.json"))
    p.add_argument("--out", default=str(data / "synthetic-hard"))
    p.add_argument("--n", type=int, help="문서 수(기본 dev 20, eval 70)")
    p.add_argument("--overwrite", action="store_true", help="이미 있는 문서를 덮어쓴다(eval에는 쓰지 않는다)")
    p.set_defaults(func=_cmd_synthetic_hard)

    p = sub.add_parser("inspect-gold", help="synthetic-hard 문서의 구간별 정답(기대 처분·유형)을 사람이 읽게 보인다")
    p.add_argument("--doc", help="문서 파일 하나")
    p.add_argument("--dir", default=str(data / "synthetic-hard"))
    p.add_argument("--split", choices=["dev", "eval"], default="dev")
    p.add_argument("--case", help="이 유형(A1~D5)이 든 문서만")
    p.add_argument("--n", type=int, default=2)
    p.set_defaults(func=_cmd_inspect_gold)

    p = sub.add_parser("make-bundles", help="합성 묶음(평가 사례 9개 × 대상 종류 3개, dev·eval)을 만든다")
    p.add_argument("--synthetic", default=str(data / "synthetic"))
    p.add_argument("--out", default=str(data / "synthetic" / "bundles"))
    p.set_defaults(func=_cmd_make_bundles)

    p = sub.add_parser("bundle-search", help="단계 2 틀: 묶음 검색을 직접 시험한다")
    p.add_argument("--bundle", default=str(data / "bundles" / "sample"))
    p.add_argument("--arabic", required=True)
    p.add_argument("--romanized", nargs="*")
    p.set_defaults(func=_cmd_bundle_search)

    p = sub.add_parser("exp001", help="EXP-001 분석기 실측 (dev로 규칙을 고정한 뒤 main 한 번)")
    p.add_argument("--snapshot", default=str(data / "wikidata" / "gcc_persons.json"))
    p.add_argument("--split", choices=["dev", "main"], default="dev")
    p.add_argument("--dev-keys", default=str(data / "wikidata" / "exp001_dev_keys.json"), help="고정한 dev 키 목록")
    p.add_argument("--out", default=str(results / "exp001"))
    p.set_defaults(func=_cmd_exp001)

    p = sub.add_parser("exp002", help="EXP-002 조건 비교 (기본: eval 30개 × 3회)")
    p.add_argument("--split", choices=["dev", "eval"], default="eval")
    p.add_argument("--docs")
    p.add_argument("--repeats", type=int)
    p.add_argument("--limit", type=int)
    p.add_argument("--fake", action="store_true")
    p.add_argument("--yes", action="store_true", help="비용이 드는 실제 실행에 동의")
    p.add_argument(
        "--resume", nargs="?", const="latest", metavar="DIR", help="멈춘 실행을 이어서 한다(경로가 없으면 최근 실행)"
    )
    p.add_argument("--workers", type=int, default=1, help="동시에 돌릴 실행 수")
    p.add_argument("--max-runs", type=int, help="이번에 새로 시작할 실행 수 상한. 닿으면 멈춘다")
    p.add_argument("--token-budget", type=int, help="이번에 쓸 토큰 상한(입력+출력). 넘으면 새 실행을 시작하지 않는다")
    p.add_argument("--finalize", action="store_true", help="--resume과 함께: 더 돌리지 않고 지금까지로 summary를 쓴다")
    p.set_defaults(func=_cmd_experiment)

    p = sub.add_parser("serve", help="단계 1.5 서비스: API·폼 화면(.env의 LLM_BACKEND·DATABASE_URL·USE_MCP_TOOLS)")
    p.add_argument("--host", help=f"기본 {settings.web_host}")
    p.add_argument("--port", type=int, help=f"기본 {settings.web_port}")
    p.set_defaults(func=_cmd_serve)

    p = sub.add_parser("exp002-status", help="EXP-002 실행의 진행과 사용량(결과 지표는 보이지 않는다)")
    p.add_argument("dir", nargs="?", help="실행 폴더(없으면 그 split의 최근 실행)")
    p.add_argument("--split", choices=["dev", "eval"], default="eval")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_cmd_experiment_status)

    p = sub.add_parser("exp003", help="EXP-003 어려운 시험지 조건 비교(99% 기준, 기본: eval 70개)")
    p.add_argument("--split", choices=["dev", "eval"], default="eval")
    p.add_argument("--docs")
    p.add_argument("--repeats", type=int)
    p.add_argument("--limit", type=int)
    p.add_argument("--fake", action="store_true")
    p.add_argument("--yes", action="store_true", help="비용이 드는 실제 실행에 동의")
    p.add_argument(
        "--resume", nargs="?", const="latest", metavar="DIR", help="멈춘 실행을 이어서 한다(경로가 없으면 최근 실행)"
    )
    p.add_argument("--workers", type=int, default=1, help="동시에 돌릴 실행 수")
    p.add_argument("--max-runs", type=int, help="이번에 새로 시작할 실행 수 상한. 닿으면 멈춘다")
    p.add_argument("--token-budget", type=int, help="이번에 쓸 토큰 상한(입력+출력). 넘으면 새 실행을 시작하지 않는다")
    p.add_argument("--finalize", action="store_true", help="--resume과 함께: 더 돌리지 않고 지금까지로 summary를 쓴다")
    p.set_defaults(func=_cmd_experiment)

    p = sub.add_parser("exp003-status", help="EXP-003 실행의 진행과 사용량(결과 지표는 보이지 않는다)")
    p.add_argument("dir", nargs="?", help="실행 폴더(없으면 그 split의 최근 실행)")
    p.add_argument("--split", choices=["dev", "eval"], default="eval")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_cmd_experiment_status)

    p = sub.add_parser(
        "exp003-rescore", help="EXP-003 저장된 출력을 지금 채점 코드로 다시 채점(참고 값, 판정은 그대로)"
    )
    p.add_argument("dir", nargs="?", help="실행 폴더(없으면 그 split의 최근 실행)")
    p.add_argument("--split", choices=["dev", "eval"], default="eval")
    p.set_defaults(func=_cmd_exp003_rescore)

    p = sub.add_parser("exp003-errors", help="EXP-003 자동 판정 오류 전부와 정답 표본을 사람 확인용 errors.csv로")
    p.add_argument("dir", nargs="?", help="실행 폴더(없으면 그 split의 최근 실행)")
    p.add_argument("--split", choices=["dev", "eval"], default="eval")
    p.add_argument("--sample", type=int, default=50, help="정답으로 판정한 것 가운데 같이 확인할 수")
    p.set_defaults(func=_cmd_exp003_errors)

    return parser


def _configure_logging(verbose: bool) -> None:
    """이 패키지의 로그만 stderr로 낸다. 다른 라이브러리는 기본값(경고 이상)을 따른다."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[%(module)s %(asctime)s] %(levelname)s %(message)s", "%H:%M:%S"))
    pkg = logging.getLogger("tashkeel_check")
    pkg.handlers[:] = [handler]
    pkg.setLevel(logging.DEBUG if verbose else logging.INFO)
    pkg.propagate = False


def _exit_code(exc: TashkeelError) -> int:
    if isinstance(exc, ConfigError):
        return 3
    if isinstance(exc, InputError):
        return 2
    return 1


def main(argv: list[str] | None = None) -> int:
    try:
        settings = load_settings()
        args = _parser(settings).parse_args(argv)
        _configure_logging(args.verbose)
        return int(args.func(args, settings))
    except TashkeelError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return _exit_code(exc)


if __name__ == "__main__":
    raise SystemExit(main())
