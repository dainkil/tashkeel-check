import json

from tashkeel_check.data.synthetic import NOTICE, generate, make_sample_bundle
from tashkeel_check.text import normalize_key, tokenize


def _tok(arabic, english, positions, genders):
    return {"arabic": arabic, "english_variants": english, "positions": positions, "genders": genders}


POOL = {
    "full_names": [normalize_key("سعيد رشيد القبيسي")],
    "tokens": {
        normalize_key(a): t
        for a, t in {
            "سعيد": _tok("سعيد", {"Saeed": 5, "Said": 2}, {"given": 5}, {"male": 5}),
            "راشد": _tok("راشد", {"Rashid": 4, "Rashed": 3}, {"given": 4, "middle": 2}, {"male": 4}),
            "رشيد": _tok("رشيد", {"Rashid": 2, "Rashed": 1}, {"middle": 2}, {"male": 2}),
            "حمد": _tok("حمد", {"Hamad": 3}, {"given": 3}, {"male": 3}),
            "فاطمة": _tok("فاطمة", {"Fatima": 3, "Fatma": 1}, {"given": 3}, {"female": 3}),
            "مريم": _tok("مريم", {"Mariam": 2, "Maryam": 2}, {"given": 2}, {"female": 2}),
            "القبيسي": _tok("القبيسي", {"Al Qubaisi": 3}, {"family": 3}, {"male": 3}),
            "النعيمي": _tok("النعيمي", {"Al Nuaimi": 2, "Al Noaimi": 1}, {"family": 2}, {"male": 2}),
            "الكعبي": _tok("الكعبي", {"Al Kaabi": 2}, {"family": 2}, {"female": 1, "male": 1}),
            "المري": _tok("المري", {"Al Marri": 2}, {"family": 2}, {"male": 2}),
        }.items()
    },
}


def _gen(tmp_path, n=6, seed=11):
    tmp_path.mkdir(parents=True, exist_ok=True)
    pool_path = tmp_path / "pool.json"
    pool_path.write_text(json.dumps(POOL, ensure_ascii=False))
    return [json.loads(p.read_text()) for p in generate(pool_path, tmp_path / "out", "dev", n, seed)]


def test_docs_are_marked_synthetic_and_deterministic(tmp_path):
    a = _gen(tmp_path / "a")
    b = _gen(tmp_path / "b")
    assert a == b
    assert all(d["synthetic"] and d["notice"] == NOTICE for d in a)
    assert {d["doc_type"] for d in a} == {"poa", "company_letter"}


def test_gold_token_ids_point_at_the_named_tokens(tmp_path):
    for doc in _gen(tmp_path):
        tokens = {t["id"]: t for t in tokenize(doc["segments"])}
        for occ in doc["gold"]["names"]:
            for tk in occ["tokens"]:
                assert tokens[tk["token_id"]]["text"] == tk["arabic"]
                assert tk["english_used"] in tk["english_variants"]
        for tid in doc["gold"]["neutral_token_ids"]:
            assert tokens[tid]["script"] == "ar"


def test_evidence_exists_only_for_evidence_roles_and_is_quoted_verbatim(tmp_path):
    for doc in _gen(tmp_path, n=10):
        seg_text = {s["segment_id"]: s["text"] for s in doc["segments"]}
        assert doc["bilingual"] == bool(doc["evidence_roles"])
        for occ in doc["gold"]["names"]:
            if occ["role"] in doc["evidence_roles"]:
                ev = occ["evidence"]
                assert ev["quote"] in seg_text[ev["segment_id"]]
                assert all(tk["english_used"] in ev["quote"] for tk in occ["tokens"])
            else:
                assert occ["evidence"] is None


def test_layouts_are_balanced_per_doc_type_and_mixed_docs_mix(tmp_path):
    docs = _gen(tmp_path, n=6)
    for doc_type in ("poa", "company_letter"):
        assert sorted(d["evidence_layout"] for d in docs if d["doc_type"] == doc_type) == ["all", "mixed", "none"]
    for doc in docs:
        has_ev = {occ["evidence"] is not None for occ in doc["gold"]["names"]}
        assert has_ev == {"none": {False}, "mixed": {True, False}, "all": {True}}[doc["evidence_layout"]]


def test_no_generated_full_name_exists_in_wikidata(tmp_path):
    for doc in _gen(tmp_path, n=10):
        for occ in doc["gold"]["names"]:
            assert normalize_key(occ["arabic_full"]) not in set(POOL["full_names"])


def test_sample_bundle_is_synthetic(tmp_path):
    docs_dir = tmp_path / "out" / "dev"
    _gen(tmp_path)
    paths = make_sample_bundle(next(docs_dir.glob("*.json")), tmp_path / "bundle")
    assert all(NOTICE in p.read_text() for p in paths)
