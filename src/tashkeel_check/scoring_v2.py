"""채점 v2: gold 형식 2(synthetic-hard)의 이름 부분마다 안전·엄격 판정을 낸다(ADR-017, docs/evaluation.md 6.4절).

- 세는 단위는 이름 부분(unit)이 나올 때마다다. عبد الله·آل X처럼 토큰 둘인 부분도 하나로 센다.
- 안전 오류: 틀린 이름이 표시 없이 나간 것. 미처리, 근거 없는 확정, 틀린 철자, 함정 근거로 맞힌 철자,
  보류 항목인데 번역문에 표시 없는 한 표기, 번역문 철자가 확정 표기와 다름.
- 엄격 오류: 안전 오류 + 확정해야 할 것을 보류 + 번역문에 확정 표기가 없음.
- 철자는 엄격 철자(romanize.strict_key)로 본다. 번역문 판정(t2)은 C0 판정 규칙의 단어열 찾기와 표시 판정을 쓴다.
gold 형식 1(synthetic-v2)에는 쓰지 않는다. reconcile이 format_version == 2일 때만 부른다.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from .analyzer import TokenAnalysis
from .reconcile import MARKER_RE, _primary, find_spellings
from .romanize import STRICT_VERSION, strict_in_text, strict_key

SCORING_VERSION = "v2"
TRANSLATION_RULE = "t2"  # t1에서 바뀐 점은 marked_t2·_hits 주석(2026-10-21, eval 생성 전)
C0_RULE = "v1"
SAFETY_KINDS = (
    "unprocessed",
    "unsupported_no_evidence",  # 근거 없는 이름을 근거로 확정했는데 인용이 어느 표기도 아님
    "unsupported_decoy",  # 회사명·이메일·URL을 근거로 인용
    "unsupported_other_person",  # 다른 사람의 표기를 근거로 인용
    "unsupported_own_insufficient",  # 그 사람의 표기지만 그 부분의 완전한 철자가 없거나(이니셜·생략) 충돌
    "unsupported_adopt",  # proper_noun을 근거 없이 adopt
    "unsupported_word_adopt",  # 이름을 word 항목으로 adopt
    "wrong_spelling",
    "decoy_evidence_correct_spelling",  # 철자는 맞지만 근거로 든 것이 그 사람의 표기가 아님
    "translation_unmarked",
    "translation_wrong_spelling",
    "silent_pick",  # C0: 근거 없는 이름을 표시 없이 한 표기로
    "not_found",  # C0: 번역문에서 그 이름을 찾지 못함(C0 판정 규칙 v0과 같이 오류로 센다)
)
STRICT_ONLY_KINDS = ("hold_instead_of_adopt", "translation_missing")


def gold_units(gold: dict) -> list[dict]:
    """이름 부분마다 한 줄. 등장(occurrence)의 정보를 붙인다."""
    return [
        {
            **tk,
            "occurrence_id": occ["occurrence_id"],
            "person_id": occ["person_id"],
            "mention": occ.get("mention", "full"),
            "segment_id": occ["segment_id"],
        }
        for occ in gold.get("names", [])
        for tk in occ["tokens"]
    ]


def _by_segment(units: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for u in units:
        out[u["segment_id"]].append(u)
    return out


def _commit_kind(item: dict) -> str | None:
    fin = item["final_decision"]
    if fin == "evidence_adopt":
        return "evidence"
    if fin == "adopt_unsupported":
        return "adopt"
    if item.get("type") == "word" and fin == "adopt":
        return "word_adopt"
    return None


def unit_disposition(unit: dict, cover: dict[int, list[dict]]) -> tuple[str, dict | None]:
    """미처리 / 확정 / 보류와 그 판단을 대표하는 항목. 부분의 토큰 가운데 하나라도 확정이면 확정으로 본다."""
    tids = unit["token_ids"]
    if any(t not in cover for t in tids):
        return "unprocessed", None
    primaries = [_primary(cover[t]) for t in tids]
    for it in primaries:
        if _commit_kind(it):
            return "commit", it
    return "hold", primaries[0]


def _segment_owners(gold: dict) -> tuple[dict[str, str], set[str]]:
    """구간 → 그 구간에 표기가 있는 사람, 함정이 있는 구간."""
    owners: dict[str, str] = {}
    for p in gold.get("persons", []):
        for r in p.get("renderings", []):
            owners[r["segment_id"]] = p["person_id"]
    return owners, {d["segment_id"] for d in gold.get("decoys", [])}


def _unsupported_kind(unit: dict, item: dict, owners: dict[str, str], decoy_segs: set[str]) -> str:
    kind = _commit_kind(item)
    if kind == "adopt":
        return "unsupported_adopt"
    if kind == "word_adopt":
        return "unsupported_word_adopt"
    sid = (item.get("evidence") or {}).get("segment_id") or ""
    owner = owners.get(sid)
    if owner == unit["person_id"]:
        return "unsupported_own_insufficient"
    if sid in decoy_segs:  # 회사 표기는 회사의 표기이면서 같은 가문명을 가진 사람에게는 함정이다
        return "unsupported_decoy"
    return "unsupported_no_evidence" if owner is None else "unsupported_other_person"


def _unit_candidates(unit: dict, analyses: dict[int, TokenAnalysis], item: dict | None) -> set[str]:
    # raw_variants(Wikidata 별칭 그대로)는 넣지 않는다. أحمد→Aziz 같은 잡음이 옆 이름과 맞는다.
    # 생성기의 같은 구간 제약도 걸러 낸 표기(english_variants)로 검사한다
    cands = set(unit.get("english_variants") or [])
    cands |= {s for s in [unit.get("english_used"), unit.get("expected_spelling"), *unit.get("must_include", [])] if s}
    head = unit["token_id"]
    if head in analyses:
        cands |= {c["display"] for c in analyses[head]["candidates"]}
    # 항목 후보는 그 항목이 이 부분만 덮을 때만 쓴다. 이름 전체 후보가 다른 부분의 단어와 맞지 않게 한다
    if item is not None and set(item["token_ids"]) <= set(unit["token_ids"]):
        cands |= {c.get("romanized") or "" for c in item.get("candidates") or []} - {""}
    return cands


def _marker_in(text: str, lo: int, hi: int) -> bool:
    """text[lo:hi]에 걸친 표시가 있는지. 표시는 원문 전체에서 찾는다(잘린 창에서 찾으면 'Suroor '의 'or '가 단어
    'or'로 잡힌다)."""
    return any(m.start() < hi and m.end() > lo for m in MARKER_RE.finditer(text))


def marked_t2(text: str, start: int, end: int) -> bool:
    """번역문 판정 규칙 t2의 표시 판정. C0 판정 규칙 v0(reconcile._marked)과 같되 두 가지가 다르다.

    - 괄호 경계 너머의 표시는 옆 이름의 것으로 보고 세지 않는다('[Sultan/?] Al Kuwaiti'의 '?'는 Al Kuwaiti의
      표시가 아니다). t1부터.
    - 단어 표시(or 등)는 원문에서 온전한 단어일 때만 센다. t2에서 고침.
    """
    if re.match(r"\s*(\(\?\)|\[\?\])", text[end:]) or re.search(r"(\(\?\)|\[\?\])\s*$", text[:start]):
        return True  # 이름 바로 옆의 (?)·[?]
    lo, hi = max(0, start - 3), end + 3
    if not re.search(r"[\])]", text[lo:start]) and _marker_in(text, lo, start):
        return True
    if not re.search(r"[\[(]", text[end:hi]) and _marker_in(text, end, hi):
        return True
    for open_, close in (("[", "]"), ("(", ")")):
        left, right = text.rfind(open_, 0, start), text.find(close, end)
        if left == -1 or right == -1 or text.rfind(close, left, start) != -1 or text.find(open_, end, right) != -1:
            continue
        inner = text[left + 1 : right]
        if "/" in inner or "?" in inner or re.search(r"\bor\b", inner):
            return True
    return False


def _own_spellings(unit: dict) -> set[str]:
    return {s for s in (unit.get("expected_spelling"), unit.get("english_used"), *unit.get("must_include", [])) if s}


def _claimed(unit: dict, peers: list[dict], english: str) -> list[tuple[int, int]]:
    """같은 구간의 다른 이름 부분이 자기 표기로 쓰인 자리."""
    return [
        (h[0], h[1])
        for u in peers
        if u["unit_id"] != unit["unit_id"]
        for h in find_spellings(_own_spellings(u), english)
    ]


def _hits(cands: set[str], english: str, claimed: list[tuple[int, int]]) -> list[tuple[int, int, str]]:
    """후보 표기가 번역문에 나온 자리. 다른 부분의 자리 안에 들어간 것은 뺀다(t2). 분석기 로마자
    'Al-M'adyd'가 옆 이름 'Abdel Aziz'의 'Aziz'와 맞아 '서로 다른 표기 둘'로 셌다."""
    return [h for h in find_spellings(cands, english) if not any(a <= h[0] and h[1] <= b for a, b in claimed)]


def _held_translation(
    unit: dict, english: str, cands: set[str], claimed: list[tuple[int, int]]
) -> tuple[str | None, str]:
    """보류한 부분의 번역문 판정. (안전 오류 종류 또는 None, 감사 상태)."""
    hits = _hits(cands, english, claimed)
    if len({h[2] for h in hits}) >= 2 or (hits and marked_t2(english, hits[0][0], hits[0][1])):
        return None, "marked"
    if not hits:
        return None, "not_found"  # 표시 여부를 판정할 수 없다. 오류로 세지 않고 감사용으로만 센다(사전 등록)
    if unit["expected"] == "adopt" and strict_in_text(unit["expected_spelling"], english):
        return None, "unmarked_expected"  # 확정해야 할 표기를 번역문에 그대로 썼다. 엄격 오류(보류)만 남는다
    return "translation_unmarked", "unmarked"


def _committed_key(unit: dict, adopted: str) -> str:
    """일관성 집계용: 확정 문자열 안에서 이 부분에 해당하는 표기의 키."""
    for s in [unit.get("expected_spelling"), *(unit.get("english_variants") or [])]:
        if s and strict_in_text(s, adopted):
            return strict_key(s)
    return "?" + strict_key(adopted)


def _judge_structured(
    unit: dict,
    cover: dict[int, list[dict]],
    translation: dict[str, str],
    analyses: dict[int, TokenAnalysis],
    owners: dict[str, str],
    decoy_segs: set[str],
    peers: list[dict],
) -> dict:
    disp, item = unit_disposition(unit, cover)
    english = translation.get(unit["segment_id"]) or ""
    claimed = _claimed(unit, peers, english)
    expected, exp_sp = unit["expected"], unit.get("expected_spelling")
    safety: str | None = None
    strict_only: str | None = None
    audit = ""
    adopted = (item or {}).get("adopted") or ""
    if disp == "unprocessed":
        safety = "unprocessed"
    elif disp == "commit" and item is not None:
        if expected == "hold":
            safety = _unsupported_kind(unit, item, owners, decoy_segs)
        elif not strict_in_text(exp_sp or "", adopted):
            safety = "wrong_spelling"
        elif _commit_kind(item) != "evidence":
            safety = _unsupported_kind(unit, item, owners, decoy_segs)
        else:
            ev = item.get("evidence") or {}
            own = {e["segment_id"] for e in unit.get("evidence", [])}
            if ev.get("segment_id") not in own or not strict_in_text(exp_sp or "", ev.get("quote") or ""):
                safety = "decoy_evidence_correct_spelling"
            elif not strict_in_text(exp_sp or "", english):
                if _hits(_unit_candidates(unit, analyses, None), english, claimed):
                    safety = "translation_wrong_spelling"
                else:
                    strict_only = "translation_missing"
    else:
        safety, audit = _held_translation(unit, english, _unit_candidates(unit, analyses, item), claimed)
        if safety is None and expected == "adopt":
            strict_only = "hold_instead_of_adopt"
    return {
        "disposition": disp,
        "adopted": adopted if disp == "commit" else "",
        "safety_error": safety,
        "strict_only_error": strict_only,
        "translation_audit": audit,
        "item": item,
    }


def _judge_c0(unit: dict, translation: dict[str, str], analyses: dict[int, TokenAnalysis], peers: list[dict]) -> dict:
    """C0 판정 규칙 v1. 표시된 것은 보류, 표시 없는 한 표기는 확정으로 보고 엄격 철자로 판정한다."""
    english = translation.get(unit["segment_id"]) or ""
    hits = _hits(_unit_candidates(unit, analyses, None), english, _claimed(unit, peers, english))
    safety: str | None = None
    strict_only: str | None = None
    written = ""
    if not hits:
        disp, safety = "not_found", "not_found"
    elif len({h[2] for h in hits}) >= 2 or marked_t2(english, hits[0][0], hits[0][1]):
        disp = "hold"
        if unit["expected"] == "adopt":
            strict_only = "hold_instead_of_adopt"
    else:
        disp, written = "commit", english[hits[0][0] : hits[0][1]]
        if unit["expected"] == "hold":
            safety = "silent_pick"
        # 일치 규칙 v1의 단어열은 관사를 무시해 옆 이름의 'Al'까지 붙을 수 있다. 철자는 구간 안 엄격 일치로 본다
        elif not strict_in_text(unit["expected_spelling"], english):
            safety = "wrong_spelling"
    return {
        "disposition": disp,
        "adopted": written,
        "safety_error": safety,
        "strict_only_error": strict_only,
        "translation_audit": "",
        "item": None,
    }


def _tally(gold: dict, units: list[dict], judged: list[dict]) -> dict[str, Any]:
    n = len(units)
    strict_ok = [j["safety_error"] is None and j["strict_only_error"] is None for j in judged]
    safety_ok = [j["safety_error"] is None for j in judged]
    out: dict[str, Any] = {
        "n_scored_units": n,
        "n_scored_arabic_tokens": sum(len(u["token_ids"]) for u in units),
        "n_expected_adopt": sum(u["expected"] == "adopt" for u in units),
        "n_expected_hold": sum(u["expected"] == "hold" for u in units),
        "n_strict_correct": sum(strict_ok),
        "n_safety_ok": sum(safety_ok),
        "n_safety_errors": n - sum(safety_ok),
    }
    for k in SAFETY_KINDS:
        out[f"n_err_{k}"] = sum(j["safety_error"] == k for j in judged)
    for k in STRICT_ONLY_KINDS:
        out[f"n_strict_only_{k}"] = sum(j["strict_only_error"] == k and j["safety_error"] is None for j in judged)
    out["n_translation_not_found"] = sum(j["translation_audit"] == "not_found" for j in judged)
    nonarg = [i for i, u in enumerate(units) if not u.get("arguable")]
    out["n_scored_units_nonarguable"] = len(nonarg)
    out["n_strict_correct_nonarguable"] = sum(strict_ok[i] for i in nonarg)
    out["n_safety_ok_nonarguable"] = sum(safety_ok[i] for i in nonarg)
    out["n_docs"] = 1
    out["doc_strict_all_correct"] = int(all(strict_ok))
    out["doc_safety_all_ok"] = int(all(safety_ok))
    by_case: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "strict": 0, "safety_ok": 0})
    for u, s_ok, f_ok in zip(units, strict_ok, safety_ok, strict=True):
        for ct in u.get("case_types") or ["none"]:
            by_case[ct]["n"] += 1
            by_case[ct]["strict"] += s_ok
            by_case[ct]["safety_ok"] += f_ok
    out["by_case_type"] = dict(sorted(by_case.items()))
    out["units"] = [
        {
            "unit_id": u["unit_id"],
            "person_id": u["person_id"],
            "slot": u["slot"],
            "segment_id": u["segment_id"],
            "arabic": u["arabic"],
            "case_types": u.get("case_types", []),
            "arguable": bool(u.get("arguable")),
            "expected": u["expected"],
            "expected_spelling": u.get("expected_spelling"),
            "disposition": j["disposition"],
            "adopted": j["adopted"],
            "error": j["safety_error"] or j["strict_only_error"] or "",
            "strict_ok": s_ok,
            "safety_ok": f_ok,
        }
        for u, j, s_ok, f_ok in zip(units, judged, strict_ok, safety_ok, strict=True)
    ]
    out["scoring"] = {"scoring": SCORING_VERSION, "strict_spelling": STRICT_VERSION, "translation": TRANSLATION_RULE}
    return out


def score_structured(
    gold: dict,
    items: list[dict],
    cover: dict[int, list[dict]],
    translation: dict[str, str],
    analyses: dict[int, TokenAnalysis],
) -> dict[str, Any]:
    units = gold_units(gold)
    owners, decoy_segs = _segment_owners(gold)
    peers = _by_segment(units)
    judged = [
        _judge_structured(u, cover, translation, analyses, owners, decoy_segs, peers[u["segment_id"]]) for u in units
    ]
    out = _tally(gold, units, judged)
    must = [(u, j) for u, j in zip(units, judged, strict=True) if u.get("must_include") and j["disposition"] == "hold"]
    out["n_hold_must_include"] = len(must)
    out["n_hold_must_include_ok"] = sum(
        all(
            any(strict_in_text(m, c.get("romanized") or "") for c in (j["item"] or {}).get("candidates") or [])
            for m in u["must_include"]
        )
        for u, j in must
    )
    lookalikes = set(gold.get("lookalike_token_ids", []))
    pn_tokens = {t for it in items if it["valid"] and it.get("type") == "proper_noun" for t in it["token_ids"]}
    out["n_lookalike_tokens"] = len(lookalikes)
    out["n_lookalike_flagged_as_name"] = len(lookalikes & pn_tokens)
    committed: dict[tuple[str, str], set[str]] = defaultdict(set)
    for u, j in zip(units, judged, strict=True):
        if j["disposition"] == "commit" and j["adopted"]:
            committed[(u["person_id"], u["slot"])].add(_committed_key(u, j["adopted"]))
    out["n_person_inconsistent"] = sum(len(v) > 1 for v in committed.values())
    return out


def score_c0(gold: dict, translation: dict[str, str], analyses: dict[int, TokenAnalysis]) -> dict[str, Any]:
    units = gold_units(gold)
    peers = _by_segment(units)
    out = _tally(gold, units, [_judge_c0(u, translation, analyses, peers[u["segment_id"]]) for u in units])
    out["scoring"]["c0_rule"] = C0_RULE
    return out
