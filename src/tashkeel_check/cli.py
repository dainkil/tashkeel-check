"""명령줄 진입점: `uv run tashkeel <명령>`.

종료 코드: 0 성공, 1 실행 동의 필요(exp002), 2 입력 오류(InputError, 쓸 수 없는 옵션 조합),
3 설정·환경 오류(ConfigError).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
        m = result["metrics"]
        print(
            json.dumps(
                {
                    "condition": cond,
                    "out": str(out),
                    "valid_output": m["valid_output"],
                    "attempts": m["attempts"],
                    "n_ambiguous_tokens": m.get("n_ambiguous_tokens"),
                    "n_unprocessed": m.get("n_unprocessed"),
                    "silent_rate": m.get("silent_rate"),
                    "tracing": tracing,
                    "mode": "practice (fake model)" if args.fake else settings.model,
                },
                ensure_ascii=False,
            )
        )
    return 0


def _cmd_fetch(args: argparse.Namespace, settings: Settings) -> int:
    from .data.wikidata import build_name_pool, fetch

    snap = fetch(args.out, endpoint=args.endpoint)
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


def _cmd_bundle_search(args: argparse.Namespace, settings: Settings) -> int:
    from .rag import BundleIndex

    index = BundleIndex.from_dir(args.bundle)
    print(f"embeddings: {index.embedding_label}", file=sys.stderr)
    for hit in index.search(args.arabic, args.romanized or []):
        print(json.dumps(hit.to_dict(), ensure_ascii=False))
    return 0


def _cmd_exp001(args: argparse.Namespace, settings: Settings) -> int:
    from .experiments import exp001

    path = exp001.run(args.snapshot, args.split, args.out, coverage_threshold=settings.coverage_threshold)
    print(path)
    return 0


def _cmd_exp002(args: argparse.Namespace, settings: Settings) -> int:
    from .experiments import exp002
    from .runner import make_model

    configure_tracing(settings)
    docs_dir = Path(args.docs or settings.data_dir / "synthetic" / args.split)
    n_docs = len(sorted(docs_dir.glob("*.json"))[: args.limit])
    repeats = args.repeats or settings.repeats
    n_runs = len(CONDITIONS) * n_docs * repeats
    if args.fake and args.split != "dev":
        print("연습 모드(--fake)는 dev 문서에만 씁니다. 평가 문서는 실제 실행에 한 번만 씁니다.", file=sys.stderr)
        return 2
    if not args.fake and not args.yes:
        print(
            f"실행 계획: 조건 {len(CONDITIONS)} × 문서 {n_docs} × 반복 {repeats} = {n_runs}회, 모델 {settings.model}.\n"
            "비용이 듭니다. 실행하려면 --yes를 붙이세요."
        )
        return 1
    path = exp002.run(
        docs_dir,
        settings.results_dir / "exp002" / args.split,
        lambda: make_model(settings, fake=args.fake),
        settings,
        repeats=repeats,
        limit=args.limit,
    )
    print(path)
    return 0


def _parser(settings: Settings) -> argparse.ArgumentParser:
    data, results = settings.data_dir, settings.results_dir
    parser = argparse.ArgumentParser(prog="tashkeel", description="아랍어 문서 모호성 은폐 측정 장치")
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
    p.set_defaults(func=_cmd_fetch)

    p = sub.add_parser("make-synthetic", help="합성 문서(dev·eval)와 샘플 묶음을 만든다")
    p.add_argument("--pool", default=str(data / "wikidata" / "name_tokens.json"))
    p.add_argument("--out", default=str(data / "synthetic"))
    p.add_argument("--dev", type=int)
    p.add_argument("--eval", type=int)
    p.set_defaults(func=_cmd_synthetic)

    p = sub.add_parser("bundle-search", help="단계 2 틀: 묶음 검색을 직접 시험한다")
    p.add_argument("--bundle", default=str(data / "bundles" / "sample"))
    p.add_argument("--arabic", required=True)
    p.add_argument("--romanized", nargs="*")
    p.set_defaults(func=_cmd_bundle_search)

    p = sub.add_parser("exp001", help="EXP-001 분석기 실측 (dev로 규칙을 고정한 뒤 main 한 번)")
    p.add_argument("--snapshot", default=str(data / "wikidata" / "gcc_persons.json"))
    p.add_argument("--split", choices=["dev", "main"], default="dev")
    p.add_argument("--out", default=str(results / "exp001"))
    p.set_defaults(func=_cmd_exp001)

    p = sub.add_parser("exp002", help="EXP-002 조건 비교 (기본: eval 30개 × 3회)")
    p.add_argument("--split", choices=["dev", "eval"], default="eval")
    p.add_argument("--docs")
    p.add_argument("--repeats", type=int)
    p.add_argument("--limit", type=int)
    p.add_argument("--fake", action="store_true")
    p.add_argument("--yes", action="store_true", help="비용이 드는 실제 실행에 동의")
    p.set_defaults(func=_cmd_exp002)

    return parser


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
        return int(args.func(args, settings))
    except TashkeelError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return _exit_code(exc)


if __name__ == "__main__":
    raise SystemExit(main())
