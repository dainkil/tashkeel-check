"""업무 규칙 기반 합성 문서 생성기(계획 5.2절). 결정적이다(seed 고정).

- 이름은 Wikidata 이름 단위를 무작위로 조합한다. 조합한 전체 이름이 Wikidata 레이블과 같으면 버린다.
- 서식은 출처가 있는 규칙(R1~R5)만 반영한다. 신분증·등록 번호는 형식 출처가 없어 자리표시 숫자를 쓴다.
- 정답 라벨(gold)은 생성기가 같이 낸다. 그래프는 gold를 대조 단계에서만 쓴다.
- 템플릿의 아랍어 문장은 사람이 검수하지 않았다.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

from ..text import Segment, normalize_key, tokenize, tokens_in_span

GENERATOR_VERSION = "synthetic-v0"
NOTICE = "SYNTHETIC: 합성 데이터. 실존 인물·회사·서류가 아니다. 이름은 Wikidata 이름 단위를 무작위로 조합했다."
RULES = {
    "R1": "위임장은 아랍어 또는 아랍어·영어 이중 언어로 쓴다 (Virtuzone, ADGM 공증 FAQ)",
    "R2": "위임인·대리인 이름은 Emirates ID 또는 여권 표기와 같아야 한다 (ADGM 공증 FAQ)",
    "R3": "법인 당사자는 상호, 법인 형태, 면허 발급 기관, 등록 번호, 주소를 적는다 (ADGM 공증 FAQ)",
    "R4": "걸프 인명은 이름 + بن/بنت + 아버지 이름 (+ 할아버지 이름) + 가문명 구조가 흔하다 (Wikidata 레이블)",
    "R5": "같은 아랍어 이름에 영문 표기가 여럿 있다 (Wikidata 별칭)",
}
NATIONALITIES = [
    ("إماراتي", "إماراتية"),
    ("سعودي", "سعودية"),
    ("قطري", "قطرية"),
    ("كويتي", "كويتية"),
    ("بحريني", "بحرينية"),
    ("عماني", "عمانية"),
]
CITIES = ["دبي", "أبوظبي", "الشارقة"]
JOBS = [("محاسب", "محاسبة"), ("مهندس", "مهندسة"), ("مندوب مبيعات", "مندوبة مبيعات")]
AUTHORITY = "دائرة التنمية الاقتصادية"
COUNTRY = "الإمارات العربية المتحدة"
LLC = "ذ.م.م"
CONNECTOR_KEYS = {normalize_key(w) for w in ("بن", "بنت")}


@dataclass
class Part:
    arabic: str
    english: str
    position: str  # given | middle | family | conn
    variants: list[str] = field(default_factory=list)


@dataclass
class Name:
    parts: list[Part]

    @property
    def arabic(self) -> str:
        return " ".join(p.arabic for p in self.parts)

    @property
    def english(self) -> str:
        return " ".join(p.english for p in self.parts)


class NamePool:
    def __init__(self, pool: dict):
        self.full_names = set(pool["full_names"])
        self.given: dict[str, list[tuple[str, dict]]] = {"male": [], "female": []}
        self.middle: list[tuple[str, dict]] = []
        self.family: list[tuple[str, dict]] = []
        for key, t in pool["tokens"].items():
            if " " in t["arabic"] or not t["english_variants"]:
                continue
            pos, gen = t["positions"], t["genders"]
            male, female = gen.get("male", 0), gen.get("female", 0)
            if pos.get("family") and t["arabic"].startswith("ال"):
                self.family.append((key, t))
            elif pos.get("given") or pos.get("middle"):
                if male >= female and male > 0:
                    self.given["male"].append((key, t))
                    self.middle.append((key, t))
                elif female > male:
                    self.given["female"].append((key, t))
        for name, lst in [
            ("male given", self.given["male"]),
            ("female given", self.given["female"]),
            ("family", self.family),
        ]:
            if not lst:
                raise ValueError(f"name pool has no {name} names")

    @staticmethod
    def _pick(rng: random.Random, lst: list[tuple[str, dict]], exclude: set[str]) -> tuple[str, dict]:
        choices = [x for x in lst if x[0] not in exclude] or lst
        weights = [sum(t["english_variants"].values()) for _, t in choices]
        return rng.choices(choices, weights=weights, k=1)[0]

    @staticmethod
    def _part(rng: random.Random, t: dict, position: str) -> Part:
        variants = list(t["english_variants"])
        english = rng.choices(variants, weights=list(t["english_variants"].values()), k=1)[0]
        return Part(arabic=t["arabic"], english=english, position=position, variants=variants)

    def person(self, rng: random.Random, gender: str, exclude: set[str]) -> Name:
        for _ in range(100):
            used = set(exclude)
            gk, g = self._pick(rng, self.given[gender], used)
            used.add(gk)
            fk, f = self._pick(rng, self.middle, used)
            used.add(fk)
            famk, fam = self._pick(rng, self.family, used)
            with_conn = rng.random() < 0.5
            conn_en = rng.choice(["bin", "Bin"]) if gender == "male" else rng.choice(["bint", "Bint"])
            parts = [self._part(rng, g, "given")]
            if with_conn:
                parts.append(Part("بن" if gender == "male" else "بنت", conn_en, "conn"))
            parts.append(self._part(rng, f, "middle"))
            if rng.random() < 0.3:
                gfk, gf = self._pick(rng, self.middle, used | {famk})
                if with_conn:
                    parts.append(Part("بن", rng.choice(["bin", "Bin"]), "conn"))
                parts.append(self._part(rng, gf, "middle"))
            parts.append(self._part(rng, fam, "family"))
            name = Name(parts)
            if normalize_key(name.arabic) not in self.full_names:
                return name
        raise RuntimeError("could not build a name that is not in Wikidata")

    def company(self, rng: random.Random, exclude: set[str]) -> Name:
        _, fam = self._pick(rng, self.family, exclude)
        return Name([self._part(rng, fam, "family")])


@dataclass
class _Mark:
    kind: str  # name | en_name | neutral
    value: Name | str
    role: str = ""
    suffix: str = ""

    def name(self) -> Name:
        if not isinstance(self.value, Name):
            raise TypeError(f"{self.kind} mark needs a Name, got {type(self.value).__name__}")
        return self.value


def _name(role: str, n: Name) -> _Mark:
    return _Mark("name", n, role)


def _en(role: str, n: Name, suffix: str = "") -> _Mark:
    return _Mark("en_name", n, role, suffix)


def _neutral(text: str) -> _Mark:
    return _Mark("neutral", text)


class _Builder:
    def __init__(self) -> None:
        self.segments: list[Segment] = []
        self.name_spans: list[dict] = []
        self.neutral_spans: list[tuple[str, int, int]] = []
        self.evidence: dict[str, dict] = {}

    def seg(self, *parts: object) -> str:
        sid = f"s{len(self.segments) + 1:02d}"
        text = ""
        for p in parts:
            if isinstance(p, _Mark):
                start = len(text)
                if p.kind == "name":
                    text += p.name().arabic
                    self.name_spans.append(
                        {"role": p.role, "name": p.name(), "segment_id": sid, "span": (start, len(text))}
                    )
                elif p.kind == "en_name":
                    quote = p.name().english + p.suffix
                    text += quote
                    self.evidence[p.role] = {"segment_id": sid, "quote": quote}
                else:
                    text += str(p.value)
                    self.neutral_spans.append((sid, start, len(text)))
            else:
                text += str(p)
        self.segments.append(Segment(segment_id=sid, text=text))
        return sid


def _placeholder_ids(rng: random.Random) -> dict[str, str]:
    return {
        "passport": f"{rng.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{rng.randint(1000000, 9999999)}",
        "id": str(rng.randint(10000000, 99999999)),
        "reg": str(rng.randint(100000, 999999)),
        "date": f"{rng.randint(1, 28):02d}/{rng.randint(1, 12):02d}/2026",
        "date2": f"{rng.randint(1, 28):02d}/{rng.randint(1, 12):02d}/2026",
    }


def _poa(rng: random.Random, pool: NamePool, bilingual: bool) -> _Builder:
    gp, ga = rng.choice(["male", "female"]), rng.choice(["male", "female"])
    mp, ma = gp == "male", ga == "male"
    P = pool.person(rng, gp, set())
    A = pool.person(rng, ga, {normalize_key(p.arabic) for p in P.parts})
    C = pool.company(rng, {normalize_key(p.arabic) for p in P.parts + A.parts})
    natp, nata = rng.choice(NATIONALITIES), rng.choice(NATIONALITIES)
    ids = _placeholder_ids(rng)
    b = _Builder()
    b.seg("وكالة خاصة")
    b.seg(
        "إنه في يوم ",
        ids["date"],
        " حضر أمام الكاتب العدل ",
        "السيد " if mp else "السيدة ",
        _name("principal", P),
        "، ",
        natp[0 if mp else 1],
        " الجنسية، ",
        "ويحمل" if mp else "وتحمل",
        " جواز سفر رقم ",
        ids["passport"],
        ".",
    )
    if bilingual:
        b.seg("Principal: ", _en("principal", P), ", Passport No. ", ids["passport"])
    b.seg(
        "وذلك بصفته مديرًا" if mp else "وذلك بصفتها مديرة",
        " لشركة ",
        _name("company", C),
        " للتجارة العامة ",
        _neutral(LLC),
        "، المرخصة من ",
        _neutral(AUTHORITY),
        " برقم ",
        ids["reg"],
        "، وعنوانها ",
        _neutral(rng.choice(CITIES)),
        "، ",
        _neutral(COUNTRY),
        ".",
    )
    if bilingual:
        b.seg("Company: ", _en("company", C, " General Trading"), " L.L.C., Registration No. ", ids["reg"])
    b.seg(
        "وقرر أنه وكّل " if mp else "وقررت أنها وكّلت ",
        "السيد " if ma else "السيدة ",
        _name("agent", A),
        "، ",
        nata[0 if ma else 1],
        " الجنسية، ",
        "ويحمل" if ma else "وتحمل",
        " بطاقة هوية رقم ",
        ids["id"],
        ".",
    )
    if bilingual:
        b.seg("Attorney: ", _en("agent", A), ", ID No. ", ids["id"])
    b.seg(
        "للقيام نيابة ",
        "عنه" if mp else "عنها",
        " بمراجعة الجهات الحكومية والتوقيع على الطلبات والمستندات المتعلقة بالشركة واستلام الشهادات والتراخيص.",
    )
    b.seg("الموكل: " if mp else "الموكلة: ", _name("principal", P))
    b.seg("الوكيل: " if ma else "الوكيلة: ", _name("agent", A))
    b.seg("التوقيع: ____________")
    return b


def _letter(rng: random.Random, pool: NamePool, bilingual: bool) -> _Builder:
    gx, gs = rng.choice(["male", "female"]), rng.choice(["male", "female"])
    mx, ms = gx == "male", gs == "male"
    X = pool.person(rng, gx, set())
    S = pool.person(rng, gs, {normalize_key(p.arabic) for p in X.parts})
    C = pool.company(rng, {normalize_key(p.arabic) for p in X.parts + S.parts})
    nat, job = rng.choice(NATIONALITIES), rng.choice(JOBS)
    ids = _placeholder_ids(rng)
    b = _Builder()
    b.seg("إقرار")
    b.seg(
        "تقر شركة ",
        _name("company", C),
        " للتجارة العامة ",
        _neutral(LLC),
        "، المرخصة من ",
        _neutral(AUTHORITY),
        " برقم ",
        ids["reg"],
        "، وعنوانها ",
        _neutral(rng.choice(CITIES)),
        "، ",
        _neutral(COUNTRY),
        "،",
    )
    if bilingual:
        b.seg("Company: ", _en("company", C, " General Trading"), " L.L.C., Registration No. ", ids["reg"])
    b.seg(
        "بأن ",
        "السيد " if mx else "السيدة ",
        _name("employee", X),
        "، ",
        nat[0 if mx else 1],
        " الجنسية، ",
        "ويحمل" if mx else "وتحمل",
        " جواز سفر رقم ",
        ids["passport"],
        "، ",
        "يعمل" if mx else "تعمل",
        " لديها بوظيفة ",
        job[0 if mx else 1],
        " منذ ",
        ids["date"],
        ".",
    )
    if bilingual:
        b.seg("Employee: ", _en("employee", X), ", Passport No. ", ids["passport"])
    b.seg("وقد أعطي هذا الإقرار بناءً على ", "طلبه" if mx else "طلبها", " دون أدنى مسؤولية على الشركة.")
    b.seg("المفوض بالتوقيع: " if ms else "المفوضة بالتوقيع: ", _name("signatory", S))
    if bilingual:
        b.seg("Authorized signatory: ", _en("signatory", S))
    b.seg("الصفة: ", "مدير" if ms else "مديرة")
    b.seg("التاريخ: ", ids["date2"])
    return b


def _gold(b: _Builder) -> dict:
    tokens = tokenize(b.segments)
    by_id = {t["id"]: t for t in tokens}
    names = []
    for i, ns in enumerate(b.name_spans, start=1):
        ids = tokens_in_span(tokens, ns["segment_id"], *ns["span"])
        name_ids = [t for t in ids if normalize_key(by_id[t]["text"]) not in CONNECTOR_KEYS]
        parts = [p for p in ns["name"].parts if p.position != "conn"]
        if len(name_ids) != len(parts):
            raise RuntimeError(f"token/name mismatch in {ns}")
        names.append(
            {
                "occurrence_id": f"n{i}",
                "role": ns["role"],
                "segment_id": ns["segment_id"],
                "span": list(ns["span"]),
                "token_ids": ids,
                "arabic_full": ns["name"].arabic,
                "english_full": ns["name"].english,
                "tokens": [
                    {
                        "token_id": tid,
                        "arabic": by_id[tid]["text"],
                        "position": p.position,
                        "english_variants": p.variants,
                        "english_used": p.english,
                    }
                    for tid, p in zip(name_ids, parts, strict=True)
                ],
                "evidence": b.evidence.get(ns["role"]),
            }
        )
    neutral = sorted({t for sid, s, e in b.neutral_spans for t in tokens_in_span(tokens, sid, s, e)})
    return {"names": names, "neutral_token_ids": neutral}


def generate(
    pool_path: str | Path, out_dir: str | Path, split: str, n: int, seed: int, bilingual_ratio: float = 0.5
) -> list[Path]:
    pool = NamePool(json.loads(Path(pool_path).read_text(encoding="utf-8")))
    rng = random.Random(seed)
    out = Path(out_dir) / split
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(1, n + 1):
        doc_type = "poa" if i % 2 else "company_letter"
        bilingual = rng.random() < bilingual_ratio
        b = (_poa if doc_type == "poa" else _letter)(rng, pool, bilingual)
        doc = {
            "doc_id": f"{split}_{i:03d}",
            "synthetic": True,
            "notice": NOTICE,
            "doc_type": doc_type,
            "bilingual": bilingual,
            "segments": b.segments,
            "meta": {
                "generator": GENERATOR_VERSION,
                "seed": seed,
                "split": split,
                "index": i,
                "rules": ["R1", "R2", "R3", "R4", "R5"],
                "identifier_formats": "placeholder (no sourced format)",
                "arabic_reviewed_by_human": False,
            },
            "gold": _gold(b),
        }
        path = out / f"{doc['doc_id']}.json"
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        paths.append(path)
    return paths


def make_sample_bundle(doc_path: str | Path, out_dir: str | Path) -> list[Path]:
    """단계 2 묶음 검색 틀(ADR-007)을 시험할 합성 참고 자료. 서식은 예시일 뿐 실제 서류 형식이 아니다."""
    doc = json.loads(Path(doc_path).read_text(encoding="utf-8"))
    person = next(n for n in doc["gold"]["names"] if n["role"] != "company")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = {
        "id_excerpt.txt": f"{NOTICE}\n(예시 서식)\nالاسم: {person['arabic_full']}\nName: {person['english_full']}\n",
        "previous_letter_en.txt": (
            f"{NOTICE}\nDear {person['english_full']},\nWe confirm receipt of your documents for {doc['doc_id']}.\n"
        ),
    }
    paths = []
    for name, text in files.items():
        p = out / name
        p.write_text(text, encoding="utf-8")
        paths.append(p)
    return paths
