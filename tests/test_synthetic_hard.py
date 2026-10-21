"""어려운 합성 문서 생성기(synthetic-hard)의 결정성과 정답(gold 형식 2) 불변 조건."""

import glob
import json
import random
from pathlib import Path

from tashkeel_check.data import synthetic_hard as sh
from tashkeel_check.romanize import strict_key, strict_words_in_quote

POOL = json.loads(Path("data/wikidata/name_tokens.json").read_text(encoding="utf-8"))
DEV_FILES = sorted(glob.glob("data/synthetic-hard/dev/*.json"))


def _pool():
    return sh.HardPool(POOL)


def test_generation_is_deterministic_and_every_doc_passes_its_invariants():
    pool = _pool()
    a = sh.build_docs(pool, "scratch", 8, 777)
    b = sh.build_docs(pool, "scratch", 8, 777)
    assert json.dumps(a, ensure_ascii=False) == json.dumps(b, ensure_ascii=False)
    assert {d["doc_type"] for d in a} == set(sh.TEMPLATE_CYCLE)
    for doc in a:
        assert sh.validate_doc(doc) == []
        assert doc["synthetic"] and doc["meta"]["arabic_reviewed_by_human"] is False
        assert doc["gold"]["format_version"] == sh.GOLD_FORMAT


def test_committed_dev_split_is_valid_and_matches_the_generator():
    assert len(DEV_FILES) == sh.DOC_COUNTS["dev"]
    regenerated = sh.build_docs(_pool(), "dev", sh.DOC_COUNTS["dev"], sh.SEEDS["dev"])
    for path, doc in zip(DEV_FILES, regenerated, strict=True):
        stored = json.loads(Path(path).read_text(encoding="utf-8"))
        assert stored == json.loads(json.dumps(doc, ensure_ascii=False)), path
        assert sh.validate_doc(stored) == []


def test_gold_rule_adopt_iff_one_spelling_in_own_renderings():
    for path in DEV_FILES:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        persons = {p["person_id"]: p for p in doc["gold"]["persons"]}
        for occ in doc["gold"]["names"]:
            renderings = persons[occ["person_id"]]["renderings"]
            for u in occ["tokens"]:
                keys = {strict_key(r["slots"][u["slot"]]) for r in renderings if r["slots"].get(u["slot"])}
                assert (u["expected"] == "adopt") == (len(keys) == 1), (path, u["unit_id"])
                assert (len(u["must_include"]) >= 2) == (len(keys) >= 2)
                for ev in u["evidence"]:
                    assert ev["quote"] in next(
                        s["text"] for s in doc["segments"] if s["segment_id"] == ev["segment_id"]
                    )
                    assert strict_words_in_quote(u["expected_spelling"], ev["quote"])


def test_every_case_type_appears_in_dev_and_mrz_lines_are_44_characters():
    docs = [json.loads(Path(p).read_text(encoding="utf-8")) for p in DEV_FILES]
    counts = sh.unit_case_counts(docs)
    assert set(sh.QUOTAS) <= set(counts)
    mrz = [r["quote"] for d in docs for p in d["gold"]["persons"] for r in p["renderings"] if r["form"] == "mrz"]
    assert mrz and all(len(q) == sh.MRZ_LEN and q.startswith("P<") for q in mrz)
    report = sh.quota_report(docs)
    assert report["n_units"] == sum(len(o["tokens"]) for d in docs for o in d["gold"]["names"])
    assert report["hard_share"] >= sh.MIN_HARD_SHARE


def test_variant_cleaning_drops_alias_noise_and_merges_case():
    spellings, weights, plausible = sh.clean_variants({"Ahmed": 314, "Ahmad": 109, "Al": 2, "Ali": 1, "AHMED": 1})
    assert spellings == ["Ahmed", "Ahmad"] and weights == [315, 109]
    assert "Ali" not in plausible and "Al" not in plausible


def test_near_miss_pairs_are_different_names_not_spelling_variants():
    pool = _pool()
    pairs = {(a, b) for _, a, b, _ in pool.near_miss}
    assert ("داوود", "داود") not in pairs and ("داود", "داوود") not in pairs
    assert sh._doubled("داود", "داوود") and not sh._doubled("حمد", "حامد")
    assert pairs


def test_mrz_drops_ancestors_before_giving_up():
    pool = _pool()
    rng = random.Random(1)
    spec = sh.Spec(role="principal", gender="male", nasab=3)
    p = sh.make_person(rng, pool, "p1", spec, set())
    quote, slots, _ = sh.render(p, "mrz")
    if quote:
        assert len(quote) == sh.MRZ_LEN and "family" in slots and "given" in slots
