"""아랍어 문서 검수 수요·공급 계산 (2026-10-20).

`docs/market/reports/아랍어 문서 검수 수요 공급 분석.md`의 수치를 모두 이 스크립트가 낸다.
기존 경제성 모델(recalc_economics.py)과 긍정 근거 시나리오(recalc_upside.py)의 상수와 함수를
그대로 불러 쓴다. 같은 입력이면 사업성 검토(사우디 기준)와 같은 값이 나오는지 0절에서 assert로 확인한다.

입력 주석의 라벨:
  [확인]   이 저장소에서 직접 조회·계산했거나, 기존 문서가 원문을 다시 대조한 값(sources.csv 확인=직접)
  [문헌○]  조사 노트가 원문을 열었다고 기록한 값(sources.csv 확인=대리)
  [요약]   검색 요약이나 2차 인용으로만 본 값(sources.csv 확인=요약)
  [단일]   동적 페이지에서 한 번 조회한 값
  [가정]   계산을 위해 둔 값. 근거가 아니다
  [미확인] 모르는 값. 계산에 넣지 않는다
출처 ID(Sxx)는 docs/market/sources.csv.

실행(저장소 밖 디렉터리에서, 표준 라이브러리만 사용):
  python3 -I /Users/muna/Documents/tashkeel-check/docs/market/recalc_demand_supply.py
"""
import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from recalc_economics import (AED, API, BASE_K, BASE_O, FIXED_M, SAR, USD,  # noqa: E402
                              eok, model, scale)
from recalc_upside import (FEE_SAR, ME_EXPORTERS, SA_K, SA_PRICE, SA_REVIEW,  # noqa: E402
                           VOUCHER_SHARE, model_split)

# =====================================================================
# 입력
# =====================================================================
# --- 기존 모델에서 그대로 가져온 값 (사업성 검토와 같음) ---
# USD = 1,462원 [확인, 사업성 검토 환율], SAR = USD/3.75 ≈ 390원 [확인, 고정환율], AED = USD/3.6725
# FIXED_M = 인건비 6,943,457원 × 2명 + 기타 200만 원 = 월 15,886,914원 [확인 KOSA 2025, S160 / 가정 2명·기타]
# API = 장당 310원 [가정] Sonnet 5.5 $2/$10(S161) × 장당 입력 3만·출력 1.5만 토큰
# SA_PRICE = 62.5리얄 × 20% = 4,873원 [가정 20% 규칙 / 확인 번역료 중앙값 S11·S12]
# SA_REVIEW = 0.1667리얄/단어 × 시간당 250단어 × 6분 = 1,625원 [가정]
# SA_K = 5년차 한국 고객 25.1곳(251곳 × 10%) [가정], BASE_O = 해외 고객 0→100곳 [가정]
# VOUCHER_SHARE = 0.30 [확인] 수출바우처 중소기업 자부담(국고 70%), S95
# ME_EXPORTERS = 14,000 [확인] 중동 수출기업 수(KOTRA 사장 발언), S93·S94

# --- 수요: 상향식 모수 ---
KR_ACTIVE = 70            # [확인] KOTRA 집계 사우디 활동 한국 기업 70여 개, S43
KR_NORMAL = 251           # [단일] 수출입은행 사우디 법인 중 상태 정상, S40
KR_CUM = 343              # [단일] 같은 출처 누적(1968~2026-06), S40
KR_CUM_2023 = 285         # [문헌○] KOTRA 2025 진출전략: 1968~2023 누적 신규 법인, S110
KR_NEW_AFTER = (14, 40, 7)  # [단일] 2024·2025·2026 상반기 신규 법인, S40
PEN_KR = 0.10             # [가정] 한국 쪽 침투율(사업성 검토와 같음)
PAGES_KR = 20             # [가정] 고객당 월 장수(사업성 검토와 같음)
ME_DEP, ME_DEP_ACTIVE = 1063, 966  # [확인] 중동 7개국 수출 비중 50% 이상 수출기업, S44
SHARE_SME = 0.01          # [가정] 중동 수출기업 중 아랍어 원문을 매달 받는 비율(긍정 근거 조사와 같음). 근거 없음
SHARE_DEP = 0.10          # [가정] 중동 의존 기업 1,063곳 중 같은 비율(비교용)
VOUCHER_SA_RECORDS = 23   # [단일] 2022년 이후 대상국 사우디 통번역 바우처 이용 기록, S32
VOUCHER_SPAN_Y = (date(2026, 10, 16) - date(2022, 1, 1)).days / 365.25  # [가정] 집계 기간을 2022-01-01~조회일로 봄
EMERG_VOUCHER = 689       # [문헌○] 중동 긴급바우처 1·2차 이용 기업, S96
VOUCHER_BUDGET = 1_502e8  # [요약] 2026 수출바우처 예산 1,502억 원, S126
FOREIGN_CR = 38_640       # [확인] 사우디 외국인 보유 활성 상업등기(2025-2Q), S50
FOREIGN_CO = 52_000       # [문헌○] 사우디 영업 외국 기업 5.2만 곳 이상(장관 발언 보도), S55·S114
RHQ = 700                 # [문헌○] 지역본부 설립 기업 700곳 이상(2026-01 장관 발언 보도), S54. 2025-09는 660곳(S114)
EG_YE_SHARE = (1029 + 439) / 3850  # [문헌○] 2024-3Q 투자 라이선스 중 이집트·예멘 몫(하한), S56
PAGES_LOCAL = 5           # [가정] 현지 외국계 기업 월 장수(사업성 검토와 같음)
PAGES_RHQ = 20            # [가정] 지역본부 기업 월 장수

# --- 수요: 하향식 교차 확인 ---
NIMDZI_ME = 1.1e9 * USD          # [확인] 2025 중동 언어 서비스 수요 11억 달러, S01
STATISTA_SA = 28.99e6 * USD      # [요약] 2024 사우디 번역 시장 2,899만 달러(학술지 재인용), S127
ASTUTE_GCC = 2_188.91e6 * USD    # [요약] 2023 GCC 번역 서비스 21.9억 달러, S128
KEN_SA_LT = (200e6 * USD, 380e6 * USD)  # [문헌○, 신뢰도 낮음] Ken Research 사우디 리걸테크 2024('illustrative', S180)·2025(S129)
TRANSL_CR = 7_964                # [확인] 사우디 번역업 활성 상업등기, S52
TRANSLATOR_PAGES_M = 110         # [가정] 번역가 1명 월 처리량(사업성 검토, 하루 2,000단어)
FTE_PER_CR = 1                   # [가정] 번역업 등기 1건당 전업 번역가 1명

# --- 고객 쪽 비교 가격 ---
FEE_PAGE = FEE_SAR * SAR         # 24,367원 [확인] 사우디 공인 번역 375단어 한 장 중앙값(S11·S12 외)
KR_FEE_PAGE = 230 * 375          # 86,250원 [확인] 국내 아랍어→한국어 단어당 중앙값 230원(S20·S21 외)
KR_PRICE = KR_FEE_PAGE * 0.20    # [가정] 한국어 출력이면 20% 규칙
V_PRICE = SA_PRICE / VOUCHER_SHARE  # [가정] 바우처 정가(자부담이 지금 가격과 같도록)
SEATS = [  # 범용 LLM 좌석 월 가격(USD)
    ("Claude Pro", 20, "[문헌○] S149"),
    ("Claude Team Standard 월 결제", 25, "[문헌○] S149"),
    ("ChatGPT Business 연 결제", 20, "[요약] S151"),
    ("M365 Copilot Business 정가(연 결제)", 21, "[문헌○] S150"),
    ("M365 Copilot Business 월 결제", 25.20, "[문헌○] S150"),
]
LADDER = [  # 장당 비교 가격(원)
    ("Google 문서 번역 $0.08/장", 0.08 * USD, "[확인] S06"),
    ("TAUS QE 약 €0.9/장 (1 EUR=1,600원)", 0.9 * 1600, "[문헌○] S09, 환율 [가정]"),
    ("MachineTranslation.com 건당 최저 $1.50", 1.50 * USD, "[문헌○] S145"),
]
ARBITR_GOVERN = 100              # [문헌○] arbitr Govern 월 $100, S135

# --- 공급: 장당 운영비 ---
SONNET = (2.0, 10.0)             # [문헌○] $/100만 토큰 입력·출력, S161. gpt-6.1-sol도 $2/$10, S162
HAIKU = (0.10, 0.50)             # [문헌○] Haiku 5.5, S161
TOK_IN, TOK_OUT = 30_000, 15_000  # [가정] 장당 토큰(사업성 검토와 같음, 미측정)
BATCH, US_ONLY = 0.5, 1.1        # [문헌○] Batch 50% 할인, US 전용 추론 1.1배, S161
REVIEW_MIN = 6                   # [가정] 장당 검수 6분(사업성 검토와 같음, 미측정)
REVIEWERS = [  # (이름, 시급 원, 라벨)
    ("기존 모델: 사우디 단어 단가 환산 41.7리얄", SA_REVIEW * 60 / REVIEW_MIN, "[가정] S11·S12 단어 단가 × 시간당 250단어"),
    ("이전 판: 두바이 100디르함", 100 * AED, "[가정] 사업성 검토 이전 판"),
    ("평가셋 작업자 $30", 30 * USD, "[가정] 공급 노트"),
    ("ProZ 아랍어-영어 프리랜서 $35", 35 * USD, "[요약] S164"),
    ("ProZ 아랍어-영어 프리랜서 $45", 45 * USD, "[요약] S164"),
    ("한국어-아랍어 230원 × 250단어", 230 * 250, "[가정] 긍정 근거 조사 3k"),
]

# --- 공급: 유료 파일럿 ---
KOSA_DEV = 6_943_457             # [확인] KOSA 2025 적용 응용SW개발자 월평균임금, S160
KOSA_SEC = 9_857_100             # [문헌○] KOSA 2025 적용 정보보안전문가, S160
PILOT_MONTHS, PILOT_ENG = 6, 1   # [가정] 엔지니어 1명 6개월(공급 노트)
EVAL_SPANS, EVAL_REVIEWERS, EVAL_MIN, EVAL_USD_H = 500, 2, 3, 30  # [가정] 평가셋 500구간 × 2명 × 3분, 시급 $30
DIAG_CUSTOMERS = 5               # [가정] 무료 진단 3~5곳의 상단(사업성 검토 다음 순서)
DIAG_PAGES = 20                  # [가정] 무료 진단 장수(recalc_economics와 같음)
INSURANCE_USD = 410              # [요약] 번역가 E&O 최저 연 $410(2021), S174. SaaS 기술 E&O 보험료는 [미확인]
# 개인정보 처리방침·국외 이전 법무 비용은 [미확인]이라 넣지 않는다

# --- 공급: 엔터프라이즈 준비 (사우디 외국계 고객) ---
SOC2_USD = 28_000                # [문헌○] SOC 2 첫해 총액(25명 스타트업), S165
ISO_USD = 30_000                 # [요약] ISO 27001 Stage 1+2 심사(Konfirmity), S179
ISMSP = (6e6, 11e6)              # [문헌○] ISMS-P 간편인증 수수료, S167
LEGAL_H = 30                     # [가정] PDPL SCC·이전 위험평가·약관 검토 시간
LAWYER_SAR = (400, 900)          # [문헌○] 사우디 부티크 변호사 시급, S99
ENT_ENG, ENT_SEC, ENT_MONTHS = 3, 0.5, 12  # [가정] 엔지니어 3명 + 보안 0.5명, 12개월(공급 노트)
DB_DAMMAM, DB_IOWA = 158, 99     # [문헌○] GCP Cloud SQL db-standard-2 월 $, S173
ENT_LEAD = (6, 12)               # [문헌○] SOC 2 Type 2 6~12개월, ISO 27001 약 6개월, S165·S166
# 사우디 안 LLM 추론(자체 GPU, 사우디 리전 관리형 LLM) 비용은 [미확인]

# --- 결정적 검증 비용 ---
EXP002_RUNS = 30 * 4 * 3         # [확인] PROJECT_PLAN 6.2: 평가 문서 30개 × 조건 4 × 3회 = 360회
PAGES_PER_SYN_DOC = 1            # [가정] 합성 문서 1개 = 1장. 실제 아랍어 단어는 문서당 73~132개 [확인]


# =====================================================================
# 계산 도우미
# =====================================================================
def won(x):
    return f"{x:,.0f}원"


def eokf(x, d=2):
    return f"{x / 1e8:,.{d}f}억"


def annual(n, pages, price):
    return n * pages * 12 * price


def be_customers(price, review, fixed_m=FIXED_M, docs=PAGES_KR):
    c = price - API - review
    return float("inf") if c <= 0 else fixed_m / c / docs


def api_cost(rates, mult=1.0):
    return (TOK_IN / 1e6 * rates[0] + TOK_OUT / 1e6 * rates[1]) * USD * mult


def runway(rows, fixed_m):
    cums = [r[5] for r in rows]
    trough = min(0, min(cums))
    pos = [r[0] for r in rows if r[4] > 0]
    return trough, (pos[0] if pos else None), -trough / fixed_m


def main():
    # ----------------------------------------------------------------
    print("== 0. 재현 확인 (기존 모델과 같은 값이어야 함)")
    base = model(price=SA_PRICE, review=SA_REVIEW, K=SA_K)
    assert abs(base["cum"] / 1e8 + 8.28) < 0.01 and abs(base["npv"] / 1e8 + 3.07) < 0.01
    assert abs(base["be_cust"] - 270.3) < 0.1
    K_pool = scale(BASE_K, ME_EXPORTERS * SHARE_SME / 100)
    s3 = model_split(V_PRICE, SA_PRICE, K=K_pool)
    assert abs(s3["cum"] / 1e8 - 3.77) < 0.01
    print(f"사우디 기본: 장당 가격 {won(SA_PRICE)}, 장당 공헌 {won(base['cpage'])}, 손익분기 {base['be_cust']:.0f}곳, "
          f"5년 누적 {eok(base['cum'])}억, NPV {eok(base['npv'])}억 (일치)")
    print(f"바우처 + 중동 수출기업 1%: 5년 누적 {eok(s3['cum'])}억, NPV {eok(s3['npv'])}억 (일치)")
    print(f"API 장당 310원 검산: Sonnet 5.5 $2/$10 × 3만/1.5만 토큰 = {won(api_cost(SONNET))}")

    # ----------------------------------------------------------------
    print("\n== 1. 수요: 상향식 (고객 수 × 월 장수 × 장당 가격, 연간)")
    cust_year = PAGES_KR * 12 * SA_PRICE
    print(f"고객 1곳(월 {PAGES_KR}장, 사우디 기준 가격): 연 {won(cust_year)}, 사람 번역이면 연 {won(PAGES_KR * 12 * FEE_PAGE)}, "
          f"절감 {won(PAGES_KR * 12 * (FEE_PAGE - SA_PRICE))}")
    print(f"검산: KOTRA 누적 {KR_CUM_2023} + 이후 신규 {sum(KR_NEW_AFTER)} = {KR_CUM_2023 + sum(KR_NEW_AFTER)} vs 수출입은행 누적 {KR_CUM}")
    rows = [
        ("A1 사우디 법인 한국 기업, KOTRA 활동 기업", KR_ACTIVE, PAGES_KR, SA_PRICE, PEN_KR),
        ("A1 사우디 법인 한국 기업, 수출입은행 정상 법인", KR_NORMAL, PAGES_KR, SA_PRICE, PEN_KR),
        ("A1' 같은 251곳, 한국어 출력 가격", KR_NORMAL, PAGES_KR, KR_PRICE, PEN_KR),
        ("A2 중동 수출기업 1만4천 곳의 1%, 바우처 정가", ME_EXPORTERS * SHARE_SME, PAGES_KR, V_PRICE, 1.0),
        ("A2' 중동 의존 수출기업 1,063곳의 10%, 바우처 정가", ME_DEP * SHARE_DEP, PAGES_KR, V_PRICE, 1.0),
        ("A3 사우디 외국인 보유 상업등기 전체", FOREIGN_CR, PAGES_LOCAL, SA_PRICE, None),
        ("A3' 위에서 이집트·예멘 몫을 뺀 상한", FOREIGN_CR * (1 - EG_YE_SHARE), PAGES_LOCAL, SA_PRICE, None),
        ("A3'' 사우디 영업 외국 기업 5.2만 곳에서 이집트·예멘 몫 제외", FOREIGN_CO * (1 - EG_YE_SHARE), PAGES_LOCAL, SA_PRICE, None),
        ("A3''' 지역본부(RHQ) 기업", RHQ, PAGES_RHQ, SA_PRICE, None),
    ]
    for name, n, pages, price, pen in rows:
        full = annual(n, pages, price)
        extra = ""
        if pen is not None:
            extra = f" | 닿는 몫 {n * pen:,.1f}곳 → 연 {eokf(full * pen)}"
        print(f"  {name}: 모수 {n:,.0f}곳 × 월 {pages}장 × {won(price)} = 연 {eokf(full)}{extra}")
    print(f"  이집트·예멘 몫(하한) {EG_YE_SHARE:.1%}")
    som = annual(SA_K[-1] + BASE_O[-1], PAGES_KR, SA_PRICE)
    print(f"  기존 SOM(5년차 한국 {SA_K[-1]:.1f} + 해외 {BASE_O[-1]}곳): 연 {eokf(som)}")

    # ----------------------------------------------------------------
    print("\n== 2. 수요: 하향식 교차 확인")
    tam_local = annual(FOREIGN_CR, PAGES_LOCAL, SA_PRICE)
    tam_kr = annual(KR_NORMAL, PAGES_KR, SA_PRICE)
    tam = tam_local + tam_kr
    print(f"기존 TAM 상한 {eokf(tam, 1)} = Nimdzi 중동 언어 서비스 수요 {eokf(NIMDZI_ME, 0)}의 {tam / NIMDZI_ME:.2%}")
    implied_human = annual(FOREIGN_CR, PAGES_LOCAL, FEE_PAGE)
    print(f"A3 문서량(월 {FOREIGN_CR * PAGES_LOCAL:,}장)을 사람이 번역하면 연 {eokf(implied_human, 0)} "
          f"= Statista 사우디 번역 시장(2024) {eokf(STATISTA_SA, 0)}의 {implied_human / STATISTA_SA:.2f}배")
    capacity = TRANSL_CR * FTE_PER_CR * TRANSLATOR_PAGES_M * 12 * FEE_PAGE
    print(f"번역업 등기 {TRANSL_CR:,}건 × 1명 × 월 {TRANSLATOR_PAGES_M}장 × 번역료 = 연 {eokf(capacity, 0)} "
          f"(Nimdzi 중동의 {capacity / NIMDZI_ME:.0%}, Statista 사우디의 {capacity / STATISTA_SA:.1f}배)")
    print(f"Statista 사우디 번역 시장 ÷ 번역업 등기 = 등기 1건당 연 {won(STATISTA_SA / TRANSL_CR)}")
    print(f"Astute GCC 번역(2023) {eokf(ASTUTE_GCC, 0)} = Statista 사우디의 {ASTUTE_GCC / STATISTA_SA:.0f}배, Nimdzi 중동의 {ASTUTE_GCC / NIMDZI_ME:.2f}배")
    print(f"TAM 상한 ÷ Ken Research 사우디 리걸테크: {tam / KEN_SA_LT[1]:.1%}(2025, $380M) ~ {tam / KEN_SA_LT[0]:.1%}(2024, $200M)")
    a2 = annual(ME_EXPORTERS * SHARE_SME, PAGES_KR, V_PRICE)
    print(f"A2 시나리오 국고 몫 {eokf(a2 * (1 - VOUCHER_SHARE))} = 2026 수출바우처 예산의 {a2 * (1 - VOUCHER_SHARE) / VOUCHER_BUDGET:.2%}")
    v_rate = VOUCHER_SA_RECORDS / VOUCHER_SPAN_Y
    print(f"관찰된 사우디 대상 통번역 바우처 이용: {VOUCHER_SA_RECORDS}건 / {VOUCHER_SPAN_Y:.1f}년 = 연 {v_rate:.1f}건 "
          f"→ A2가 가정한 상시 고객 {ME_EXPORTERS * SHARE_SME:.0f}곳은 그 {ME_EXPORTERS * SHARE_SME / v_rate:.0f}배")
    print(f"바우처 손익분기 56곳 = 중동 수출기업의 {56 / ME_EXPORTERS:.2%}, 중동 의존 1,063곳의 {56 / ME_DEP:.1%}, "
          f"긴급바우처 이용 {EMERG_VOUCHER}곳의 {56 / EMERG_VOUCHER:.1%}")

    # ----------------------------------------------------------------
    print("\n== 3. 고객이 견주는 가격")
    for name, usd, lab in SEATS:
        krw = usd * USD
        print(f"  {name} 월 ${usd:g} = {won(krw)} → 사우디 기준 {krw / SA_PRICE:.1f}장, 바우처 정가 {krw / V_PRICE:.1f}장, "
              f"한국어 출력 {krw / KR_PRICE:.1f}장 값 {lab}")
    print(f"  월 {PAGES_KR}장 고객의 도구 비용 {won(PAGES_KR * SA_PRICE)} = Claude Pro 좌석의 {PAGES_KR * SA_PRICE / (20 * USD):.1f}배")
    arb = ARBITR_GOVERN * USD
    print(f"  arbitr Govern 월 ${ARBITR_GOVERN} = {won(arb)} → 사우디 기준 {arb / SA_PRICE:.0f}장 값")
    for name, krw, lab in LADDER:
        print(f"  {name} = {won(krw)} → 사우디 기준 가격은 그 {SA_PRICE / krw:.1f}배 {lab}")
    print(f"  사람 번역: 사우디 {won(FEE_PAGE)}(도구는 {SA_PRICE / FEE_PAGE:.0%}), 국내 {won(KR_FEE_PAGE)}(바우처 정가는 {V_PRICE / KR_FEE_PAGE:.0%})")

    # ----------------------------------------------------------------
    print("\n== 4. 공급: 장당 운영비")
    variants = [("Sonnet 5.5 표준", api_cost(SONNET)), ("Sonnet 5.5 Batch", api_cost(SONNET, BATCH)),
                ("Sonnet 5.5 US 전용", api_cost(SONNET, US_ONLY)), ("Haiku 5.5 표준", api_cost(HAIKU))]
    for name, c in variants:
        print(f"  API {name}: 장당 {won(c)}")
    print(f"  모델이 쓰는 API 상수 {won(API)}")
    print(f"  {'검수자 시급':<34} 시급        장당 검수   장당 변동비  공헌(4,873) 손익분기  공헌(16,244) 손익분기  공헌(17,250) 손익분기")
    for name, hourly, lab in REVIEWERS:
        rv = hourly * REVIEW_MIN / 60
        var = API + rv
        cells = []
        for p in (SA_PRICE, V_PRICE, KR_PRICE):
            b = be_customers(p, rv)
            cells.append(f"{p - var:>9,.0f} {('없음' if b == float('inf') else f'{b:,.0f}곳'):>8}")
        print(f"  {name:<34} {hourly:>9,.0f} {rv:>9,.0f} {var:>10,.0f} " + "  ".join(cells) + f"  {lab}")
    print(f"  기존 모델에서 검수 원가가 장당 변동비에서 차지하는 몫: {SA_REVIEW / (API + SA_REVIEW):.0%}, API 몫 {API / (API + SA_REVIEW):.0%}")
    h0 = REVIEWERS[0][1]
    print(f"  ProZ 시급($35~45)은 기존 모델 시급의 {35 * USD / h0:.1f}~{45 * USD / h0:.1f}배")
    rv_zero = (SA_PRICE - API) / (REVIEW_MIN / 60)
    print(f"  사우디 기준 가격에서 장당 공헌이 0이 되는 검수자 시급: {won(rv_zero)} = ${rv_zero / USD:.1f}")
    print(f"  CAC(고객 획득 비용): 한국 {won(base['cac_kr'])}, 해외 {won(base['cac_os'])} (기존 모델)")

    # ----------------------------------------------------------------
    print("\n== 5. 공급: 유료 파일럿까지 (한국 중소기업, 인증 없음)")
    p_eng = PILOT_ENG * PILOT_MONTHS * KOSA_DEV
    eval_h = EVAL_SPANS * EVAL_REVIEWERS * EVAL_MIN / 60
    p_eval = eval_h * EVAL_USD_H * USD
    p_diag = DIAG_CUSTOMERS * DIAG_PAGES * (API + SA_REVIEW)
    p_ins = INSURANCE_USD * USD
    cash = p_eval + p_diag + p_ins
    print(f"  엔지니어 {PILOT_ENG}명 × {PILOT_MONTHS}개월 × {won(KOSA_DEV)} = {won(p_eng)}")
    print(f"  평가셋 {EVAL_SPANS}구간 × {EVAL_REVIEWERS}명 × {EVAL_MIN}분 = {eval_h:.0f}시간 × ${EVAL_USD_H} = {won(p_eval)}")
    print(f"  무료 진단 {DIAG_CUSTOMERS}곳 × {DIAG_PAGES}장 × (API + 검수) = {won(p_diag)}")
    print(f"  보험(번역가 E&O 최저) ${INSURANCE_USD} = {won(p_ins)}")
    print(f"  현금 지출(인건비 제외, 법무 미포함) {won(cash)}, 인건비 포함 {won(cash + p_eng)}")
    print(f"  같은 6개월을 기존 모델 고정비(2명 + 기타)로 버티면 {won(PILOT_MONTHS * FIXED_M)}")

    # ----------------------------------------------------------------
    print("\n== 6. 공급: 엔터프라이즈 준비 (사우디 외국계, 첫해)")
    soc2 = SOC2_USD * USD
    iso = ISO_USD * USD
    legal = tuple(LEGAL_H * s * SAR for s in LAWYER_SAR)
    eng = ENT_ENG * ENT_MONTHS * KOSA_DEV
    sec = ENT_SEC * ENT_MONTHS * KOSA_SEC
    db = (DB_DAMMAM - DB_IOWA) * USD
    cert_lo, cert_hi = soc2 + legal[0], soc2 + legal[1]
    full_lo, full_hi = soc2 + iso + ISMSP[0] + legal[0], soc2 + iso + ISMSP[1] + legal[1]
    ppl = eng + sec
    print(f"  SOC 2 첫해 {won(soc2)}, ISO 27001 심사 {won(iso)}, ISMS-P 간편 {won(ISMSP[0])}~{won(ISMSP[1])}")
    print(f"  PDPL·약관 법률 검토 {LEGAL_H}시간 × {LAWYER_SAR[0]}~{LAWYER_SAR[1]}리얄 = {won(legal[0])}~{won(legal[1])}")
    print(f"  인증·법무: SOC 2 하나 {eokf(cert_lo)}~{eokf(cert_hi)}, 셋 다 {eokf(full_lo)}~{eokf(full_hi)}")
    print(f"  인력: 엔지니어 {ENT_ENG}명 {eokf(eng)} + 보안 {ENT_SEC}명 {eokf(sec)} = {eokf(ppl)}")
    print(f"  합계(인력 + SOC 2 하나와 법무) {eokf(ppl + cert_lo)}~{eokf(ppl + cert_hi)}, 인증 셋 다면 {eokf(ppl + full_hi)}")
    print(f"  사우디 리전 DB 할증 월 {won(db)}, 손익분기 물량(월 {base['be_pages']:,.0f}장) 기준 장당 {db / base['be_pages']:.0f}원")
    print(f"  기간: 결정 후 {ENT_LEAD[0]}~{ENT_LEAD[1]}개월. 파일럿 {PILOT_MONTHS}개월 뒤 시작하면 첫 엔터프라이즈 판매는 {PILOT_MONTHS + ENT_LEAD[0]}~{PILOT_MONTHS + ENT_LEAD[1]}개월째")
    c_year20 = base["contrib_cust"]
    c_year5 = PAGES_LOCAL * 12 * base["cpage"]
    print(f"  해외 고객 1곳 연 공헌: 월 20장 {won(c_year20)}, 월 5장 {won(c_year5)}")
    for label, cost in (("인증·법무", cert_lo), ("인증·법무 상단", cert_hi), ("인력 포함", ppl + cert_lo), ("인력 포함 상단", ppl + cert_hi)):
        print(f"  {label} {eokf(cost)}를 1년 공헌으로 회수하려면 해외 고객 {cost / c_year20:,.0f}곳(월 20장) / {cost / c_year5:,.0f}곳(월 5장)")

    # ----------------------------------------------------------------
    print("\n== 7. 격차: 손익분기 대 닿을 수 있는 고객, 필요 자금")
    print(f"  손익분기(사우디 기준, 급여 있음) {base['be_cust']:.0f}곳 vs 한국 쪽 닿는 몫 {KR_ACTIVE * PEN_KR:.0f}~{KR_NORMAL * PEN_KR:.0f}곳 "
          f"→ {base['be_cust'] / (KR_NORMAL * PEN_KR):.0f}~{base['be_cust'] / (KR_ACTIVE * PEN_KR):.0f}배. 후보 전부(70~251곳)와 견줘도 {base['be_cust'] / KR_NORMAL:.1f}~{base['be_cust'] / KR_ACTIVE:.1f}배")
    be_v = be_customers(V_PRICE, SA_REVIEW)
    be_kr = model(price=KR_PRICE, review=230 * 250 / 10, K=SA_K, O=[0] * 5)["be_cust"]
    be_stu = model(price=SA_PRICE, review=SA_REVIEW, K=SA_K, fixed_m=2_000_000)["be_cust"]
    print(f"  손익분기: 바우처 정가 {be_v:.0f}곳, 한국어 출력 {be_kr:.0f}곳, 대학생 팀 {be_stu:.0f}곳")
    for name, be in (("한국어 출력", be_kr), ("대학생 팀", be_stu)):
        print(f"  {name} 손익분기 {be:.0f}곳 vs 닿는 몫 7~25곳 → {be / (KR_NORMAL * PEN_KR):.1f}~{be / (KR_ACTIVE * PEN_KR):.1f}배, "
              f"후보 전부 70~251곳 → {be / KR_NORMAL:.2f}~{be / KR_ACTIVE:.2f}배")
    print(f"  바우처 손익분기 {be_v:.0f}곳 vs 관찰된 사우디 대상 통번역 바우처 이용 연 {v_rate:.1f}건 → {be_v / v_rate:.0f}배")
    rv35 = 35 * USD * REVIEW_MIN / 60
    scen = [
        ("사우디 기본", model(price=SA_PRICE, review=SA_REVIEW, K=SA_K)["rows"], FIXED_M),
        ("사우디 기본, 해외 0곳", model(price=SA_PRICE, review=SA_REVIEW, K=SA_K, O=[0] * 5)["rows"], FIXED_M),
        ("대학생 팀", model(price=SA_PRICE, review=SA_REVIEW, K=SA_K, fixed_m=2_000_000)["rows"], 2_000_000),
        ("바우처 + 중동 수출기업 1%", s3["rows"], FIXED_M),
        ("바우처 + 1%, 해외 0곳", model_split(V_PRICE, SA_PRICE, K=K_pool, O=[0] * 5)["rows"], FIXED_M),
        ("대학생 팀 + 바우처", model_split(V_PRICE, SA_PRICE, fixed_m=2_000_000)["rows"], 2_000_000),
        ("사우디 기본, 검수자 ProZ $35", model(price=SA_PRICE, review=rv35, K=SA_K)["rows"], FIXED_M),
        ("바우처 + 1%, 검수자 ProZ $35", model_split(V_PRICE, SA_PRICE, review=rv35, K=K_pool)["rows"], FIXED_M),
    ]
    for name, rws, fm in scen:
        trough, first_pos, months = runway(rws, fm)
        print(f"  {name}: 5년 누적 {eok(rws[-1][5])}억, 필요 자금(최저 누적) {eokf(-trough)} = 월 고정비 {months:.0f}개월분, "
              f"첫 흑자 연차 {first_pos if first_pos else '없음'}")

    # ----------------------------------------------------------------
    print("\n== 8. 결정적 검증의 비용 (옵션 가치)")
    exp002 = EXP002_RUNS * PAGES_PER_SYN_DOC * API
    decisive = exp002 + p_eval
    trough_base = -runway(base["rows"], FIXED_M)[0]
    print(f"  EXP-001: 형태소 분석기만 씀, API 0원")
    print(f"  EXP-002: {EXP002_RUNS}회 × {PAGES_PER_SYN_DOC}장 × {won(API)} = {won(exp002)} 이하")
    print(f"  사전 감사 검수자(평가셋과 같은 규모) {won(p_eval)}")
    print(f"  합계 {won(decisive)} = 기본 시나리오 필요 자금 {eokf(trough_base)}의 {decisive / trough_base:.2%}, 월 고정비의 {decisive / FIXED_M:.0%}")


if __name__ == "__main__":
    main()
