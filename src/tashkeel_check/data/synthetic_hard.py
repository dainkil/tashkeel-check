"""어려운 합성 문서 생성기(synthetic-hard, ADR-017, docs/data.md 5.3절). 결정적이다(seed 고정).

- synthetic-v2와 같은 이름 풀(Wikidata 이름 단위)로 사람을 만들고, 어려운 유형을 문서에 심는다:
  동명이인·이름 겹침(A), 근거 형식 변형(B), 함정 근거(C), 문서 규모·문맥(D).
- 유형은 실제 KYC 서류에서 생길 법한 것으로 먼저 정했다. 모델 결과로 문서를 고르거나 버리지 않는다(ADR-014).
- 기대 처분은 정답 규칙 하나로 정한다. 사람마다 이름 부분별로 그 사람의 로마자 표기에 나온 완전한 철자(엄격 키)를
  모아 하나면 확정, 둘 이상이면 보류(그 철자들이 모두 후보에 있어야 함), 없으면 보류.
  이니셜과 생략은 철자로 치지 않는다.
  다른 사람의 표기, 회사명·이메일·URL은 근거가 아니다. 같은 사람이 다시 나오면 같은 처분을 따른다.
- 유형 태그는 문서를 다 만든 뒤 gold에서 다시 계산한다. 배정표는 태그 수가 모자란 유형에 가중치를 더 준다.
- 템플릿의 아랍어 문장은 사람이 검수하지 않았다.
"""

from __future__ import annotations

import json
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..romanize import match_spelling, strict_key, strict_words_in_quote
from ..text import Segment, normalize_key, tokenize, tokens_in_span
from .synthetic import AUTHORITY, CITIES, COUNTRY, JOBS, LLC, NATIONALITIES, NOTICE, _placeholder_ids

GENERATOR_VERSION = "synthetic-hard-v1"
GOLD_FORMAT = 2
SEEDS = {"dev": 3001, "eval": 4002}
DOC_COUNTS = {"dev": 20, "eval": 70}
PREFIX = {"dev": "hdev", "eval": "heval"}
CASE_TYPES = {
    "A1": "같은 아랍어 이름(부자 가문명·아버지 이름 포함), 근거는 다른 사람에게만",
    "A2": "같은 아랍어 이름의 두 사람이 서로 다른 영문 표기로 각자 근거가 있음",
    "A3": "같은 사람이 짧은 형태·호칭으로 다시 나옴",
    "B1": "근거가 전부 대문자",
    "B2": "근거가 '성, 이름' 순서 또는 Surname/Given names 칸",
    "B3": "근거가 여권 MRZ 줄",
    "B4": "근거에서 그 부분이 이니셜뿐",
    "B5": "근거의 관사가 El",
    "B6": "근거에서 그 부분(아버지·할아버지 이름)이 빠짐",
    "C1": "비슷하지만 다른 이름을 가진 다른 사람의 표기만 있음",
    "C2": "회사명·이메일·URL 속에만 그 가문명이 있음",
    "C3": "같은 사람의 표기가 둘이고 그 부분의 철자가 서로 다름",
    "D1": "이름 부분이 30개 넘는 긴 문서(문서 단위)",
    "D2": "같은 문서에 그 이름과 같은 일반 단어가 있음",
    "D3": "호칭·آل/عبد/أبو 단위·긴 nasab",
    "D4": "라벨 없는 먼 곳의 표기(서명 목록·첨부)만 근거",
    "D5": "국적 형용사와 같은 가문명(nisba)",
}
FEATURES = ("A1", "A2", "B1", "B2", "B3", "B4", "B5", "B6", "C1", "C2", "C3", "D2", "D3", "D4", "D5")
# eval 최소 수량(이름 부분 기준). dev는 문서 수 비율로 줄인다. 값은 dev와 별도 seed로만 조정한다
QUOTAS = {
    "A1": 80,
    "A2": 60,
    "A3": 100,
    "B1": 60,
    "B2": 60,
    "B3": 60,
    "B4": 40,
    "B5": 30,
    "B6": 50,
    "C1": 50,
    "C2": 80,
    "C3": 50,
    "D2": 50,
    "D3": 80,
    "D4": 60,
    "D5": 20,
}
D1_MIN_DOCS = 15
LOOKALIKE_MIN = 50
# 어려운 유형에 속한 이름 부분의 최소 비율. 나머지는 쉬운 대조군(근거가 바로 옆에 있거나 아예 없는 이름)으로,
# 엄격 정확도에서 과잉 보류를 잰다. 계획은 0.70이었으나 생성기 구조상 약 2/3에서 멈춰 하한을 0.60으로 둔다
MIN_HARD_SHARE = 0.60
ADOPT_SHARE = (0.40, 0.60)
LONG_DOC_UNITS = 30
TEMPLATE_CYCLE = ("poa", "letter", "cr", "minutes")
# 긴 문서에서 한 문서에 심을 수 있는 횟수(나머지는 1번)
REPEATABLE = {
    "A1": 2,
    "A2": 2,
    "C1": 3,
    "C2": 2,
    "C3": 2,
    "B1": 2,
    "B2": 2,
    "B3": 2,
    "B4": 2,
    "B5": 2,
    "B6": 4,
    "D3": 3,
}
TEMPLATE_FEATURES = {
    "poa": set(FEATURES),
    "letter": set(FEATURES) - {"D4"},
    "cr": set(FEATURES) - {"D2"},
    "minutes": set(FEATURES) - {"B3"},  # 의사록 참석자 명단에 여권 MRZ 줄은 어색하다
}
STATE = {"إماراتي": "ARE", "سعودي": "SAU", "قطري": "QAT", "كويتي": "KWT", "بحريني": "BHR", "عماني": "OMN"}
TITLES = {"male": ("الشيخ", "الدكتور", "المهندس"), "female": ("الشيخة", "الدكتورة", "المهندسة")}
NISBA = {"الكويتي": 3, "القطري": 2}  # 가문명 → NATIONALITIES 번호
HONORIFIC = {"male": "السيد", "female": "السيدة"}
MRZ_LEN = 44
SLOT_ORDER = ("given", "father", "grandfather", "ggf", "family")
POSITION = {"given": "given", "father": "middle", "grandfather": "middle", "ggf": "middle", "family": "family"}
ASCII_NAME = re.compile(r"[A-Za-z][A-Za-z' \-]*")


# ---------- 이름 풀 ----------


@dataclass
class Unit:
    key: str
    arabic: str
    spellings: list[str]  # 근거에 쓸 수 있는 표기: 엄격 키별 대표, 빈도 2 이상, 최빈 표기와 일치 규칙 v1로 맞음
    weights: list[int]
    plausible: list[str]  # 후보로 볼 만한 표기(빈도 조건 없음)
    raw: list[str]

    @property
    def n_keys(self) -> int:
        return len({strict_key(s) for s in self.spellings})


def clean_variants(variants: dict[str, int], min_count: int = 2) -> tuple[list[str], list[int], list[str]]:
    """같은 엄격 키의 변이를 합치고, Wikidata 별칭 잡음(أحمد→Ali 등)을 걷는다."""
    groups: dict[str, dict[str, int]] = defaultdict(dict)
    for v, c in variants.items():
        if ASCII_NAME.fullmatch(v) and (k := strict_key(v)):
            groups[k][v] = groups[k].get(v, 0) + c
    reps: list[tuple[str, int]] = []
    for forms in groups.values():
        best = sorted(forms.items(), key=lambda x: (x[0].isupper() or x[0].islower(), -x[1], x[0]))[0][0]
        reps.append((best[0].upper() + best[1:], sum(forms.values())))
    reps.sort(key=lambda x: (-x[1], x[0]))
    if not reps:
        return [], [], []
    top = reps[0][0]
    ok = [(r, c) for r, c in reps if r == top or match_spelling(r, top)]
    ev = [(r, c) for r, c in ok if c >= min_count]
    return [r for r, _ in ev], [c for _, c in ev], [r for r, _ in ok]


def _doubled(a: str, b: str) -> bool:
    """한쪽이 다른 쪽에 이웃 글자를 하나 더 겹쳐 쓴 것(داود/داوود)이면 같은 이름의 표기 변이로 본다."""
    short, long_ = sorted((a, b), key=len)
    if len(long_) != len(short) + 1:
        return False
    for i in range(len(long_)):
        if long_[:i] + long_[i + 1 :] == short:
            return (i > 0 and long_[i - 1] == long_[i]) or (i + 1 < len(long_) and long_[i + 1] == long_[i])
    return False


def _edit1(a: str, b: str) -> bool:
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b, strict=True)) == 1
    short, long_ = sorted((a, b), key=len)
    return any(long_[:i] + long_[i + 1 :] == short for i in range(len(long_)))


class HardPool:
    def __init__(self, pool: dict):
        self.full_names = set(pool["full_names"])
        self.units: dict[str, Unit] = {}
        self.given: dict[str, list[Unit]] = {"male": [], "female": []}
        self.middle: list[Unit] = []
        self.family: dict[str, list[Unit]] = {"al": [], "aal": [], "abu": [], "nisba": []}
        for key, t in pool["tokens"].items():
            ar = t["arabic"]
            words = ar.split()
            if "الشيخ" in ar or not t["english_variants"] or len(words) > 2:
                continue
            nisba = normalize_key(ar) in {normalize_key(n) for n in NISBA}
            sp, w, pl = clean_variants(t["english_variants"], 1 if nisba else 2)
            if not sp:
                continue
            u = Unit(key, ar, sp, w, pl, list(t["english_variants"]))
            pos, gen = t["positions"], t["genders"]
            male, female = gen.get("male", 0), gen.get("female", 0)
            head = words[0] if len(words) == 2 else ""
            if nisba:
                self.family["nisba"].append(u)
            elif pos.get("family") and not pos.get("given") and head in ("آل", "أبو"):
                self.family["aal" if head == "آل" else "abu"].append(u)
            elif pos.get("family") and not head and ar.startswith("ال"):
                self.family["al"].append(u)
            elif (pos.get("given") or pos.get("middle")) and head in ("", "عبد"):
                if male >= female and male > 0:
                    self.given["male"].append(u)
                    self.middle.append(u)
                elif female > male:
                    self.given["female"].append(u)
            else:
                continue
            self.units[normalize_key(ar)] = u
        for name, lst in [
            ("male", self.given["male"]),
            ("female", self.given["female"]),
            ("family", self.family["al"]),
        ]:
            if not lst:
                raise ValueError(f"name pool has no {name} names")
        # 비슷하지만 다른 이름(C1): 아랍어가 한 글자 다르고(같은 글자를 겹쳐 쓴 표기 변이는 제외),
        # 한쪽의 근거 표기가 다른 쪽 후보와 일치 규칙 v1로 맞는 쌍. (부분 종류, a, b, a의 표기)
        self.near_miss: list[tuple[str, str, str, str]] = []
        for kind, lst in (("given", self.given["male"]), ("family", self.family["al"])):
            singles = [u for u in lst if " " not in u.arabic]
            for i, a in enumerate(singles):
                for b in singles[i + 1 :]:
                    ka, kb = normalize_key(a.arabic), normalize_key(b.arabic)
                    if not _edit1(ka, kb) or _doubled(ka, kb):
                        continue
                    for x, y in ((a, b), (b, a)):
                        spell = next(
                            (
                                s
                                for s in x.spellings
                                if any(match_spelling(s, v) for v in y.plausible)
                                and all(strict_key(s) != strict_key(v) for v in y.plausible)
                            ),
                            None,
                        )
                        if spell:
                            self.near_miss.append((kind, x.key, y.key, spell))
        self.near_miss.sort()
        self.multi_given = [u for u in self.given["male"] if u.n_keys >= 2]
        self.multi_family = [u for u in self.family["al"] if u.n_keys >= 2]

    def unit(self, arabic: str) -> Unit | None:
        return self.units.get(normalize_key(arabic))

    @staticmethod
    def pick(rng: random.Random, lst: list[Unit], exclude: set[str]) -> Unit:
        choices = [u for u in lst if u.key not in exclude] or lst
        return rng.choices(choices, weights=[sum(u.weights) for u in choices], k=1)[0]

    @staticmethod
    def spelling(rng: random.Random, u: Unit) -> str:
        return rng.choices(u.spellings, weights=u.weights, k=1)[0]


# ---------- 사람 ----------


class _Retry(Exception):
    """이 문서를 같은 난수 흐름으로 다시 만든다(제약 위반)."""


@dataclass
class HSlot:
    slot: str
    unit: Unit
    spelling: str  # 이 사람의 신분증 표기(정답 기준)


@dataclass
class HPerson:
    pid: str
    kind: str  # person | company
    role: str
    gender: str
    slots: dict[str, HSlot]
    conn: bool = False
    title: str | None = None
    nationality: int = 0
    nisba: bool = False
    relation: str = ""  # son_of:<pid> 등 정답 판단의 근거(arguable 표시)

    def order(self) -> list[str]:
        return [s for s in SLOT_ORDER if s in self.slots]

    def arabic_pieces(self, mention: str) -> list[tuple[str, str | None]]:
        """(텍스트, 이름 부분 또는 None). 연결어 بن/بنت은 이름 부분이 아니다."""
        if self.kind == "company":
            return [(self.slots["family"].unit.arabic, "family")]
        if mention == "short":
            return [(self.slots["given"].unit.arabic, "given"), (self.slots["family"].unit.arabic, "family")]
        if mention == "title_short":
            return [(self.slots["given"].unit.arabic, "given")]
        out: list[tuple[str, str | None]] = []
        ancestors = [s for s in self.order() if s not in ("given", "family")]
        out.append((self.slots["given"].unit.arabic, "given"))
        for i, s in enumerate(ancestors):
            if self.conn:
                out.append(("بنت" if i == 0 and self.gender == "female" else "بن", None))
            out.append((self.slots[s].unit.arabic, s))
        out.append((self.slots["family"].unit.arabic, "family"))
        return out

    def full_arabic(self) -> str:
        return " ".join(t for t, _ in self.arabic_pieces("full"))


def _clash(units: list[Unit]) -> bool:
    """한 사람의 이름 부분끼리 아랍어가 같거나 표기가 일치 규칙 v1로 맞으면 번역문 판정이 섞인다."""
    for i, a in enumerate(units):
        for b in units[i + 1 :]:
            if a.key == b.key or any(match_spelling(x, y) for x in a.plausible for y in b.plausible):
                return True
    return False


@dataclass
class Spec:
    """사람 하나를 만들기 전에 정하는 것. 유형 배정이 여기를 채운다."""

    role: str
    gender: str = ""
    nasab: int = 0  # 0이면 무작위(1~2), 3이면 긴 nasab
    family_kind: str = "al"
    title: bool = False
    force: dict[str, Unit] = field(default_factory=dict)
    avoid: set[str] = field(default_factory=set)
    spell: dict[str, str] = field(default_factory=dict)
    el_family: bool = False
    forms: list[str] = field(default_factory=list)  # 이 사람의 표기(라벨 줄·여권 칸 등). 비면 표기 없음
    conflict: list[str] = field(default_factory=list)  # 두 번째 표기에서 철자를 바꿀 이름 부분
    unlabeled: bool = False  # 라벨 없는 먼 곳 표기(D4)
    relation: str = ""
    lookalike: str | None = None  # 이 사람의 이름과 같은 일반 단어(D2)
    keep_forms: bool = False  # 쌍 유형(A1·A2·C1)이 이 사람의 표기 유무에 기대고 있다
    nationality: int | None = None  # 아들은 아버지와 같은 국적


def make_person(rng: random.Random, pool: HardPool, pid: str, spec: Spec, used: set[str]) -> HPerson:
    gender = spec.gender or rng.choice(["male", "female"])
    for _ in range(100):
        nasab = spec.nasab or rng.choices([1, 2], weights=[45, 55])[0]
        slots: dict[str, Unit] = {}
        taken = set(used) | spec.avoid
        fam_list = pool.family[spec.family_kind] or pool.family["al"]
        for s in ("given", "father", "grandfather", "ggf")[: nasab + 1]:
            if s in spec.force:
                slots[s] = spec.force[s]
            else:
                lst = pool.given[gender] if s == "given" else pool.middle
                slots[s] = pool.pick(rng, lst, taken)
            taken.add(slots[s].key)
        slots["family"] = spec.force.get("family") or pool.pick(rng, fam_list, taken)
        units = list(slots.values())
        if _clash(units):
            continue
        hs = {s: HSlot(s, u, spec.spell.get(s) or pool.spelling(rng, u)) for s, u in slots.items()}
        fam = hs["family"]
        if spec.el_family and re.match(r"^Al[ \-]", fam.spelling):
            fam.spelling = rng.choice(["El ", "El-"]) + fam.spelling[3:]
        nat = NISBA.get(
            next((n for n in NISBA if normalize_key(n) == fam.unit.key), ""), rng.randrange(len(NATIONALITIES))
        )
        p = HPerson(
            pid,
            "person",
            spec.role,
            gender,
            hs,
            conn=rng.random() < 0.5,
            title=rng.choice(TITLES[gender]) if spec.title else None,
            nationality=nat if spec.nationality is None else spec.nationality,
            nisba=fam.unit.key in {normalize_key(n) for n in NISBA},
            relation=spec.relation,
        )
        if normalize_key(p.full_arabic()) not in pool.full_names:
            return p
    raise _Retry(f"could not build person {pid} ({spec.role})")  # 강제한 이름끼리 겹친다. 문서를 다시 뽑는다


def make_company(rng: random.Random, pool: HardPool, pid: str, family: Unit | None, used: set[str]) -> HPerson:
    u = family or pool.pick(rng, pool.family["al"], used)
    return HPerson(pid, "company", "company", "male", {"family": HSlot("family", u, pool.spelling(rng, u))})


# ---------- 로마자 표기 형태 ----------


def _initial(spelling: str) -> str:
    return spelling.strip()[0].upper() + "."


def render(p: HPerson, form: str, spell: dict[str, str] | None = None) -> tuple[str, dict[str, str], list[str]]:
    """(인용 텍스트, 완전한 철자가 나온 이름 부분 → 철자, 이니셜로만 나온 이름 부분)."""
    sp = {s: (spell or {}).get(s) or p.slots[s].spelling for s in p.order()}
    if p.kind == "company":
        return sp["family"], {"family": sp["family"]}, []
    order = p.order()
    middle = [s for s in order if s not in ("given", "family")]
    conn = ["bint" if p.gender == "female" else "bin"] if p.conn else []
    if form in ("plain", "caps", "unlabeled_full", "unlabeled_caps"):
        words = [sp["given"]]
        for i, s in enumerate(middle):
            words += (conn if i == 0 else (["bin"] if p.conn else [])) + [sp[s]]
        text = " ".join([*words, sp["family"]])
        if form in ("caps", "unlabeled_caps"):
            text = text.upper()
        return text, sp, []
    given_names = " ".join(sp[s] for s in ["given", *middle])
    if form == "reversed_comma":
        return f"{sp['family'].upper()}, {given_names}", sp, []
    if form == "surname_given":
        return f"Surname: {sp['family'].upper()} / Given names: {given_names.upper()}", sp, []
    if form == "mrz":

        def mrz(t: str) -> str:
            return re.sub(r"[ \-]+", "<", t.upper().replace("'", ""))

        state = STATE[NATIONALITIES[p.nationality][0]]
        # 실제 MRZ는 44자를 넘으면 이름을 자른다. 여기서는 할아버지 이하를 빼고, 그래도 넘으면 쓰지 않는다
        for names in (["given", *middle], ["given", *middle[:1]]):
            text = f"P<{state}{mrz(sp['family'])}<<{mrz(' '.join(sp[s] for s in names))}"
            if len(text) <= MRZ_LEN:
                return text.ljust(MRZ_LEN, "<"), {s: sp[s] for s in [*names, "family"]}, []
        return "", {}, []
    if form == "initials":
        inits = ["given", *middle[:1]]
        text = " ".join([*(_initial(sp[s]) for s in inits), sp["family"]])
        return text, {"family": sp["family"]}, inits
    if form == "partial":
        return f"{sp['given']} {sp['family']}", {"given": sp["given"], "family": sp["family"]}, []
    raise ValueError(form)


# ---------- 문서 조립 ----------


@dataclass
class _Mark:
    kind: str  # name | ren | decoy | title | look | neutral
    person: HPerson | None = None
    mention: str = "full"
    form: str = ""
    spell: dict[str, str] | None = None
    labeled: bool = True
    text: str = ""
    dkind: str = ""
    resembles: list[str] = field(default_factory=list)
    twin: str | None = None


def N(p: HPerson, mention: str = "full") -> _Mark:
    return _Mark("name", p, mention)


def R(p: HPerson, form: str, spell: dict[str, str] | None = None, labeled: bool = True) -> _Mark:
    return _Mark("ren", p, form=form, spell=spell, labeled=labeled)


def D(text: str, kind: str, resembles: list[str]) -> _Mark:
    return _Mark("decoy", text=text, dkind=kind, resembles=resembles)


def T(text: str) -> _Mark:
    return _Mark("title", text=text)


def L(text: str, kind: str = "common_word", twin: str | None = None) -> _Mark:
    return _Mark("look", text=text, dkind=kind, twin=twin)


def Z(text: str) -> _Mark:
    return _Mark("neutral", text=text)


class HardBuilder:
    def __init__(self) -> None:
        self.segments: list[Segment] = []
        self.mentions: list[dict] = []
        self.renderings: list[dict] = []
        self.decoys: list[dict] = []
        self.titles: list[tuple[str, int, int]] = []
        self.lookalikes: list[dict] = []
        self.neutral: list[tuple[str, int, int]] = []

    def seg(self, *parts: object) -> str:
        sid = f"s{len(self.segments) + 1:02d}"
        text = ""
        for part in parts:
            if not isinstance(part, _Mark):
                text += str(part)
                continue
            start = len(text)
            if part.kind == "name" and part.person is not None:
                slot_spans: dict[str, tuple[int, int]] = {}
                for i, (piece, slot) in enumerate(part.person.arabic_pieces(part.mention)):
                    if i:
                        text += " "
                    if slot:
                        slot_spans[slot] = (len(text), len(text) + len(piece))
                    text += piece
                self.mentions.append(
                    {
                        "person": part.person,
                        "mention": part.mention,
                        "segment_id": sid,
                        "span": (start, len(text)),
                        "slots": slot_spans,
                    }
                )
            elif part.kind == "ren" and part.person is not None:
                quote, full, initials = render(part.person, part.form, part.spell)
                if not quote:
                    raise _Retry(f"{part.form} does not fit")
                text += quote
                self.renderings.append(
                    {
                        "person_id": part.person.pid,
                        "segment_id": sid,
                        "quote": quote,
                        "form": part.form,
                        "labeled": part.labeled,
                        "slots": full,
                        "initial_slots": initials,
                    }
                )
            else:
                text += part.text
                span = (sid, start, len(text))
                if part.kind == "decoy":
                    self.decoys.append(
                        {"segment_id": sid, "quote": part.text, "kind": part.dkind, "resembles": part.resembles}
                    )
                elif part.kind == "title":
                    self.titles.append(span)
                elif part.kind == "look":
                    self.lookalikes.append({"span": span, "kind": part.dkind, "twin": part.twin})
                else:
                    self.neutral.append(span)
        self.segments.append(Segment(segment_id=sid, text=text))
        return sid


def _hon(p: HPerson) -> str:
    return HONORIFIC[p.gender] + " "


def _named(p: HPerson, mention: str = "full") -> list[object]:
    """칭호(الشيخ·الدكتور 등)가 있으면 칭호와 이름, 없으면 السيد/السيدة와 이름. 짧은 형태는 칭호를 붙이지 않는다."""
    if p.title and mention != "short":
        return [T(p.title), " ", N(p, mention)]
    return [_hon(p), N(p, mention)]


def _nat(p: HPerson) -> str:
    return NATIONALITIES[p.nationality][0 if p.gender == "male" else 1]


def _slug(spelling: str) -> str:
    return re.sub(r"[^a-z]", "", spelling.lower())


# ---------- 유형 배정 ----------


class Caster:
    """사람 명세(Spec)를 만들고 유형을 심는다. 실제 태그는 gold에서 다시 계산하므로 여기서는 기회를 만들 뿐이다."""

    def __init__(self, rng: random.Random, pool: HardPool, feats: set[str], long: bool = False):
        self.rng, self.pool = rng, pool
        # 긴 문서는 사람이 많아 쌍 유형·충돌·가족 회사를 두 번까지 심는다
        self.budget = Counter({f: REPEATABLE.get(f, 1) if long else 1 for f in feats})
        self.specs: dict[str, Spec] = {}
        self.persons: dict[str, HPerson] = {}
        self.used: set[str] = set()

    def spec(self, pid: str, role: str, **kw: Any) -> Spec:
        s = Spec(role=role, **kw)
        self.specs[pid] = s
        return s

    def build(self, pid: str) -> HPerson:
        p = make_person(self.rng, self.pool, pid, self.specs[pid], self.used)
        self.persons[pid] = p
        for s in p.slots.values():
            self.used.add(s.unit.key)
        return p

    def has(self, f: str) -> bool:
        return self.budget[f] > 0

    def take(self, f: str) -> bool:
        if self.budget[f] > 0:
            self.budget[f] -= 1
            return True
        return False

    def decorate(self, spec: Spec) -> None:
        """한 사람에게 붙일 수 있는 유형(형식 변형·호칭·nisba)."""
        rng = self.rng
        if spec.forms and spec.forms[0] not in ("initials", "partial"):
            for f, form in (("B1", "caps"), ("B2", rng.choice(["reversed_comma", "surname_given"])), ("B3", "mrz")):
                if self.take(f):
                    if spec.forms[0] == "plain":
                        spec.forms[0] = form
                    else:
                        spec.forms.append(form)
            if self.take("B5"):
                spec.el_family = True
        if self.take("D3"):
            spec.title = True
            choice = rng.choice(["aal", "abd", "nasab"])
            if choice == "aal" and self.pool.family["aal"]:
                spec.family_kind = "aal"
            elif choice == "abd":
                abd = [u for u in self.pool.given["male"] if u.arabic.startswith("عبد")]
                if abd and spec.gender != "female" and "given" not in spec.force:
                    spec.gender = "male"
                    spec.force["given"] = self.pool.pick(rng, abd, self.used)
            else:
                spec.nasab = 3

    def pairs(self, a: Spec, b: Spec) -> None:
        """두 사람 사이의 유형(A1·A2·C1). a가 먼저 만들어진다."""
        rng, pool = self.rng, self.pool
        if self.take("A1"):
            a.gender = b.gender = "male"
            a.forms = a.forms or ["plain"]
            b.forms = []
            b.relation = "son_of"
            a.keep_forms = b.keep_forms = True
            return
        free = "given" not in a.force and "given" not in b.force
        if free and pool.multi_given and self.take("A2"):
            u = pool.pick(rng, pool.multi_given, self.used)
            s1, s2 = rng.sample(sorted({strict_key(s): s for s in u.spellings}.values()), 2)
            a.gender = b.gender = "male"
            a.force["given"], b.force["given"] = u, u
            a.spell["given"], b.spell["given"] = s1, s2
            a.forms = a.forms or ["plain"]
            b.forms = b.forms or ["plain"]
            a.keep_forms = b.keep_forms = True
            return
        if free and "family" not in a.force and "family" not in b.force and pool.near_miss and self.take("C1"):
            kind, ka, kb, spell = rng.choice(pool.near_miss)
            slot = "given" if kind == "given" else "family"
            if slot == "given":
                a.gender = b.gender = "male"
            a.force[slot], b.force[slot] = pool.units[ka], pool.units[kb]
            a.spell[slot] = spell
            a.forms = a.forms or ["plain"]
            b.forms = []
            a.keep_forms = b.keep_forms = True

    def link(self, a: HPerson, b_pid: str) -> None:
        """A1(아들) 관계: b가 a의 가문명과 a의 이름을 아버지 이름으로 갖는다."""
        spec = self.specs[b_pid]
        if spec.relation == "son_of":
            spec.force["family"] = a.slots["family"].unit
            spec.force["father"] = a.slots["given"].unit
            spec.nationality = a.nationality
            spec.nasab = max(spec.nasab, 1)
            spec.relation = f"son_of:{a.pid}"

    def conflict(self, spec: Spec) -> None:
        """C3: 두 번째 표기에서 한두 부분의 철자를 바꾼다. 그 부분은 철자가 둘 이상인 단위로 고른다."""
        rng, pool = self.rng, self.pool
        if spec.forms and spec.forms[0] in ("initials", "partial"):  # 이니셜·생략 표기(B4·B6)를 지우지 않는다
            return
        free = [
            s for s in ("given", "family") if s not in spec.force and not (s == "given" and spec.gender == "female")
        ]
        if not free or not self.take("C3"):
            return
        rng.shuffle(free)
        for slot in free[: 2 if rng.random() < 0.4 else 1]:
            lst = pool.multi_given if slot == "given" else pool.multi_family
            if slot == "given":
                spec.gender = "male"
            spec.force[slot] = pool.pick(rng, lst, self.used)
            spec.conflict.append(slot)
        spec.forms = spec.forms or ["plain"]

    def second_spelling(self, p: HPerson) -> dict[str, str]:
        out = {}
        for slot in self.specs[p.pid].conflict:
            u, cur = p.slots[slot].unit, p.slots[slot].spelling
            alts = sorted({strict_key(s): s for s in u.spellings if strict_key(s) != strict_key(cur)}.values())
            if alts:
                out[slot] = self.rng.choice(alts)
        return out


def _renderings_for(c: Caster, p: HPerson, label: str, suffix: str = "") -> list[list[object]]:
    """한 사람의 표기 구간들(라벨 줄 + 여권 칸 + 충돌 표기). 표기가 없으면 빈 목록."""
    spec = c.specs[p.pid]
    segs: list[list[object]] = []
    for i, form in enumerate(spec.forms):
        if form in ("plain", "caps", "reversed_comma", "initials", "partial"):
            segs.append([f"{label}: ", R(p, form), suffix if i == 0 else ""])
        else:
            segs.append([R(p, form)])
    second = c.second_spelling(p)
    if second and segs:
        form = c.rng.choice(["surname_given", "caps", "reversed_comma"])
        segs.append(["Passport name: " if form != "surname_given" else "", R(p, form, second)])
    return segs


# ---------- 템플릿 ----------


def _initials_partial(c: Caster, specs: list[Spec]) -> None:
    """B4는 한 사람, B6(아버지 이름을 뺀 영문)은 쌍 유형에 묶이지 않은 사람 모두에게 붙인다."""
    targets = [t for t in specs if not t.keep_forms]
    if targets and c.take("B4"):
        targets.pop(0).forms = ["initials"]
    if targets and c.take("B6"):
        for t in targets:
            t.forms = ["partial"]


def _poa(c: Caster, ids: dict[str, str]) -> HardBuilder:
    rng = c.rng
    sp = c.spec("p1", "principal", forms=["plain"] if rng.random() < 0.6 else [])
    sa = c.spec("p2", "agent", forms=["plain"] if rng.random() < 0.45 else [])
    c.pairs(sp, sa)
    _initials_partial(c, [sa, sp])
    c.conflict(sp)
    c.decorate(sp)
    if c.take("D2"):
        word = rng.choice(["صالح", "كامل"])
        if (u := c.pool.unit(word)) and "given" not in sp.force:
            sp.gender, sp.force["given"], sp.lookalike = "male", u, word
    if c.take("D5"):
        sp.family_kind = "nisba"
    if not sp.keep_forms and sp.forms in ([], ["plain"]) and not sp.conflict and c.take("D4"):
        sp.forms, sp.unlabeled = [], True
    c2: str | None = None
    if c.take("C2"):  # 회사명이 표기 없는 사람의 가문명과 같다(가족 회사)
        if not sa.forms and not sa.unlabeled:
            c2 = "p2"
        elif not sp.forms and not sp.unlabeled:
            c2 = "p1"
        elif not sa.keep_forms:
            sa.forms, c2 = [], "p2"
    P = c.build("p1")
    c.link(P, "p2")
    A = c.build("p2")
    company_family = c.persons[c2].slots["family"].unit if c2 else None
    C = make_company(rng, c.pool, "c1", company_family, c.used if company_family is None else set())
    c.persons["c1"] = C
    company_rendered = company_family is not None or rng.random() < 0.5
    b = HardBuilder()
    b.seg("وكالة خاصة")
    b.seg(
        "إنه في يوم ",
        ids["date"],
        " حضر أمام الكاتب العدل ",
        *_named(P),
        "، ",
        _nat(P),
        " الجنسية، ",
        "ويحمل" if P.gender == "male" else "وتحمل",
        " جواز سفر رقم ",
        ids["passport"],
        ".",
    )
    for parts in _renderings_for(c, P, "Principal", f", Passport No. {ids['passport']}"):
        b.seg(*parts)
    b.seg(
        "وذلك بصفته مديرًا" if P.gender == "male" else "وذلك بصفتها مديرة",
        " لشركة ",
        N(C),
        " للتجارة العامة ",
        Z(LLC),
        "، المرخصة من ",
        Z(AUTHORITY),
        " برقم ",
        ids["reg"],
        "، وعنوانها ",
        Z(rng.choice(CITIES)),
        "، ",
        Z(COUNTRY),
        ".",
    )
    if company_rendered:
        resembles = [f"{q.pid}.family" for q in (P, A) if q.slots["family"].unit.key == C.slots["family"].unit.key]
        b.seg("Company: ", R(C, "plain"), f" General Trading L.L.C., Registration No. {ids['reg']}")
        if resembles:
            b.decoys.append(
                {
                    "segment_id": b.segments[-1]["segment_id"],
                    "quote": render(C, "plain")[0],
                    "kind": "company",
                    "resembles": resembles,
                }
            )
    b.seg(
        "وقرر أنه وكّل " if P.gender == "male" else "وقررت أنها وكّلت ",
        *_named(A),
        "، ",
        _nat(A),
        " الجنسية، ",
        "ويحمل" if A.gender == "male" else "وتحمل",
        " بطاقة هوية رقم ",
        ids["id"],
        ".",
    )
    for parts in _renderings_for(c, A, "Attorney", f", ID No. {ids['id']}"):
        b.seg(*parts)
    b.seg(
        "للقيام نيابة ",
        "عنه" if P.gender == "male" else "عنها",
        " بمراجعة الجهات الحكومية والتوقيع على الطلبات والمستندات المتعلقة بالشركة واستلام الشهادات والتراخيص.",
    )
    twin = f"{P.pid}.given"
    b.seg(
        "وهذا التوكيل ",
        L("صالح", twin=twin if c.specs["p1"].lookalike == "صالح" else None),
        " لمدة سنة واحدة من تاريخه.",
    )
    if P.gender == "male":
        b.seg(
            "والموكل ", L("كامل", twin=twin if c.specs["p1"].lookalike == "كامل" else None), " الأهلية المعتبرة قانونًا."
        )
    b.seg("الموكل: " if P.gender == "male" else "الموكلة: ", N(P, "short"))
    b.seg("الوكيل: " if A.gender == "male" else "الوكيلة: ", N(A, "short"))
    b.seg("التوقيع: ____________")
    if c.specs["p1"].unlabeled:
        b.seg("المرفقات: صورة جواز السفر")
        b.seg(R(P, rng.choice(["unlabeled_full", "unlabeled_caps"]), labeled=False), f" — {ids['passport']}")
    return b


def _letter(c: Caster, ids: dict[str, str]) -> HardBuilder:
    rng = c.rng
    sx = c.spec("p1", "employee", forms=["plain"] if rng.random() < 0.55 else [])
    ss = c.spec("p2", "signatory", forms=["plain"] if rng.random() < 0.5 else [])
    c.pairs(ss, sx)
    _initials_partial(c, [sx, ss])
    c.conflict(sx)
    c.decorate(sx)
    if c.take("D2") and (u := c.pool.unit("حسن")) and "given" not in sx.force:
        sx.gender, sx.force["given"], sx.lookalike = "male", u, "حسن"
    if c.take("D5"):
        sx.family_kind = "nisba"
    family_business = c.take("C2")
    c2_target = None
    if family_business:  # 가족 회사: 표기 없는 사람의 가문명이 회사명·이메일·URL에만 나온다
        if not ss.keep_forms:
            ss.forms, c2_target = [], "p2"
        elif not sx.forms:
            c2_target = "p1"
    S = c.build("p2")
    c.link(S, "p1")
    X = c.build("p1")
    fam = c.persons[c2_target].slots["family"].unit if c2_target else None
    C = make_company(rng, c.pool, "c1", fam, set() if fam else c.used)
    c.persons["c1"] = C
    cslug = _slug(C.slots["family"].spelling)
    same_family = [q.pid for q in (X, S) if q.slots["family"].unit.key == C.slots["family"].unit.key]
    b = HardBuilder()
    if family_business or rng.random() < 0.5:
        b.seg(R(C, "plain"), " General Trading L.L.C.")
        if same_family:
            b.decoys.append(
                {
                    "segment_id": b.segments[-1]["segment_id"],
                    "quote": render(C, "plain")[0],
                    "kind": "company",
                    "resembles": [f"{q}.family" for q in same_family],
                }
            )
    if family_business or rng.random() < 0.3:
        domain = rng.choice(["example.com", "example.net"])
        url = f"www.{cslug}-group.{domain}"
        b.seg("Tel: +971 4 ", ids["id"][:7], " | ", D(url, "url", [f"{q}.family" for q in same_family] + ["c1.family"]))
    b.seg("إفادة لمن يهمه الأمر")
    b.seg(
        "تشهد شركة ",
        N(C),
        " للتجارة العامة ",
        Z(LLC),
        "، المرخصة من ",
        Z(AUTHORITY),
        " برقم ",
        ids["reg"],
        "، وعنوانها ",
        Z(rng.choice(CITIES)),
        "، ",
        Z(COUNTRY),
        "،",
    )
    job = rng.choice(JOBS)
    b.seg(
        "بأن ",
        *_named(X),
        "، ",
        _nat(X),
        " الجنسية، ",
        "ويحمل" if X.gender == "male" else "وتحمل",
        " جواز سفر رقم ",
        ids["passport"],
        "، ",
        "يعمل" if X.gender == "male" else "تعمل",
        " لديها بوظيفة ",
        job[0 if X.gender == "male" else 1],
        " منذ ",
        ids["date"],
        ".",
    )
    for parts in _renderings_for(c, X, "Employee", f", Passport No. {ids['passport']}"):
        b.seg(*parts)
    if X.gender == "male":
        twin = f"{X.pid}.given" if c.specs["p1"].lookalike == "حسن" else None
        b.seg("ونشهد بأنه ", L("حسن", twin=twin), " السيرة والسلوك طوال مدة عمله لدينا.")
    b.seg("وقد أعطيت هذه الإفادة بناءً على ", "طلبه" if X.gender == "male" else "طلبها", " دون أدنى مسؤولية على الشركة.")
    b.seg("المدير العام: " if S.gender == "male" else "المديرة العامة: ", *_named(S))
    for parts in _renderings_for(c, S, "General Manager"):
        b.seg(*parts)
    b.seg("للاستفسار يرجى التواصل مع ", _hon(S), N(S, "short"), " على البريد الإلكتروني أدناه.")
    email = f"{_slug(S.slots['given'].spelling)[:1]}.{_slug(S.slots['family'].spelling)}@{cslug}.example.com"
    b.seg("Email: ", D(email, "email", [f"{S.pid}.family"]))
    b.seg("التاريخ: ", ids["date2"])
    return b


def _people_doc(
    c: Caster, roles: list[str], render_p: float, forced: dict[str, tuple[Unit, str]] | None = None
) -> list[HPerson]:
    """여러 사람이 나오는 긴 문서의 사람들. 유형을 사람 쌍과 개인에게 나눠 심는다.

    forced: pid → (이름 단위, 같은 문서의 일반 단어). D2처럼 이름을 미리 정할 때 쓴다.
    표기 유무가 유형의 조건인 사람(쌍 유형, 가족 회사 형제, 라벨 없는 표기)은 keep_forms로 묶어
    다른 유형이 건드리지 않게 한다.
    """
    rng = c.rng
    pids = [f"p{i + 1}" for i in range(len(roles))]
    specs = []
    for pid, role in zip(pids, roles, strict=True):
        spec = c.spec(pid, role, forms=["plain"] if rng.random() < render_p else [])
        if forced and pid in forced:
            spec.gender, spec.force["given"], spec.lookalike = "male", forced[pid][0], forced[pid][1]
        specs.append(spec)
    order = list(range(len(specs)))
    rng.shuffle(order)
    pairs = [(order[i], order[i + 1]) for i in range(0, len(order) - 1, 2)]
    for a, b in pairs:
        c.pairs(specs[a], specs[b])
    deps: dict[int, tuple[int, str]] = {b: (a, "son") for a, b in pairs if specs[b].relation == "son_of"}

    def free() -> list[int]:
        return [i for i in order if not specs[i].keep_forms and not specs[i].force]

    if c.has("C2") and len(free()) >= 2:  # 가족 회사: 표기 없는 형제 둘이 회사와 같은 가문명을 쓴다
        i1, i2 = free()[:2]
        for i in (i1, i2):
            specs[i].forms, specs[i].keep_forms = [], True
        deps[i2] = (i1, "sibling")
        specs[i2].relation = "sibling"
    for _ in range(2 if c.take("D4") else 0):  # 라벨 없는 먼 곳 표기만 있는 사람
        if cand := free():
            specs[cand[0]].forms, specs[cand[0]].unlabeled, specs[cand[0]].keep_forms = [], True, True
    for f, form in (("B4", "initials"), ("B6", "partial")):
        while c.has(f):
            cands = [s for s in specs if s.forms in (["plain"], []) and not s.keep_forms and not s.conflict]
            if not cands:
                break
            c.take(f)
            rng.choice(cands).forms = [form]
    plain = [s for s in specs if s.forms == ["plain"]]
    rng.shuffle(plain)
    for s in plain[:5]:
        c.conflict(s)
        c.decorate(s)
    for s in specs:
        if rng.random() < 0.5:
            s.title = True
    if c.take("D5"):
        rng.choice(
            [s for i, s in enumerate(specs) if "family" not in s.force and i not in deps] or specs
        ).family_kind = "nisba"
    built: dict[int, HPerson] = {}

    def ensure(i: int) -> HPerson:
        if i not in built:
            if i in deps:
                j, kind = deps[i]
                pj = ensure(j)
                if kind == "son":
                    c.link(pj, pids[i])
                else:
                    specs[i].force["family"] = pj.slots["family"].unit
            built[i] = c.build(pids[i])
        return built[i]

    for i in order:
        ensure(i)
    return [built[i] for i in range(len(pids))]


def _signature_list(b: HardBuilder, c: Caster, people: list[HPerson]) -> None:
    signers = [p for p in people if c.specs[p.pid].unlabeled]
    if signers:
        b.seg("التوقيعات:")
        for p in signers:
            b.seg(R(p, c.rng.choice(["unlabeled_full", "unlabeled_caps"]), labeled=False))


def _company_line(b: HardBuilder, C: HPerson, people: list[HPerson], prefix: str) -> None:
    b.seg(prefix, R(C, "plain"), " General Trading L.L.C.")
    same = [f"{p.pid}.family" for p in people if p.slots["family"].unit.key == C.slots["family"].unit.key]
    if same:
        b.decoys.append(
            {
                "segment_id": b.segments[-1]["segment_id"],
                "quote": render(C, "plain")[0],
                "kind": "company",
                "resembles": same,
            }
        )


def _family_company(c: Caster, people: list[HPerson]) -> HPerson:
    """C2면 표기 없는 사람(형제가 있으면 형제)의 가문명으로 회사 이름을 짓는다."""
    unrendered = [p for p in people if not c.specs[p.pid].forms and not c.specs[p.pid].unlabeled]
    shared = Counter(p.slots["family"].unit.key for p in unrendered)
    unrendered.sort(key=lambda p: -shared[p.slots["family"].unit.key])
    fam = unrendered[0].slots["family"].unit if unrendered and c.take("C2") else None
    C = make_company(c.rng, c.pool, "c1", fam, set() if fam else c.used)
    c.persons["c1"] = C
    return C


def _cr(c: Caster, ids: dict[str, str]) -> HardBuilder:
    rng = c.rng
    n = rng.randint(7, 9)
    people = _people_doc(c, ["partner"] * n, 0.4)
    C = _family_company(c, people)
    shares = [rng.randint(5, 40) for _ in people]
    same = [f"{p.pid}.family" for p in people if p.slots["family"].unit.key == C.slots["family"].unit.key]
    b = HardBuilder()
    b.seg("مستخرج من السجل التجاري")
    b.seg("الاسم التجاري: ", N(C), " للتجارة العامة ", Z(LLC))
    if same or rng.random() < 0.5:
        _company_line(b, C, people, "Trade name: ")
    if same:
        cslug = _slug(C.slots["family"].spelling)
        b.seg(
            "البريد الإلكتروني: ",
            D(f"info@{cslug}-group.{rng.choice(['example.com', 'example.net'])}", "email", [*same, "c1.family"]),
        )
    b.seg("رقم الرخصة: ", ids["reg"], "، جهة الإصدار: ", Z(AUTHORITY), "، الإمارة: ", Z(rng.choice(CITIES)))
    b.seg("الشكل القانوني: شركة ذات مسؤولية محدودة")
    b.seg("الشركاء:")
    for k, (p, share) in enumerate(zip(people, shares, strict=True), start=1):
        b.seg(f"{k}. ", *_named(p), "، ", _nat(p), " الجنسية، الحصة ", str(share), "٪")
        for parts in _renderings_for(c, p, f"Partner {k}"):
            b.seg(*parts)
    manager = rng.choice([p for p in people if p.gender == "male"] or people)
    b.seg("المدير: " if manager.gender == "male" else "المديرة: ", _hon(manager), N(manager, "short"))
    signer = rng.choice([p for p in people if p is not manager])
    b.seg("المفوض بالتوقيع: " if signer.gender == "male" else "المفوضة بالتوقيع: ", _hon(signer), N(signer, "short"))
    b.seg("تاريخ الإصدار: ", ids["date"])
    _signature_list(b, c, people)
    return b


def _minutes(c: Caster, ids: dict[str, str]) -> HardBuilder:
    rng = c.rng
    n_att = rng.randint(4, 6)
    roles = ["chair", "secretary", *["attendee"] * n_att]
    looks: dict[str, str] = {}  # 일반 단어 → 그 이름을 가진 사람
    forced: dict[str, tuple[Unit, str]] = {}
    if c.take("D2"):
        for word, pid in (("أمين", "p2"), ("عادل", "p3"), ("سليم", "p4")):
            if rng.random() < 0.9 and (u := c.pool.unit(word)):
                looks[word], forced[pid] = pid, (u, word)
    people = _people_doc(c, roles, 0.35, forced)
    chair, sec, attendees = people[0], people[1], people[2:]
    C = _family_company(c, people)
    b = HardBuilder()
    b.seg("محضر اجتماع الجمعية العمومية العادية")
    b.seg("لشركة ", N(C), " للتجارة العامة ", Z(LLC))
    if any(p.slots["family"].unit.key == C.slots["family"].unit.key for p in people) or rng.random() < 0.5:
        _company_line(b, C, people, "Company: ")
    b.seg("عقد الاجتماع في ", Z(rng.choice(CITIES)), " بتاريخ ", ids["date"], " برئاسة ", *_named(chair), ".")
    for parts in _renderings_for(c, chair, "Chairman"):
        b.seg(*parts)
    b.seg("وحضر الاجتماع كل من:")
    for k, p in enumerate(attendees, start=1):
        b.seg(f"{k}. ", *_named(p))
        for parts in _renderings_for(c, p, f"Attendee {k}"):
            b.seg(*parts)
    b.seg("وتولى أمانة السر ", *_named(sec), ".")
    for parts in _renderings_for(c, sec, "Secretary"):
        b.seg(*parts)
    b.seg("وبعد التداول قرر المجتمعون بالإجماع ما يلي:")
    appointee = rng.choice([p for p in attendees if p.gender == "male"] or attendees)
    b.seg("أولًا: الموافقة على تعيين ", _hon(appointee), N(appointee, "short"), " مديرًا للشركة لمدة ثلاث سنوات.")
    if "عادل" in looks or rng.random() < 0.5:
        b.seg(
            "ثانيًا: توزيع الأرباح بشكل ",
            L("عادل", twin=f"{looks['عادل']}.given" if "عادل" in looks else None),
            " بين الشركاء حسب حصصهم.",
        )
    else:
        b.seg("ثانيًا: توزيع الأرباح على الشركاء حسب حصصهم.")
    if "سليم" in looks or rng.random() < 0.5:
        b.seg(
            "ثالثًا: المركز المالي للشركة ",
            L("سليم", twin=f"{looks['سليم']}.given" if "سليم" in looks else None),
            " ولا توجد عليها التزامات متأخرة.",
        )
    else:
        b.seg("ثالثًا: اعتماد الميزانية العمومية للسنة المالية المنتهية.")
    delegate = rng.choice([p for p in attendees if p is not appointee])
    b.seg("رابعًا: تفويض ", _hon(delegate), N(delegate, "short"), " بالتوقيع على محضر الاجتماع وتقديمه للجهات المختصة.")
    if chair.title is not None and rng.random() < 0.5:
        b.seg("رئيس الاجتماع: ", T(chair.title), " ", N(chair, "title_short"))
    else:
        b.seg("رئيس الاجتماع: ", N(chair, "short"))
    b.seg(L("أمين", twin=f"{looks['أمين']}.given" if "أمين" in looks else None), " السر: ", N(sec, "short"))
    _signature_list(b, c, people)
    return b


TEMPLATE_FUNCS = {"poa": _poa, "letter": _letter, "cr": _cr, "minutes": _minutes}


# ---------- 정답(gold 형식 2) ----------


def _slot_rules(b: HardBuilder, persons: dict[str, HPerson]) -> dict[tuple[str, str], dict]:
    """정답 규칙: 사람·이름 부분마다 기대 처분."""
    out: dict[tuple[str, str], dict] = {}
    for p in persons.values():
        rens = [r for r in b.renderings if r["person_id"] == p.pid]
        for slot in p.order():
            full = [r for r in rens if r["slots"].get(slot)]
            keys: dict[str, str] = {}
            for r in full:
                keys.setdefault(strict_key(r["slots"][slot]), r["slots"][slot])
            rule: dict[str, Any] = {
                "expected": "adopt" if len(keys) == 1 else "hold",
                "expected_spelling": next(iter(keys.values())) if len(keys) == 1 else None,
                "evidence": [{"segment_id": r["segment_id"], "quote": r["quote"]} for r in full]
                if len(keys) == 1
                else [],
                "must_include": sorted(keys.values()) if len(keys) >= 2 else [],
                "forms": sorted({r["form"] for r in full}),
                "initial": any(slot in r["initial_slots"] for r in rens),
                "omitted": bool(rens) and not full and not any(slot in r["initial_slots"] for r in rens),
                "all_unlabeled": bool(full) and all(not r["labeled"] for r in full),
                "conflict_person": any(
                    len({strict_key(r["slots"][s]) for r in rens if r["slots"].get(s)}) >= 2 for s in p.order()
                ),
            }
            out[(p.pid, slot)] = rule
    return out


def _tag_units(
    units: list[dict], persons: dict[str, HPerson], rules: dict, b: HardBuilder, look_keys: set[str]
) -> None:
    by_key: dict[str, list[tuple[str, str]]] = defaultdict(list)  # 같은 아랍어 이름 부분을 가진 사람(회사 제외)
    for p in persons.values():
        if p.kind != "person":
            continue
        for s, hs in p.slots.items():
            by_key[hs.unit.key].append((p.pid, s))
    decoy_targets = {t for d in b.decoys for t in d["resembles"]}
    for u in units:
        pid, slot, rule = u["person_id"], u["slot"], rules[(u["person_id"], u["slot"])]
        p = persons[pid]
        tags: set[str] = set()
        others = [(q, s) for q, s in by_key[p.slots[slot].unit.key] if q != pid]
        if rule["expected"] == "hold" and any(rules[o]["expected"] == "adopt" for o in others):
            tags.add("A1")
        if rule["expected"] == "adopt" and any(
            rules[o]["expected"] == "adopt"
            and strict_key(rules[o]["expected_spelling"]) != strict_key(rule["expected_spelling"])
            for o in others
        ):
            tags.add("A2")
        if u["mention"] in ("short", "title_short"):
            tags.add("A3")
        if rule["expected"] == "adopt" and "plain" not in rule["forms"]:
            forms = set(rule["forms"])
            if forms & {"caps", "unlabeled_caps"}:
                tags.add("B1")
            if forms & {"reversed_comma", "surname_given"}:
                tags.add("B2")
            if "mrz" in forms:
                tags.add("B3")
        if rule["expected"] == "hold" and rule["initial"]:
            tags.add("B4")
        if rule["expected"] == "adopt" and re.match(r"^El\b", rule["expected_spelling"] or ""):
            tags.add("B5")
        if rule["expected"] == "hold" and rule["omitted"]:
            tags.add("B6")
        if rule["expected"] == "hold" and p.kind == "person":
            mine = p.slots[slot].unit
            for q in persons.values():
                if q.pid == pid:
                    continue
                for s2, hs2 in q.slots.items():
                    r2 = rules[(q.pid, s2)]
                    if (
                        r2["expected"] == "adopt"
                        and hs2.unit.key != mine.key
                        and any(match_spelling(r2["expected_spelling"], v) for v in mine.plausible)
                    ):
                        tags.add("C1")
        if rule["expected"] == "hold" and f"{pid}.{slot}" in decoy_targets:
            tags.add("C2")
        if rule["must_include"]:
            tags.add("C3")
        if p.slots[slot].unit.key in look_keys:
            tags.add("D2")
        if (
            " " in p.slots[slot].unit.arabic
            or slot == "ggf"
            or (p.title and u["mention"] != "short" and slot == "given")
        ):
            tags.add("D3")
        if rule["expected"] == "adopt" and rule["all_unlabeled"]:
            tags.add("D4")
        if p.nisba and slot == "family":
            tags.add("D5")
        u["case_types"] = sorted(tags)
        rel = p.relation.startswith("son_of") and rule["expected"] == "hold" and slot in ("family", "father")
        u["arguable"] = bool(
            rel
            or u["mention"] in ("short", "title_short")
            or (rule["conflict_person"] and not rule["must_include"])
            or (rule["expected"] == "adopt" and rule["all_unlabeled"])
        )


def build_gold(b: HardBuilder, persons: dict[str, HPerson]) -> dict:
    tokens = tokenize(b.segments)
    by_id = {t["id"]: t for t in tokens}
    rules = _slot_rules(b, persons)
    names = []
    units_all: list[dict] = []
    first_ren: dict[str, dict] = {}
    for r in b.renderings:
        first_ren.setdefault(r["person_id"], {"segment_id": r["segment_id"], "quote": r["quote"]})
    for i, m in enumerate(b.mentions, start=1):
        p: HPerson = m["person"]
        ids = tokens_in_span(tokens, m["segment_id"], *m["span"])
        units = []
        seen: set[int] = set()
        for slot, (s, e) in m["slots"].items():
            tids = tokens_in_span(tokens, m["segment_id"], s, e)
            if not tids or seen & set(tids) or any(by_id[t]["script"] != "ar" for t in tids):
                raise _Retry(f"bad unit tokens {slot} {tids}")
            seen |= set(tids)
            hs = p.slots[slot]
            rule = rules[(p.pid, slot)]
            unit = {
                "token_id": tids[-1],
                "token_ids": tids,
                "unit_id": f"n{i}.{slot}",
                "slot": slot,
                "arabic": hs.unit.arabic,
                "position": POSITION[slot],
                "english_variants": hs.unit.plausible,
                "raw_variants": hs.unit.raw,
                "english_used": hs.spelling,
                "expected": rule["expected"],
                "expected_spelling": rule["expected_spelling"],
                "evidence": rule["evidence"],
                "must_include": rule["must_include"],
                "person_id": p.pid,
                "mention": m["mention"],
            }
            units.append(unit)
        names.append(
            {
                "occurrence_id": f"n{i}",
                "role": p.role,
                "person_id": p.pid,
                "mention": m["mention"],
                "segment_id": m["segment_id"],
                "span": list(m["span"]),
                "token_ids": ids,
                "arabic_full": " ".join(t for t, _ in p.arabic_pieces(m["mention"])),
                "english_full": " ".join(p.slots[s].spelling for s in m["slots"]),
                "evidence": first_ren.get(p.pid),
                "tokens": units,
            }
        )
        units_all.extend(units)
    look_tokens = []
    look_keys = set()
    for lk in b.lookalikes:
        sid, s, e = lk["span"]
        for t in tokens_in_span(tokens, sid, s, e):
            look_tokens.append({"token_id": t, "kind": lk["kind"], "twin": lk["twin"]})
            if lk["twin"]:
                look_keys.add(normalize_key(by_id[t]["text"]))
    for p in persons.values():  # D5: 가문명과 같은 국적 형용사
        if p.nisba:
            for m in b.mentions:
                if m["person"] is p:
                    nat_tokens = [
                        t
                        for t in tokens
                        if t["segment_id"] == m["segment_id"]
                        and t["script"] == "ar"
                        and normalize_key(t["text"]) == normalize_key(_nat(p))
                    ]
                    look_tokens += [
                        {"token_id": t["id"], "kind": "nationality", "twin": f"{p.pid}.family"} for t in nat_tokens
                    ]
    _tag_units(units_all, persons, rules, b, look_keys)
    for n in names:
        for u in n["tokens"]:
            u.pop("person_id")
            u.pop("mention")
    titles = sorted({t for sid, s, e in b.titles for t in tokens_in_span(tokens, sid, s, e)})
    neutral = sorted({t for sid, s, e in b.neutral for t in tokens_in_span(tokens, sid, s, e)} | set(titles))
    return {
        "format_version": GOLD_FORMAT,
        "names": names,
        "persons": [
            {
                "person_id": p.pid,
                "kind": p.kind,
                "role": p.role,
                "gender": p.gender,
                "relation": p.relation,
                "slots": {s: {"arabic": hs.unit.arabic, "spelling": hs.spelling} for s, hs in p.slots.items()},
                "renderings": [r for r in b.renderings if r["person_id"] == p.pid],
            }
            for p in persons.values()
        ],
        "decoys": b.decoys,
        "neutral_token_ids": neutral,
        "title_token_ids": titles,
        "lookalikes": sorted(look_tokens, key=lambda x: x["token_id"]),
        "lookalike_token_ids": sorted({x["token_id"] for x in look_tokens}),
    }


# ---------- 검사 ----------


def validate_doc(doc: dict) -> list[str]:
    """문서 하나의 불변 조건. 비어 있으면 통과."""
    problems: list[str] = []
    seg_text = {s["segment_id"]: s["text"] for s in doc["segments"]}
    gold = doc["gold"]
    per_seg: dict[str, list[dict]] = defaultdict(list)
    for occ in gold["names"]:
        for u in occ["tokens"]:
            per_seg[occ["segment_id"]].append(u)
            adopt = u["expected"] == "adopt"
            if adopt != bool(u["expected_spelling"]) or adopt != bool(u["evidence"]):
                problems.append(f"{u['unit_id']}: expected/spelling/evidence mismatch")
            for ev in u["evidence"]:
                if ev["quote"] not in seg_text.get(ev["segment_id"], ""):
                    problems.append(f"{u['unit_id']}: quote not in segment")
                if not strict_words_in_quote(u["expected_spelling"], ev["quote"]):
                    problems.append(f"{u['unit_id']}: expected spelling not in quote (rule v2)")
            for s in [u["english_used"], *u["must_include"], *([u["expected_spelling"]] if adopt else [])]:
                if not ASCII_NAME.fullmatch(s):
                    problems.append(f"{u['unit_id']}: non-ASCII spelling {s!r}")
    for sid, units in per_seg.items():
        for i, a in enumerate(units):
            for b in units[i + 1 :]:
                same = normalize_key(a["arabic"]) == normalize_key(b["arabic"])
                close = any(match_spelling(x, y) for x in a["english_variants"] for y in b["english_variants"])
                if same or close:
                    problems.append(f"{sid}: units {a['unit_id']} and {b['unit_id']} look alike in one segment")
    persons = {p["person_id"]: p for p in gold["persons"]}
    shorts = Counter(
        (p["slots"]["given"]["arabic"], p["slots"]["family"]["arabic"])
        for p in persons.values()
        if p["kind"] == "person"
    )
    givens = Counter(p["slots"]["given"]["arabic"] for p in persons.values() if p["kind"] == "person")
    for occ in gold["names"]:
        p = persons[occ["person_id"]]
        if occ["mention"] == "short" and shorts[(p["slots"]["given"]["arabic"], p["slots"]["family"]["arabic"])] > 1:
            problems.append(f"{occ['occurrence_id']}: short mention is not unique")
        if occ["mention"] == "title_short" and givens[p["slots"]["given"]["arabic"]] > 1:
            problems.append(f"{occ['occurrence_id']}: title mention is not unique")
    for p in persons.values():
        for r in p["renderings"]:
            if r["form"] == "mrz" and len(r["quote"]) != MRZ_LEN:
                problems.append(f"{p['person_id']}: MRZ length {len(r['quote'])}")
            if not r["labeled"]:
                full = [q for q in persons.values() if q["kind"] == "person" and q["slots"] == p["slots"]]
                if len(full) > 1 or set(r["slots"]) != set(p["slots"]):
                    problems.append(f"{p['person_id']}: unlabeled rendering is not a unique full name")
    return problems


# ---------- 생성 ----------


def _quota(split_n: int) -> dict[str, int]:
    return {k: max(1, round(v * split_n / DOC_COUNTS["eval"])) for k, v in QUOTAS.items()}


def _choose_features(
    rng: random.Random, template: str, counts: Counter, quota: dict[str, int], greedy: bool = False
) -> set[str]:
    """문서 하나에 심을 유형. 앞쪽 문서는 모자란 유형에 가중치를 준 무작위, 뒤쪽 문서는 가장 모자란 유형부터."""
    supported = sorted(TEMPLATE_FEATURES[template])
    k = rng.randint(3, 5) if template in ("poa", "letter") else rng.randint(6, 9)
    # 최소 수량의 1.35배를 목표로 둬서 문서 수가 정해진 상태에서도 최소 수량을 넘기게 한다
    ratio = {f: counts[f] / (1.35 * quota[f]) for f in supported}
    if greedy:
        return set(sorted(supported, key=lambda f: (ratio[f], rng.random()))[:k])
    weights = {f: 1.0 / (1.0 + ratio[f]) ** 3 for f in supported}
    chosen: set[str] = set()
    while len(chosen) < min(k, len(supported)):
        rest = [f for f in supported if f not in chosen]
        chosen.add(rng.choices(rest, weights=[weights[f] for f in rest], k=1)[0])
    return chosen


def generate_doc(pool: HardPool, split: str, index: int, seed: int, template: str, feats: set[str]) -> dict:
    rng = random.Random(seed * 10007 + index)
    last: list[str] = []
    for _ in range(80):
        c = Caster(rng, pool, feats, long=template in ("cr", "minutes"))
        try:
            b = TEMPLATE_FUNCS[template](c, _placeholder_ids(rng))
            gold = build_gold(b, c.persons)
        except _Retry as exc:
            last = [str(exc)]
            continue
        doc = {
            "doc_id": f"{PREFIX.get(split, split)}_{index:03d}",
            "synthetic": True,
            "notice": NOTICE,
            "doc_type": template,
            "bilingual": bool(b.renderings or b.decoys),
            "segments": b.segments,
            "features_planned": sorted(feats),
            "meta": {
                "generator": GENERATOR_VERSION,
                "gold_format": GOLD_FORMAT,
                "seed": seed,
                "split": split,
                "index": index,
                "identifier_formats": "placeholder (no sourced format)",
                "arabic_reviewed_by_human": False,
            },
            "gold": gold,
        }
        last = validate_doc(doc)
        if not last:
            units = [u for occ in gold["names"] for u in occ["tokens"]]
            tags = sorted(
                {t for u in units for t in u["case_types"]} | ({"D1"} if len(units) > LONG_DOC_UNITS else set())
            )
            doc["case_types"] = tags
            return doc
    raise RuntimeError(f"{split} {index} {template}: could not satisfy constraints: {last[:3]}")


def unit_case_counts(docs: list[dict]) -> Counter:
    counts: Counter = Counter()
    for doc in docs:
        for occ in doc["gold"]["names"]:
            for u in occ["tokens"]:
                counts.update(u["case_types"])
    return counts


def quota_report(docs: list[dict], split_n: int | None = None) -> dict:
    """유형별 수량과 최소 수량 충족 여부."""
    n = split_n or len(docs)
    quota = _quota(n)
    counts = unit_case_counts(docs)
    units = [u for d in docs for occ in d["gold"]["names"] for u in occ["tokens"]]
    looks = sum(len(d["gold"]["lookalike_token_ids"]) for d in docs)
    long_docs = sum("D1" in d.get("case_types", []) for d in docs)
    hard = sum(bool(u["case_types"]) for u in units)
    adopt = sum(u["expected"] == "adopt" for u in units)
    d1_min = max(1, round(D1_MIN_DOCS * n / DOC_COUNTS["eval"]))
    look_min = max(1, round(LOOKALIKE_MIN * n / DOC_COUNTS["eval"]))
    short = {k: (counts[k], q) for k, q in quota.items() if counts[k] < q}
    if long_docs < d1_min:
        short["D1"] = (long_docs, d1_min)
    if looks < look_min:
        short["lookalike_tokens"] = (looks, look_min)
    share = hard / len(units) if units else 0.0
    adopt_share = adopt / len(units) if units else 0.0
    return {
        "n_docs": len(docs),
        "n_units": len(units),
        "n_arabic_tokens": sum(len(u["token_ids"]) for u in units),
        "case_counts": dict(sorted(counts.items())),
        "quota": quota,
        "long_docs": long_docs,
        "lookalike_tokens": looks,
        "hard_share": round(share, 3),
        "adopt_share": round(adopt_share, 3),
        "arguable": sum(bool(u.get("arguable")) for u in units),
        "short": short,
        "ok": not short and share >= MIN_HARD_SHARE and ADOPT_SHARE[0] <= adopt_share <= ADOPT_SHARE[1],
    }


def build_docs(pool: HardPool, split: str, n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    quota = _quota(n)
    counts: Counter = Counter()
    docs = []
    for i in range(1, n + 1):
        template = TEMPLATE_CYCLE[(i - 1) % len(TEMPLATE_CYCLE)]
        feats = _choose_features(rng, template, counts, quota, greedy=i > 0.5 * n)
        doc = generate_doc(pool, split, i, seed, template, feats)
        counts.update(unit_case_counts([doc]))
        docs.append(doc)
    return docs


def generate(
    pool_path: str | Path,
    out_dir: str | Path,
    split: str,
    n: int | None = None,
    seed: int | None = None,
    check_quota: bool | None = None,
) -> tuple[list[Path], dict]:
    raw = json.loads(Path(pool_path).read_text(encoding="utf-8"))
    pool = HardPool(raw)
    n = n or DOC_COUNTS[split]
    seed = SEEDS[split] if seed is None else seed
    docs = build_docs(pool, split, n, seed)
    report = quota_report(docs)
    # 최소 수량은 eval에만 강제한다. dev 20개는 프롬프트·형식 점검용이라 비율로 줄인 수량을 참고로만 본다
    if (split == "eval" if check_quota is None else check_quota) and not report["ok"]:
        raise RuntimeError(
            f"quota not met: {report['short']}, hard_share {report['hard_share']}, adopt_share {report['adopt_share']}"
        )
    out = Path(out_dir) / split
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for doc in docs:
        path = out / f"{doc['doc_id']}.json"
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        paths.append(path)
    # 문서 폴더 밖에 둔다. 실험은 폴더의 *.json을 모두 문서로 읽는다
    (Path(out_dir) / f"quota_{split}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    return paths, report


# ---------- 확인용 출력 ----------


def describe(doc: dict) -> str:
    """구간마다 원문과, 그 구간의 이름 부분별 기대 처분·유형을 사람이 읽게 적는다(inspect-gold)."""
    gold = doc["gold"]
    units_by_seg: dict[str, list[dict]] = defaultdict(list)
    for occ in gold["names"]:
        for u in occ["tokens"]:
            units_by_seg[occ["segment_id"]].append({**u, "person_id": occ["person_id"], "mention": occ["mention"]})
    marks: dict[str, list[str]] = defaultdict(list)
    for p in gold["persons"]:
        for r in p["renderings"]:
            tag = "" if r["labeled"] else " 라벨 없음"
            marks[r["segment_id"]].append(f"표기 {p['person_id']} {r['form']}{tag}")
    for d in gold["decoys"]:
        marks[d["segment_id"]].append(f"함정 {d['kind']} → {', '.join(d['resembles'])}")
    lines = [
        f"{doc['doc_id']} ({doc['doc_type']}) 유형: {', '.join(doc.get('case_types', []))}",
        "사람: "
        + "; ".join(
            f"{p['person_id']}({p['role']}{', ' + p['relation'] if p['relation'] else ''}) "
            + " ".join(f"{v['arabic']}={v['spelling']}" for v in p["slots"].values())
            for p in gold["persons"]
        ),
    ]
    for seg in doc["segments"]:
        sid = seg["segment_id"]
        lines.append(f"[{sid}] {seg['text']}")
        for m in marks.get(sid, []):
            lines.append(f"      ({m})")
        for u in units_by_seg.get(sid, []):
            exp = f"확정 {u['expected_spelling']}" if u["expected"] == "adopt" else "보류"
            if u["must_include"]:
                exp += f" (후보에 {' / '.join(u['must_include'])})"
            flags = " ".join(u["case_types"]) + (" arguable" if u.get("arguable") else "")
            lines.append(f"      - {u['person_id']}.{u['slot']} {u['arabic']}: {exp}  [{flags}]")
    return "\n".join(lines)
