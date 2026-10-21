"""합성 KYC 묶음(상업등기 + 여권 + 정관) 사례 8개가 정답과 맞는지. dev·eval 둘 다 돈다."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tashkeel_check.bundle import review_bundle
from tashkeel_check.bundle.loader import split_bundle_gold
from tashkeel_check.data.kyc_bundles import CASES, DOC_TYPES, generate_kyc_bundles

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def kyc(tmp_path_factory) -> dict[str, dict]:
    out = tmp_path_factory.mktemp("kyc")
    paths = generate_kyc_bundles(ROOT / "data" / "synthetic", out, "dev") + generate_kyc_bundles(
        ROOT / "data" / "synthetic", out, "eval"
    )
    assert len(paths) == 2 * len(CASES)
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in paths}


@pytest.mark.parametrize("split", ["dev", "eval"])
@pytest.mark.parametrize("case", CASES)
def test_case_matches_gold(kyc, split, case):
    obj = kyc[f"{split}_kyc_{case}"]
    bundle, gold = split_bundle_gold(obj)
    assert {d.document_type for d in bundle.documents} <= set(DOC_TYPES)
    assert set(bundle.entities.values()) == {"organization", "person"}
    got = {i.mention_id: (i.status, i.reason) for i in review_bundle(bundle)}
    assert got == {g["mention_id"]: (g["status"], g["reason"]) for g in gold["review_items"]}


@pytest.mark.parametrize("split", ["dev", "eval"])
def test_namesake_shareholder_is_not_linked(kyc, split):
    bundle, gold = split_bundle_gold(kyc[f"{split}_kyc_namesake_shareholder"])
    owner = next(i for i in review_bundle(bundle) if i.mention_id == "register_001:s03:1")
    assert owner.status == "confirmed" and all(e.document_id == "passport_p1" for e in owner.evidence)
    assert gold["must_not_link"]["english"] not in {e.english_name for e in owner.evidence}


@pytest.mark.parametrize("split", ["dev", "eval"])
def test_mrz_only_uses_mrz_segments(kyc, split):
    bundle, gold = split_bundle_gold(kyc[f"{split}_kyc_mrz_only"])
    persons = [i for i in review_bundle(bundle) if i.mention_id in ("register_001:s03:1", "register_001:s04:1")]
    for it in persons:
        passport_ev = [e for e in it.evidence if e.document_id.startswith("passport")]
        assert passport_ev and all(e.segment_id == "s03" and e.valid for e in passport_ev)
        expected = "pending" if it.mention_id in gold["mrz_lossy"] else "confirmed"
        assert it.status == expected


def test_committed_kyc_bundles_match_generator(kyc):
    for stem, obj in kyc.items():
        split = stem.split("_", 1)[0]
        committed = json.loads((ROOT / "data" / "synthetic" / "bundles" / split / f"{stem}.json").read_text("utf-8"))
        assert committed == obj
