"""EXP-001 main 보조 분석(사후, 규칙 변경 없음): 단위 부트스트랩 95% 구간, 빈도 상위·하위(계획 6.1절의 나눠 보기)."""
import json
import random
import statistics

from tashkeel_check.experiments.exp001 import collect_units

rows = [json.loads(line) for line in open("results/exp001/exp001_main_units.jsonl", encoding="utf-8")]
freq = {u["key"]: sum(u["positions"].values()) for u in collect_units("data/wikidata/gcc_persons.json")[0]}
rng = random.Random(0)
vals = sorted(sum(r["covered_dialect"] for r in rng.choices(rows, k=len(rows))) / len(rows) for _ in range(1000))
print("M5_dialect unit bootstrap 95%:", round(vals[25], 4), round(vals[974], 4))
med = statistics.median(freq[r["key"]] for r in rows)
for name, part in (("freq>median", [r for r in rows if freq[r["key"]] > med]), ("freq<=median", [r for r in rows if freq[r["key"]] <= med])):
    print(name, len(part), "M5_dialect", round(sum(r["covered_dialect"] for r in part) / len(part), 4),
          "no-candidate", round(sum(not r["candidates_romanized"] or r["candidates_romanized"] == [""] for r in part) / len(part), 4))
print("median person count per unit:", med)
