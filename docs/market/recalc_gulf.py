"""구조 변경(2026-10-20) 뒤 추정: 걸프 영어권 최종 사용자, 아랍어 → 영어, 사람 검수 없음.

사용자 결정(2026-10-20):
- 한국 고객·채널·한국어 출력을 빼고 영어-아랍어만 본다.
- 고객은 번역가를 부르던 비용을 아끼려는 최종 사용자다. 번역사무소는 고객이 아니다.
- 인터뷰와 사람 검수(제품 안의 검수, 아랍어 검수자를 쓰는 사전 감사)는 할 수 없어 추후 과제로 둔다.

같은 날 두 번째 결정(ADR-009): 1순위 고객은 걸프 법인 고객을 받는 KYC·컴플라이언스 팀이고 API로 판다.
걸프 진출 외국 중소기업 셀프서브는 체험·유입용 2순위다(8절).

그래서 수요 입력은 모두 공개 자료에 [가정]을 곱한 추산이다. 근거와 해석은
`사업성 검토 아랍어 문서 검증 도구.md`(2026-10-20 개정)에 있다. 경제성 모델은
recalc_economics.model을 그대로 쓰고, 사람 검수 원가만 0으로 둔다.

실행: 저장소 밖 디렉터리에서 `python3 -I <이 파일의 절대 경로>`
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from recalc_economics import AED, API, BASE_O, FIXED_M, RATE, SAR, USD, eok, model, scale  # noqa: E402

# ---------- 가격 기준 ----------
SA_FEE = 62.5 * SAR          # [확인] 사우디 공인 번역 375단어 한 장 중앙값(업체 5곳), S11·S12 외. 24,367원
UA_FEE = 150 * AED           # [대리·가정] 두바이 공개 가격 3건 범위 47~250디르함의 중간값(이전 판), S181~S183. 59,714원
SHARE = 0.20                 # [가정] 번역료의 20%(이전 판과 같은 규칙)
SEAT = 20 * USD              # [문헌○] Claude Pro·ChatGPT Business 월 $20, S149·S151
MT_UNLIMITED = 9.50 * USD    # [문헌○] MachineTranslation.com 월 무제한 $9.50, S145
ARBITR = 100 * USD           # [문헌○] arbitr Govern 월 $100(검증 계층 SaaS의 공개 가격), S135
PAGES = 20                   # [가정] 유료 고객당 월 장수(이전 판과 같음)

# ---------- 고객 모수 ----------
SA_FOREIGN_CR = 38_640       # [확인] 사우디 외국인 보유 활성 상업등기(2025-2Q), S50. 걸프 투자자 31,488건은 뺌
EG_YE_SHARE = (1029 + 439) / 3850  # [문헌○] 2024-3Q 투자 라이선스 중 이집트·예멘 몫(하한), S56
SA_ACTIVE_CR = 1_905_306     # [대리] 사우디 활성 상업등기 전체(2026-3Q), S51
UA_COMPANIES = 1_400_000     # [대리] UAE 활동 기업 140만 이상(경제부 장관 발언), S184
UA_HI_SHARE = 0.05           # [가정] 이전 판의 UAE 수요 기업 비율. 근거 없음
STATISTA_SA = 28.99e6 * USD  # [요약] 2024 사우디 번역 시장 2,899만 달러(학술지 재인용), S127

# ---------- 공급 ----------
KOSA_DEV = 6_943_457         # [확인] KOSA 2025 적용 응용SW개발자 월평균임금, S160
KOSA_SEC = 9_857_100         # [문헌○] KOSA 2025 적용 정보보안전문가, S160
STUDENT_FIXED = 2_000_000    # [가정] 대학생 팀 고정비(인건비 0, 기타 운영비만). 이전 판과 같음
EXP002_RUNS = 360            # [확인] EXP-002 평가 30문서 × 4조건 × 3회
LAWYER_SAR = (400, 900)      # [문헌○] 사우디 부티크 변호사 시급, S99
LEGAL_H = 30                 # [가정] PDPL SCC·이전 위험평가·약관 검토 시간
INSURANCE_USD = 410          # [요약] 번역가 E&O 최저 연 $410(2021), S174. SaaS 기술 E&O는 [미확인]
SOC2_USD = 28_000            # [문헌○] SOC 2 첫해(25명 이하 스타트업), S165
ISO_USD = 30_000             # [요약] ISO 27001 Stage 1+2 심사, S179
DB_PREMIUM_USD = 158 - 99    # [문헌○] Cloud SQL db-standard-2 담맘 − 아이오와 월 가격, S173

# ---------- API 고객: KYC·컴플라이언스 팀(ADR-009) ----------
API_PAGES = 200              # [가정] 고객당 월 서류 묶음 10건 × 20장(아랍어 상업등기·정관 + 여권 사본)
API_N5 = (10, 20, 40)        # [가정] 5년차 API 고객 수. 경로 모양은 BASE_O(0·10·30·60·100%)
SOC2_YEAR = 2                # [가정] 첫 API 판매 전인 2년차에 SOC 2를 받음. 갱신 비용은 [미확인]이라 넣지 않음
CAC_ENT = 10_000_000         # [가정] 엔터프라이즈 영업을 넣은 고객당 획득 비용(비교용). 근거 없음


def won(x):
    return f"{x:,.0f}원"


def eok1(x):
    return f"{x / 1e8:.2f}억"


def line(name, r):
    print(f"  {name}: 장당 공헌 {won(r['cpage'])}, 손익분기 {r['be_cust']:.0f}곳, "
          f"5년 누적 {eok(r['cum'])}억, NPV {eok(r['npv'])}억, 누적 최저 {eok(r['trough'])}억")


def first_profit_year(r):
    for y, _k, _o, _rev, cf, _cum in r["rows"]:
        if cf > 0:
            return y
    return None


def main():
    sa_price, ua_price = SA_FEE * SHARE, UA_FEE * SHARE
    sa_pool = SA_FOREIGN_CR * (1 - EG_YE_SHARE)
    ua_lo = UA_COMPANIES * sa_pool / SA_ACTIVE_CR
    ua_hi = UA_COMPANIES * UA_HI_SHARE
    w_sa = sa_pool / (sa_pool + ua_lo)
    gcc_price = w_sa * sa_price + (1 - w_sa) * ua_price

    print("== 0. 재현 확인")
    base = model(price=sa_price, review=0.1667 * 250 * SAR / 10, K=scale([10, 30, 50, 75, 100], 0.251))
    assert round(base["cum"] / 1e8, 2) == -8.28 and round(base["npv"] / 1e8, 2) == -3.07
    print(f"  이전 구조(사우디 기본) 5년 누적 {eok(base['cum'])}억, NPV {eok(base['npv'])}억 재현")

    print("\n== 1. 가격")
    print(f"  번역료: 사우디 {won(SA_FEE)}, UAE {won(UA_FEE)} (UAE/사우디 {UA_FEE / SA_FEE:.2f}배)")
    print(f"  장당 가격(번역료의 20%): 사우디 {won(sa_price)}, UAE {won(ua_price)}, 걸프 가중 {won(gcc_price)} "
          f"(사우디 비중 {w_sa:.1%})")
    for name, fee in [("LLM 좌석 $20", SEAT), ("MachineTranslation.com 무제한 $9.50", MT_UNLIMITED),
                      ("arbitr Govern $100", ARBITR)]:
        print(f"  월 {won(fee)}({name})을 월 {PAGES}장으로 나누면 장당 {won(fee / PAGES)}")
    print(f"  고객 월 지출(20장): 사우디 {won(sa_price * PAGES)}, UAE {won(ua_price * PAGES)} "
          f"= LLM 좌석의 {sa_price * PAGES / SEAT:.1f}배 / {ua_price * PAGES / SEAT:.1f}배")
    print(f"  고객 절감(번역 대비, 월 20장): 사우디 연 {won((SA_FEE - sa_price) * PAGES * 12)}, "
          f"UAE 연 {won((UA_FEE - ua_price) * PAGES * 12)}")

    print("\n== 2. 수요: 고객 모수")
    print(f"  사우디: 외국인 보유 등기 {SA_FOREIGN_CR:,} × (1 − 이집트·예멘 {EG_YE_SHARE:.1%}) = {sa_pool:,.0f}곳 (상한)")
    print(f"  사우디 모수 / 전체 활성 등기 = {sa_pool / SA_ACTIVE_CR:.2%}")
    print(f"  UAE 하단: 140만 × {sa_pool / SA_ACTIVE_CR:.2%}(사우디 비율) = {ua_lo:,.0f}곳 / 상단: 140만 × 5% = {ua_hi:,.0f}곳")
    print(f"  걸프 모수: {sa_pool + ua_lo:,.0f}곳(하단) ~ {sa_pool + ua_hi:,.0f}곳(상단)")

    print("\n== 3. 수요: 연 지출 규모(모수 × 평균 월 장수 × 가격)")
    for pages in (1, 2, 5):
        sa = sa_pool * pages * 12 * sa_price
        ua_l, ua_h = ua_lo * pages * 12 * ua_price, ua_hi * pages * 12 * ua_price
        human = sa_pool * pages * 12 * SA_FEE
        print(f"  평균 월 {pages}장: 사우디 {eok1(sa)}, UAE {eok1(ua_l)}~{eok1(ua_h)}, 합 {eok1(sa + ua_l)}~{eok1(sa + ua_h)} "
              f"| 사우디 모수를 사람 번역하면 {eok1(human)} = Statista 사우디 번역 시장의 {human / STATISTA_SA:.0%}")

    print("\n== 4. 경제성: 사람 검수 없음, 한국 고객 0, 해외 경로는 이전 판 모양(0·10·30·60·100)")
    Z = [0] * 5
    for title, fixed in [("급여 있는 2명(월 1,589만 원)", FIXED_M), ("대학생 팀(월 200만 원)", STUDENT_FIXED)]:
        print(f" -- {title}")
        for mname, price in [("사우디", sa_price), ("UAE", ua_price), ("걸프 가중", gcc_price)]:
            for n5 in (100, 200, 400):
                r = model(price=price, review=0, K=Z, O=scale(BASE_O, n5 / 100), fixed_m=fixed)
                fp = first_profit_year(r)
                line(f"{mname}, 5년차 {n5}곳, 첫 흑자 {fp or '없음'}{'년차' if fp else ''}", r)

    print("\n== 5. 가격을 대체재에 맞추면 (걸프 가중 모수, 급여 있음 / 대학생 팀 손익분기)")
    for name, monthly in [("LLM 좌석 2개 값 $40", 2 * SEAT), ("arbitr Govern $100", ARBITR),
                          ("번역료 20%(걸프 가중)", gcc_price * PAGES)]:
        cpage = monthly / PAGES - API
        be, be_s = FIXED_M / (cpage * PAGES), STUDENT_FIXED / (cpage * PAGES)
        print(f"  월 {won(monthly)}({name}): 장당 공헌 {won(cpage)}, 손익분기 {be:.0f}곳 / {be_s:.0f}곳 "
              f"= 걸프 하단 모수의 {be / (sa_pool + ua_lo):.2%} / {be_s / (sa_pool + ua_lo):.2%}")
    cpage = SEAT / PAGES - API
    print(f"  관문: EXP-002에서 지시만으로 충분하면 가격 천장 ≈ LLM 좌석 {won(SEAT)} → 장당 공헌 {won(cpage)}, "
          f"손익분기 {FIXED_M / (cpage * PAGES):.0f}곳 / {STUDENT_FIXED / (cpage * PAGES):.0f}곳")
    for title, fixed in [("급여", FIXED_M), ("대학생", STUDENT_FIXED)]:
        for n5 in (100, 400):
            r = model(price=SEAT / PAGES, review=0, K=[0] * 5, O=scale(BASE_O, n5 / 100), fixed_m=fixed)
            print(f"  LLM 좌석 가격, {title}, 5년차 {n5}곳: 5년 누적 {eok(r['cum'])}억, NPV {eok(r['npv'])}억")

    print("\n== 6. 고객 획득 비용 민감도 (걸프 가중 가격, 5년차 200곳)")
    for mult, label in [(3, "기본: 무료 진단 원가 × 3 = 93,000원"), (30, "×10: 마케팅비 포함 가정 930,000원"),
                        (90, "×30: 2,790,000원")]:
        for title, fixed in [("급여", FIXED_M), ("대학생", STUDENT_FIXED)]:
            r = model(price=gcc_price, review=0, K=Z, O=scale(BASE_O, 2), fixed_m=fixed, os_cac_mult=mult)
            print(f"  CAC {label}, {title}: 5년 누적 {eok(r['cum'])}억, NPV {eok(r['npv'])}억")

    print("\n== 7. 공급: 고객이 요구하는 수준까지 드는 시간과 돈")
    exp002 = EXP002_RUNS * API
    legal = [LEGAL_H * s * SAR for s in LAWYER_SAR]
    ins = INSURANCE_USD * USD
    eng6 = 6 * KOSA_DEV
    print(f"  A 판정(EXP-001·002, 2~4주): EXP-001 0원, EXP-002 {won(exp002)} 이하")
    print(f"  B 제품화(근거 검색·이름 사전·API·업로드 화면, 3~6개월): 엔지니어 1명 6개월 {won(eng6)}, 대학생 팀 0원")
    print(f"  C 셀프서브 출시(1~2개월, B와 병행): 사우디 PDPL 법률 검토 {won(legal[0])}~{won(legal[1])}, "
          f"보험 {won(ins)}, UAE 개인정보 검토 [미확인]")
    c_cash = (exp002 + legal[0] + ins, exp002 + legal[1] + ins)
    print(f"  A~C 현금(인건비 제외): {won(c_cash[0])}~{won(c_cash[1])}, 인건비 포함: {won(c_cash[0] + eng6)}~{won(c_cash[1] + eng6)}")
    soc2, iso = SOC2_USD * USD, ISO_USD * USD
    staff = (3 * KOSA_DEV + 0.5 * KOSA_SEC) * 12
    print(f"  D 엔터프라이즈(선택, 6~12개월): SOC 2 첫해 {won(soc2)}, ISO 27001 심사 {won(iso)}, "
          f"인력(엔지니어 3 + 보안 0.5, 12개월) {eok1(staff)}")
    print(f"  사우디 리전 DB 할증 월 {won(DB_PREMIUM_USD * USD)}")
    total_months = (2 / 4.345 + 3, 1 + 6)
    print(f"  셀프서브 첫 판매까지: 약 {total_months[0]:.1f}~{total_months[1]:.0f}개월 [가정, A + B]")

    print("\n== 8. API 고객: KYC·컴플라이언스 팀 (걸프 가중 가격, 고객당 월 200장, 2년차 SOC 2)")
    cpage = gcc_price - API
    per_cust = cpage * API_PAGES
    print(f"  고객당 월 공헌 {won(per_cust)}, 손익분기 {FIXED_M / per_cust:.1f}곳(급여) / {STUDENT_FIXED / per_cust:.1f}곳(대학생)")
    cac_base = 20 / 0.2 * API * 3
    for title, fixed in [("급여", FIXED_M), ("대학생", STUDENT_FIXED)]:
        for cac, cac_label in [(cac_base, "기본"), (CAC_ENT, "1,000만 원")]:
            for n5 in API_N5:
                r = model(price=gcc_price, review=0, docs=API_PAGES, K=[0] * 5, O=scale(BASE_O, n5 / 100),
                          fixed_m=fixed, os_cac_mult=cac / (20 / 0.2 * API))
                cum, npv, trough, first = 0, 0, 0, None
                for y, _k, _o, _rev, cf, _c in r["rows"]:
                    cf -= soc2 if y == SOC2_YEAR else 0
                    cum += cf
                    npv += cf / (1 + RATE) ** y
                    trough = min(trough, cum)
                    first = first or (y if cf > 0 else None)
                print(f"  {title}, CAC {cac_label}, 5년차 {n5}곳: 5년 누적 {eok(cum)}억, NPV {eok(npv)}억, "
                      f"누적 최저 {eok(trough)}억, 첫 흑자 {first or '없음'}{'년차' if first else ''}")


if __name__ == "__main__":
    main()
