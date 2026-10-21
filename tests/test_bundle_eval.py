"""가이드 14단계 평가 사례를 합성 묶음으로 돌린다. 사례 9개 × 대상 종류 3개. 종류에 따라 결과가 달라지면 버그다."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tashkeel_check.bundle import review_bundle
from tashkeel_check.bundle.dictionary import DictionaryEntry, InMemoryDictionary
from tashkeel_check.bundle.evidence import validate_evidence, validated
from tashkeel_check.bundle.loader import split_bundle_gold
from tashkeel_check.bundle.pipeline import bundle_mentions
from tashkeel_check.bundle.rules import decide_status
from tashkeel_check.bundle.schemas import BundleEvidence
from tashkeel_check.data.bundles import CASES, ENTITY_TYPES, generate_bundles

ROOT = Path(__file__).resolve().parents[1]
BASE_DOC = ROOT / "data" / "synthetic" / "dev" / "dev_001.json"


@pytest.fixture(scope="module")
def bundles(tmp_path_factory) -> dict[str, dict]:
    out = tmp_path_factory.mktemp("bundles")
    paths = generate_bundles(BASE_DOC, out, "dev")
    assert len(paths) == len(ENTITY_TYPES) * (len(CASES) + 1)  # other_customer는 묶음 2개
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in paths}


def _outcomes(bundle_obj: dict, dictionary=None) -> dict[str, tuple[str, str]]:
    bundle, _ = split_bundle_gold(bundle_obj)
    return {i.mention_id: (i.status, i.reason) for i in review_bundle(bundle, dictionary)}


@pytest.mark.parametrize("entity_type", ENTITY_TYPES)
@pytest.mark.parametrize("case", [c for c in CASES if c != "model_error"])
def test_case_matches_gold(bundles, entity_type, case):
    obj = bundles[f"dev_{entity_type}_{case}"]
    gold = obj["gold"]
    assert gold["entity_type"] == entity_type and not gold["requires_llm"]
    expected = {g["mention_id"]: (g["status"], g["reason"]) for g in gold["review_items"]}
    assert _outcomes(obj) == expected


@pytest.mark.parametrize("entity_type", ENTITY_TYPES)
def test_namesake_is_never_linked(bundles, entity_type):
    bundle, gold = split_bundle_gold(bundles[f"dev_{entity_type}_namesake"])
    items = review_bundle(bundle)
    assert all(it.evidence == [] for it in items)
    assert all(gold["must_not_link"]["english"] != it.suggestion for it in items)


@pytest.mark.parametrize("entity_type", ENTITY_TYPES)
def test_bad_quote_is_rejected(bundles, entity_type):
    bundle, gold = split_bundle_gold(bundles[f"dev_{entity_type}_bad_quote"])
    claim = gold["claimed_evidence"]
    ev = BundleEvidence(**{k: v for k, v in claim.items() if k != "expected_failure"})
    assert validate_evidence(bundle, ev) == (False, claim["expected_failure"])
    mention = bundle_mentions(bundle)[0]
    assert decide_status(mention, validated(bundle, [ev])).reason == "validation_failed"


@pytest.mark.parametrize("entity_type", ENTITY_TYPES)
def test_other_customer_evidence_is_not_used(bundles, entity_type):
    a_obj = bundles[f"dev_{entity_type}_other_customer"]
    b_obj = bundles[f"dev_{entity_type}_other_customer_b"]
    b, b_gold = split_bundle_gold(b_obj)
    confirmed = [it for it in review_bundle(b) if it.status == "confirmed"]
    assert len(confirmed) == 1 and b_gold["review_items"][0]["reason"] == "evidence_match"
    # 고객 b가 확정한 표기를 고객 b의 사전에 올려도 고객 a의 묶음에는 쓰이지 않는다
    d = InMemoryDictionary()
    it = confirmed[0]
    assert b.customer_id and it.entity_id and it.translated_name
    d.register(
        DictionaryEntry(
            customer_id=b.customer_id,
            entity_id=it.entity_id,
            arabic_key=bundle_mentions(b)[0].arabic_key,
            arabic_name=it.arabic_name,
            english_name=it.translated_name,
        )
    )
    assert set(_outcomes(a_obj, d).values()) == {("pending", "no_evidence")}


@pytest.mark.parametrize("entity_type", ENTITY_TYPES)
def test_model_error_case_is_reserved_for_llm_path(bundles, entity_type):
    gold = bundles[f"dev_{entity_type}_model_error"]["gold"]
    assert gold["requires_llm"] is True
    pytest.skip("LLM 경로(9단계)에서 평가한다")


def test_results_do_not_depend_on_entity_type(bundles):
    by_case: dict[str, set[tuple[tuple[str, str], ...]]] = {}
    for obj in bundles.values():
        if obj["gold"]["requires_llm"]:
            continue
        key = obj["bundle_id"].replace(f"_{obj['gold']['entity_type']}_", "_", 1)  # dev_match, dev_other_customer_b …
        by_case.setdefault(key, set()).add(tuple(sorted(_outcomes(obj).values())))
    assert len(by_case) == len(CASES)  # other_customer_b 포함, model_error 제외
    assert all(len(v) == 1 for v in by_case.values()), by_case
