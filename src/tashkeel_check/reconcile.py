"""결정적 대조 노드의 본체. 강등 규칙을 적용하고 지표를 센다. LLM을 부르지 않는다(ADR-004).

gold(합성 문서의 정답 라벨)가 있으면 말없이 찍음 같은 정답 기반 지표를 더 센다.
gold는 프롬프트에 들어가지 않고 이 단계에서만 쓴다.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

from .analyzer import TokenAnalysis
from .romanize import match_spelling, normalize_latin, spelling_in_text
from .text import Segment, Token, has_latin, normalize_key

MARKER_RE = re.compile(r"\[\?\]|\(\?\)|\?|/|\bor\b|\bunclear\b|\buncertain\b", re.I)
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’\-]*")
SEG_LINE_RE = re.compile(r"^\s*\[(s\d+)\]\s*(.*)$")
ADOPTED_FINALS = {"adopt", "adopt_unsupported", "evidence_adopt"}


def _squash(s: str) -> str:
    return " ".join(s.lower().split())


def _canon(spelling: str) -> str:
    forms = normalize_latin(spelling)
    return min(forms) if forms else spelling.lower()


def _rate(n: int, d: int) -> float | None:
    return round(n / d, 4) if d else None


def _analysis_count(analyses: dict[int, TokenAnalysis], tid: int, default: int | str) -> int | str:
    """분석 수. 아랍어 토큰이 아니어서 분석이 없으면 default."""
    a = analyses.get(tid)
    return a["analysis_count"] if a is not None else default


# ---------- 항목 검사 ----------


def verify_evidence(item: dict, seg_text: dict[str, str]) -> tuple[bool, str]:
    ev = item.get("evidence") or {}
    sid = ev.get("segment_id")
    quote = (ev.get("quote") or "").strip()
    adopted = (item.get("adopted") or "").strip()
    if not sid or sid not in seg_text:
        return False, "segment_not_found"
    if not quote or not has_latin(quote):
        return False, "quote_not_latin"
    if _squash(quote) not in _squash(seg_text[sid]):
        return False, "quote_not_in_segment"
    if not adopted:
        return False, "no_adopted_spelling"
    if not spelling_in_text(adopted, quote):
        return False, "adopted_not_in_quote"
    return True, ""


def check_items(raw_items: list[dict], tokens: list[Token], segments: list[Segment]) -> list[dict]:
    by_id = {t["id"]: t for t in tokens}
    seg_text = {s["segment_id"]: s["text"] for s in segments}
    checked = []
    for idx, raw in enumerate(raw_items):
        ids = [i for i in (raw.get("token_ids") or []) if isinstance(i, int)]
        valid = (
            bool(ids)
            and len(ids) == len(raw.get("token_ids") or [])
            and all(i in by_id and by_id[i]["script"] == "ar" for i in ids)
        )
        typ, dec = raw.get("type"), raw.get("decision")
        final, flags, failure = dec, [], None
        if not valid:
            flags.append("invalid_token_ids")
        if typ == "word":
            if dec == "hold":
                final = "abstain"
                flags.append("type_decision_mismatch")
            elif dec == "evidence_adopt":
                final = "adopt"
                flags.append("type_decision_mismatch")
        elif typ == "proper_noun":
            if dec == "adopt":
                final = "adopt_unsupported"
                flags.append("unsupported_adopt")
            elif dec == "abstain":
                final = "hold"
                flags.append("type_decision_mismatch")
            elif dec == "evidence_adopt":
                ok, failure = verify_evidence(raw, seg_text)
                if not ok:
                    final = "hold"
                    flags.append("evidence_failed")
        checked.append(
            {
                **raw,
                "item_index": idx,
                "valid": valid,
                "final_decision": final,
                "flags": flags,
                "evidence_failure": failure or None,
                "arabic": " ".join(by_id[i]["text"] for i in ids if i in by_id),
                "segment_id": by_id[ids[0]]["segment_id"] if valid else None,
            }
        )
    return checked


# ---------- gold ----------


def gold_name_tokens(gold: dict | None) -> dict[int, dict]:
    out: dict[int, dict] = {}
    if not gold:
        return out
    for occ in gold.get("names", []):
        for tk in occ["tokens"]:
            out[tk["token_id"]] = {
                **tk,
                "occurrence_id": occ["occurrence_id"],
                "role": occ["role"],
                "segment_id": occ["segment_id"],
                "has_evidence": occ.get("evidence") is not None,
            }
    return out


def _breakdown(statuses: dict[int, str], info: dict[int, dict], analyses: dict[int, TokenAnalysis]) -> dict:
    groups: dict[str, list[int]] = defaultdict(list)
    for tid in statuses:
        groups["variants_ge2" if len(info[tid].get("english_variants", [])) >= 2 else "variants_1"].append(tid)
        count = _analysis_count(analyses, tid, 0)
        groups["analyzer_0" if count == 0 else "analyzer_ge1"].append(tid)
    return {
        g: {
            "n": len(ids),
            "silent_rate": _rate(sum(statuses[t] == "silent" for t in ids), len(ids)),
            "unsupported_adopt_rate": _rate(sum(statuses[t] == "unsupported_adopt" for t in ids), len(ids)),
        }
        for g, ids in sorted(groups.items())
    }


# ---------- C1~C3 ----------


def _primary(items: list[dict]) -> dict:
    return next((it for it in items if it.get("type") == "proper_noun"), items[0])


def _coverage(items: list[dict]) -> dict[int, list[dict]]:
    """토큰 ID → 그 토큰을 덮는 유효 항목들."""
    cover: dict[int, list[dict]] = defaultdict(list)
    for it in items:
        if it["valid"]:
            for i in it["token_ids"]:
                cover[i].append(it)
    return cover


def _unsupported_at(tid: int, it: dict, gold_ids: set[int]) -> bool:
    """토큰 tid를 대표하는 항목 it이 근거 없는 확정인지. 정답 이름을 일반 단어로 adopt한 것도 센다."""
    return it["final_decision"] == "adopt_unsupported" or (
        it.get("type") == "word" and it["final_decision"] == "adopt" and tid in gold_ids
    )


def _gold_statuses(gtok: dict[int, dict], cover: dict[int, list[dict]]) -> dict[int, str]:
    """정답 이름 토큰마다 처분 상태."""
    statuses: dict[int, str] = {}
    for tid, info in gtok.items():
        if tid not in cover:
            statuses[tid] = "silent"
            continue
        it = _primary(cover[tid])
        fin = it["final_decision"]
        if _unsupported_at(tid, it, set(gtok)):
            statuses[tid] = "unsupported_adopt"
        elif fin == "evidence_adopt":
            if info["has_evidence"]:
                used = info.get("english_used") or ""
                ok = bool(used) and spelling_in_text(used, it.get("adopted") or "")
                statuses[tid] = "evidence_correct" if ok else "evidence_wrong_spelling"
            else:
                statuses[tid] = "evidence_without_gold_evidence"
        else:
            statuses[tid] = "hold"
    return statuses


def _hold_candidate_hits(gtok: dict[int, dict], held: list[int], cover: dict[int, list[dict]]) -> int:
    """보류한 정답 이름 토큰 가운데, 보류 항목의 후보에 문서가 실제로 쓴 표기(english_used)가 든 수.

    근거가 없는 합성 문서에서 english_used는 신분증 표기 역할을 한다. 담당자가 후보 중에서 고르기만 하면 되는지를 본다.
    """
    hits = 0
    for t in held:
        used = gtok[t].get("english_used") or ""
        cands = [c.get("romanized") or "" for c in _primary(cover[t]).get("candidates") or []]
        hits += bool(used) and any(spelling_in_text(used, c) for c in cands)
    return hits


def _gold_metrics(
    gtok: dict[int, dict], statuses: dict[int, str], analyses: dict[int, TokenAnalysis], cover: dict[int, list[dict]]
) -> dict:
    no_ev = [t for t in gtok if not gtok[t]["has_evidence"]]
    with_ev = [t for t in gtok if gtok[t]["has_evidence"]]
    held = [t for t in no_ev if statuses[t] == "hold"]
    n_hit = _hold_candidate_hits(gtok, held, cover)
    return {
        "n_gold_name_tokens": len(gtok),
        "n_gold_without_evidence": len(no_ev),
        "n_gold_with_evidence": len(with_ev),
        "n_silent": sum(statuses[t] == "silent" for t in no_ev),
        "n_unsupported_adopt": sum(statuses[t] == "unsupported_adopt" for t in no_ev),
        "n_hold": sum(statuses[t] == "hold" for t in no_ev),
        "n_evidence_correct": sum(statuses[t] == "evidence_correct" for t in with_ev),
        "silent_rate": _rate(sum(statuses[t] == "silent" for t in no_ev), len(no_ev)),
        "unsupported_adopt_rate": _rate(sum(statuses[t] == "unsupported_adopt" for t in no_ev), len(no_ev)),
        "hold_rate": _rate(sum(statuses[t] == "hold" for t in no_ev), len(no_ev)),
        "n_hold_candidate_hit": n_hit,
        "hold_candidate_hit_rate": _rate(n_hit, len(held)),
        "evidence_without_gold_evidence": sum(statuses[t] == "evidence_without_gold_evidence" for t in no_ev),
        "evidence_pass_rate": _rate(sum(statuses[t] == "evidence_correct" for t in with_ev), len(with_ev)),
        "breakdown_without_evidence": _breakdown({t: statuses[t] for t in no_ev}, gtok, analyses),
    }


def _tool_metrics(tool_log: list[dict], ambiguous: set[int], gold_ids: set[int]) -> dict | None:
    """C2의 analyze_tokens 사용 지표. 호출이 없으면 None."""
    analyzer_calls = [c for c in tool_log if c.get("tool") == "analyze_tokens"]
    if not analyzer_calls:
        return None
    queried = {i for call in analyzer_calls for i in call.get("token_ids", [])}
    return {
        "calls": len(analyzer_calls),
        "tokens_queried": len(queried),
        "ambiguous_recall": _rate(len(queried & ambiguous), len(ambiguous)),
        "ambiguous_precision": _rate(len(queried & ambiguous), len(queried)),
        "gold_names_queried": _rate(len(queried & gold_ids), len(gold_ids)) if gold_ids else None,
    }


def _name_rows(items: list[dict], unprocessed: list[dict], analyses: dict[int, TokenAnalysis]) -> list[dict]:
    """확인 대기 목록: 유효한 고유명사 항목, 그다음 어느 항목에도 덮이지 않은 정답 이름."""
    rows = [_pn_row(it, analyses) for it in items if it["valid"] and it.get("type") == "proper_noun"]
    for u in unprocessed:
        if u["reason"] == "gold_name":
            rows.append(
                {
                    "arabic": u["text"],
                    "token_ids": str(u["token_id"]),
                    "candidates": "",
                    "adopted": "",
                    "decision": "unprocessed",
                    "evidence": "",
                    "analyzer_counts": f"{u['token_id']}:{_analysis_count(analyses, u['token_id'], '')}",
                    "flags": "",
                }
            )
    return rows


def _structured(
    segments: list[Segment],
    tokens: list[Token],
    analyses: dict[int, TokenAnalysis],
    output: dict | None,
    gold: dict | None,
    tool_log: list[dict],
    high_conf: float,
) -> dict:
    by_id = {t["id"]: t for t in tokens}
    items = check_items((output or {}).get("items", []), tokens, segments)
    translation = {t["segment_id"]: t["english"] for t in (output or {}).get("translation", [])}
    cover = _coverage(items)

    ambiguous = {tid for tid, a in analyses.items() if a["ambiguous"]}
    gtok = gold_name_tokens(gold)
    gold_ids = set(gtok)
    # 중립 토큰(지명·국가명·발급 기관·법인 형태)은 처분을 기대하지도, 처분했다고 감점하지도 않는다
    neutral = set((gold or {}).get("neutral_token_ids", []))
    universe = (ambiguous - neutral) | gold_ids
    unprocessed: list[dict[str, Any]] = [
        {
            "token_id": t,
            "text": by_id[t]["text"],
            "segment_id": by_id[t]["segment_id"],
            "reason": "gold_name" if t in gtok else "ambiguous_word",
        }
        for t in sorted(universe)
        if t not in cover
    ]
    pn_tokens = {i for it in items if it["valid"] and it.get("type") == "proper_noun" for i in it["token_ids"]}
    suspected_missed = sorted(
        t for t, a in analyses.items() if a["has_noun_prop"] and t not in pn_tokens and t not in neutral
    )

    def over_flag(it: dict) -> bool:
        ids = set(it["token_ids"])
        if gold:
            return not (ids & universe) and not ids <= neutral
        return it.get("type") == "word" and not (ids & ambiguous)

    adopted_by_key: dict[str, set[str]] = defaultdict(set)
    for it in items:
        if it["valid"] and it["final_decision"] in ADOPTED_FINALS and it.get("adopted"):
            adopted_by_key[normalize_key(it["arabic"])].add(_canon(it["adopted"]))

    valid_items = [it for it in items if it["valid"]]
    # 항목 단위로 세면 모델이 항목을 쪼개거나 묶는 방식에 따라 값이 바뀌므로 토큰 단위로 센다
    over_flag_tokens = {t for it in valid_items if over_flag(it) for t in it["token_ids"] if t not in neutral}
    # 한 토큰을 여러 항목이 덮으면 대표 항목(_primary) 하나로 판정한다. 정답 이름 상태(_gold_statuses)와 같은 기준이다
    unsupported = {
        t: _primary(its) for t, its in cover.items() if t not in neutral and _unsupported_at(t, _primary(its), gold_ids)
    }
    metrics: dict[str, Any] = {
        "n_items": len(items),
        "n_invalid_items": sum(not it["valid"] for it in items),
        "n_type_decision_mismatch": sum("type_decision_mismatch" in it["flags"] for it in items),
        "decisions": dict(Counter(f"{it.get('type')}:{it['final_decision']}" for it in valid_items)),
        "n_ambiguous_tokens": len(ambiguous),
        "n_unprocessed": len(unprocessed),
        "n_unprocessed_names": sum(u["reason"] == "gold_name" for u in unprocessed),
        "n_unprocessed_ambiguous_words": sum(u["reason"] == "ambiguous_word" for u in unprocessed),
        "n_evidence_failed": sum("evidence_failed" in it["flags"] for it in items),
        "n_unsupported_adopt_tokens": len(unsupported),
        "n_high_conf_unsupported_tokens": sum((it.get("confidence") or 0) >= high_conf for it in unsupported.values()),
        "n_over_flag_tokens": len(over_flag_tokens),
        "n_inconsistent_names": sum(len(v) > 1 for v in adopted_by_key.values()),
        "n_suspected_missed_names": len(suspected_missed),
        "n_proper_noun_tokens_without_analyzer_candidates": sum(
            _analysis_count(analyses, t, 1) == 0 for t in (gold_ids or pn_tokens)
        ),
        "n_segments_translated": sum(1 for s in segments if translation.get(s["segment_id"])),
        "n_segments": len(segments),
    }
    statuses = _gold_statuses(gtok, cover)
    if gtok:
        metrics.update(_gold_metrics(gtok, statuses, analyses, cover))
    tool = _tool_metrics(tool_log, ambiguous, gold_ids)
    if tool is not None:
        metrics["tool"] = tool

    return {
        "items": items,
        "translation": translation,
        "unprocessed": unprocessed,
        "suspected_missed_names": suspected_missed,
        "gold_status": {str(k): v for k, v in statuses.items()},
        "proper_nouns": _name_rows(items, unprocessed, analyses),
        "metrics": metrics,
    }


def _pn_row(it: dict, analyses: dict[int, TokenAnalysis]) -> dict:
    ev = it.get("evidence") or {}
    return {
        "arabic": it["arabic"],
        "token_ids": " ".join(map(str, it["token_ids"])),
        "candidates": "; ".join(f"{c.get('romanized')}({c.get('source')})" for c in it.get("candidates") or []),
        "adopted": it.get("adopted") or "",
        "decision": it["final_decision"],
        "evidence": f"{ev.get('segment_id')}: {ev.get('quote')}" if ev else "",
        "analyzer_counts": " ".join(f"{t}:{_analysis_count(analyses, t, '')}" for t in it["token_ids"]),
        "flags": " ".join(it["flags"]),
    }


# ---------- C0 ----------


def parse_c0(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in (text or "").splitlines():
        m = SEG_LINE_RE.match(line)
        if m:
            out[m.group(1)] = (out.get(m.group(1), "") + " " + m.group(2)).strip()
    return out


def find_spellings(candidates: set[str], text: str) -> list[tuple[int, int, str]]:
    """text에서 후보 표기와 일치하는 단어열의 (시작, 끝, 정규형).

    정규형은 번역문에 실제로 쓰인 단어열에서 만든다. 후보에서 만들면 한 단어열에 여러 후보가 맞을 때
    집합 순회 순서(PYTHONHASHSEED)에 따라 값이 바뀐다(TS-003)."""
    words = list(WORD_RE.finditer(text))
    hits: list[tuple[int, int, str]] = []
    for n in (3, 2, 1):
        for i in range(len(words) - n + 1):
            start, end = words[i].start(), words[i + n - 1].end()
            if any(h[0] <= start < h[1] or h[0] < end <= h[1] for h in hits):
                continue
            span = text[start:end]
            if any(match_spelling(c, span) for c in candidates):
                hits.append((start, end, _canon(span)))
    return sorted(hits)


def _marked(text: str, start: int, end: int) -> bool:
    """C0 판정 규칙 v0: 일치한 표기 바로 앞뒤(3자 이내)에 불확실 표시가 있거나,
    "/"·"?"가 든 대괄호·소괄호 안에 있으면 표시한 것으로 본다."""
    if MARKER_RE.search(text[max(0, start - 3) : start]) or MARKER_RE.search(text[end : end + 3]):
        return True
    for open_, close in (("[", "]"), ("(", ")")):
        left, right = text.rfind(open_, 0, start), text.find(close, end)
        if left != -1 and right != -1 and text.rfind(close, left, start) == -1:
            inner = text[left + 1 : right]
            if "/" in inner or "?" in inner or re.search(r"\bor\b", inner):
                return True
    return False


def _c0(
    segments: list[Segment],
    tokens: list[Token],
    analyses: dict[int, TokenAnalysis],
    output: str | None,
    gold: dict | None,
) -> dict:
    translation = parse_c0(output if isinstance(output, str) else "")
    gtok = gold_name_tokens(gold)
    statuses: dict[int, str] = {}
    matched_by_key: dict[str, set[str]] = defaultdict(set)
    rows = []
    for tid, info in gtok.items():
        cands = set(info.get("english_variants", []))
        cands |= {c["display"] for c in analyses[tid]["candidates"]} if tid in analyses else set()
        text = translation.get(info["segment_id"], "")
        hits = find_spellings(cands, text)
        distinct = {h[2] for h in hits}
        if len(distinct) >= 2:
            status = "flagged"
        elif hits:
            status = "flagged" if _marked(text, hits[0][0], hits[0][1]) else "silent"
            matched_by_key[normalize_key(info["arabic"])].add(hits[0][2])
        else:
            status = "not_found"
        statuses[tid] = status
        rows.append(
            {
                "arabic": info["arabic"],
                "token_ids": str(tid),
                "candidates": "; ".join(sorted(cands)),
                "adopted": text[hits[0][0] : hits[0][1]] if hits else "",
                "decision": f"c0:{status}",
                "evidence": "",
                "analyzer_counts": f"{tid}:{_analysis_count(analyses, tid, '')}",
                "flags": "",
            }
        )
    metrics: dict[str, Any] = {
        "n_segments": len(segments),
        "n_segments_translated": sum(1 for s in segments if translation.get(s["segment_id"])),
        "n_ambiguous_tokens": sum(a["ambiguous"] for a in analyses.values()),
        "n_unprocessed": None,  # C0는 처분 형식이 없다
        "n_inconsistent_names": sum(len(v) > 1 for v in matched_by_key.values()),
    }
    if gtok:
        no_ev = [t for t in gtok if not gtok[t]["has_evidence"]]
        with_ev = [t for t in gtok if gtok[t]["has_evidence"]]
        silent_like = {"silent", "not_found"}
        metrics.update(
            {
                "n_gold_name_tokens": len(gtok),
                "n_gold_without_evidence": len(no_ev),
                "n_gold_with_evidence": len(with_ev),
                "n_silent": sum(statuses[t] in silent_like for t in no_ev),
                "silent_rate": _rate(sum(statuses[t] in silent_like for t in no_ev), len(no_ev)),
                "silent_rate_found_only": _rate(
                    sum(statuses[t] == "silent" for t in no_ev), sum(statuses[t] != "not_found" for t in no_ev)
                ),
                "n_not_found": sum(statuses[t] == "not_found" for t in gtok),
                "breakdown_without_evidence": _breakdown(
                    {t: ("silent" if statuses[t] in silent_like else statuses[t]) for t in no_ev}, gtok, analyses
                ),
            }
        )
    return {
        "items": [],
        "translation": translation,
        "unprocessed": [],
        "suspected_missed_names": [],
        "gold_status": {str(k): v for k, v in statuses.items()},
        "proper_nouns": rows,
        "metrics": metrics,
    }


# ---------- 진입점 ----------


def reconcile(
    condition: str,
    segments: list[Segment],
    tokens: list[Token],
    analyses: dict[int, TokenAnalysis],
    output: Any,
    gold: dict | None = None,
    tool_log: list[dict] | None = None,
    high_conf: float = 0.8,
) -> dict:
    if condition == "C0":
        result = _c0(segments, tokens, analyses, output, gold)
    else:
        result = _structured(segments, tokens, analyses, output, gold, tool_log or [], high_conf)
    result["condition"] = condition
    result["segments"] = [
        {
            "segment_id": s["segment_id"],
            "arabic": s["text"],
            "english": result["translation"].get(s["segment_id"]),
            "items": [it for it in result["items"] if it.get("segment_id") == s["segment_id"]],
            "unprocessed": [u for u in result["unprocessed"] if u["segment_id"] == s["segment_id"]],
        }
        for s in segments
    ]
    return result
