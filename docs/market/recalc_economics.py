"""사업성 검토 경제성 모델 재현(UAE 원본) + 사우디 재계산."""

USD = 1462
AED = USD / 3.6725
SAR = USD / 3.75
FIXED_M = 6_943_457 * 2 + 2_000_000  # 인건비 2명 + 기타
API = 310
DIAG_PAGES = 20      # 무료 진단 장수
CONV = 0.20          # 유료 전환율
OS_CAC_MULT = 3
RATE = 0.50
BASE_K = [10, 30, 50, 75, 100]
BASE_O = [0, 10, 30, 60, 100]


def model(price, review, docs=20, K=BASE_K, O=BASE_O, fixed_m=FIXED_M,
          os_cac_mult=OS_CAC_MULT, api=API):
    cpage = price - api - review
    cac_kr = DIAG_PAGES / CONV * (api + review)
    cac_os = cac_kr * os_cac_mult
    fixed = fixed_m * 12
    rows, cum, prevK, prevO, npv = [], 0, 0, 0, 0
    trough = 0
    for y, (k, o) in enumerate(zip(K, O), 1):
        n = k + o
        rev = n * docs * 12 * price
        contrib = n * docs * 12 * cpage
        cac = (k - prevK) * cac_kr + (o - prevO) * cac_os
        cf = contrib - fixed - cac
        cum += cf
        trough = min(trough, cum)
        npv += cf / (1 + RATE) ** y
        rows.append((y, k, o, rev, cf, cum))
        prevK, prevO = k, o
    be_pages = fixed_m / cpage
    return dict(cpage=cpage, margin=cpage / price, cac_kr=cac_kr, cac_os=cac_os,
                rev_cust=docs * 12 * price, contrib_cust=docs * 12 * cpage,
                payback_kr=cac_kr / (docs * cpage), payback_os=cac_os / (docs * cpage),
                be_pages=be_pages, be_cust=be_pages / docs, rows=rows, cum=cum,
                npv=npv, trough=trough)


def eok(x):
    return f"{x / 1e8:+.2f}"


def show(title, r):
    print(f"\n== {title}")
    print(f"장당 공헌이익 {r['cpage']:,.0f}원 ({r['margin']:.1%}), CAC 한국 {r['cac_kr']:,.0f} 해외 {r['cac_os']:,.0f}")
    print(f"고객당 연매출 {r['rev_cust']:,.0f}, 연공헌 {r['contrib_cust']:,.0f}, 회수 한국 {r['payback_kr']:.1f}개월 해외 {r['payback_os']:.1f}개월")
    print(f"손익분기 월 {r['be_pages']:,.0f}장, 고객 {r['be_cust']:.1f}곳, 번역가 {r['be_pages'] / 110:.1f}명분")
    for y, k, o, rev, cf, cum in r["rows"]:
        print(f"  {y}년 한국 {k:g} 해외 {o:g} 매출 {rev / 1e8:.2f}억 CF {eok(cf)} 누적 {eok(cum)}")
    print(f"  NPV {eok(r['npv'])}억, 최저 누적 {eok(r['trough'])}억")


def scale(lst, f):
    return [x * f for x in lst]


def os_needed(base_kwargs):
    """해외 고객 경로를 몇 배 늘려야 5년 누적 0인지(선형)."""
    r0 = model(**base_kwargs)
    kw = dict(base_kwargs)
    kw["O"] = scale(base_kwargs.get("O", BASE_O), 2)
    r1 = model(**kw)
    per_k = r1["cum"] - r0["cum"]
    k = 1 - r0["cum"] / per_k
    return k, k * base_kwargs.get("O", BASE_O)[-1]


def price_needed(base_kwargs):
    lo, hi = 0, 200_000
    for _ in range(100):
        mid = (lo + hi) / 2
        kw = dict(base_kwargs, price=mid)
        if model(**kw)["cum"] < 0:
            lo = mid
        else:
            hi = mid
    return hi


def sensitivity(base_kwargs, title):
    print(f"\n-- 민감도 ({title}): 5년 누적 변화, 손익분기 고객")
    b = model(**base_kwargs)
    p = base_kwargs["price"]; rv = base_kwargs["review"]; d = base_kwargs.get("docs", 20)
    K = base_kwargs.get("K", BASE_K); O = base_kwargs.get("O", BASE_O)
    cases = {
        "장당 가격": (dict(price=p * 0.8), dict(price=p * 1.2)),
        "고객당 문서량": (dict(docs=d * 0.8), dict(docs=d * 1.2)),
        "유료 고객 수": (dict(K=scale(K, .8), O=scale(O, .8)), dict(K=scale(K, 1.2), O=scale(O, 1.2))),
        "장당 검수 시간": (dict(review=rv * 1.2), dict(review=rv * 0.8)),
        "해외 CAC": (dict(os_cac_mult=OS_CAC_MULT * 1.2), dict(os_cac_mult=OS_CAC_MULT * 0.8)),
    }
    for name, (bad, good) in cases.items():
        rb = model(**{**base_kwargs, **bad}); rg = model(**{**base_kwargs, **good})
        print(f"  {name}: 나쁠 때 {eok(rb['cum'] - b['cum'])}억 / 좋을 때 {eok(rg['cum'] - b['cum'])}억 | 손익분기 {rb['be_cust']:.0f} / {rg['be_cust']:.0f}")


def main():
    # ---------- 1) UAE 원본 재현 ----------
    uae_price = 30 * AED
    uae_review = 100 * AED / 10          # 시급 100디르함 × 6분
    uae = dict(price=uae_price, review=uae_review)
    show("UAE 원본 재현 (기대: 공헌 약 7,700원, 손익분기 104곳, 누적 -2.70, NPV -1.9)", model(**uae))
    print("해외 몇 곳이면 누적 0:", os_needed(uae))
    sensitivity(uae, "UAE 원본")
    for name, f_price, docs, kf, of in [("비관", 15, 10, .5, 0), ("낙관", 45, 40, 2, 4)]:
        r = model(price=f_price * AED, review=uae_review, docs=docs, K=scale(BASE_K, kf), O=scale(BASE_O, of))
        print(f"UAE {name}: 5년차 매출 {r['rows'][-1][3] / 1e8:.1f}억, 손익분기 {r['be_cust']:.0f}, 누적 {eok(r['cum'])}, NPV {eok(r['npv'])}")
    stu = model(price=uae_price, review=uae_review, fixed_m=2_000_000)
    stu_kr = model(price=uae_price, review=uae_review, fixed_m=2_000_000, O=[0] * 5)
    print(f"UAE 대학생팀: 손익분기 {stu['be_cust']:.1f}, 누적 {eok(stu['cum'])}, 한국만 {eok(stu_kr['cum'])}")
    print("UAE 해외 0곳:", eok(model(**uae, O=[0] * 5)["cum"]), eok(model(**uae, O=[0] * 5)["npv"]))

    # ---------- 2) 사우디 ----------
    fee_sar = 62.5                     # 375단어 한 장 중앙값(업체 5곳)
    sa_price = fee_sar * 0.20 * SAR
    sa_review_hourly = 0.1667 * 250 * SAR   # 단어당 0.167리얄 × 시간당 250단어
    sa_review = sa_review_hourly / 10
    KR_POOL = 251
    sa_K = scale(BASE_K, KR_POOL * 0.10 / 100)   # 침투율 10% 유지 → 5년차 25곳
    sa = dict(price=sa_price, review=sa_review, K=sa_K)
    print(f"\n사우디 입력: 번역료 {fee_sar * SAR:,.0f}원, 장당 가격 {sa_price:,.0f}원, 검수 시급 {sa_review_hourly:,.0f}원, 장당 검수 {sa_review:,.0f}원")
    show("사우디 기본", model(**sa))
    print("해외 몇 곳이면 누적 0:", os_needed(sa))
    pn = price_needed(sa)
    print(f"누적 0이 되는 장당 가격: {pn:,.0f}원 = {pn / SAR:.1f}리얄 = 번역료의 {pn / (fee_sar * SAR):.0%}, 현재 대비 {pn / sa_price - 1:+.0%}")
    r_kr_only = model(**sa, O=[0] * 5)
    print(f"해외 0곳: 누적 {eok(r_kr_only['cum'])}, NPV {eok(r_kr_only['npv'])}")
    r_kr_all = model(price=sa_price, review=sa_review, K=scale(BASE_K, KR_POOL / 100), O=[0] * 5)
    print(f"한국 251곳 전부(해외 0): 누적 {eok(r_kr_all['cum'])}, 5년차 매출 {r_kr_all['rows'][-1][3] / 1e8:.2f}억")
    sensitivity(sa, "사우디 기본")
    for name, pct, docs, kf, of in [("비관", .10, 10, .5, 0), ("기본", .20, 20, 1, 1), ("낙관", .30, 40, 2, 4)]:
        r = model(price=fee_sar * pct * SAR, review=sa_review, docs=docs, K=scale(sa_K, kf), O=scale(BASE_O, of))
        print(f"사우디 {name}: 가격 {fee_sar * pct:.2f}리얄={fee_sar * pct * SAR:,.0f}원, 5년차 고객 {sa_K[-1] * kf:g}+{BASE_O[-1] * of:g}, 5년차 매출 {r['rows'][-1][3] / 1e8:.2f}억, 손익분기 {r['be_cust']:.0f}, 누적 {eok(r['cum'])}, NPV {eok(r['npv'])}")
    stu = model(**sa, fixed_m=2_000_000)
    stu_kr = model(**sa, fixed_m=2_000_000, O=[0] * 5)
    show("사우디 대학생팀", stu)
    print(f"사우디 대학생팀 한국만: 누적 {eok(stu_kr['cum'])}")

    # ---------- 3) 시장 규모 ----------
    foreign_cr = 38_640
    tam_local = foreign_cr * 5 * 12 * sa_price
    tam_kr = KR_POOL * 20 * 12 * sa_price
    som = (sa_K[-1] + BASE_O[-1]) * 20 * 12 * sa_price
    print(f"\nTAM 현지 상한 {tam_local / 1e8:.1f}억, 한국 {tam_kr / 1e8:.2f}억, 합 {(tam_local + tam_kr) / 1e8:.1f}억, SOM {som / 1e8:.2f}억")
    print(f"중동 11억달러 대비 {(tam_local + tam_kr) / (1.1e9 * USD):.2%}")
    print(f"절감: 번역 {fee_sar * SAR:,.0f} vs 도구 {sa_price:,.0f} → {1 - sa_price / (fee_sar * SAR):.0%}, 월20장 연 {(fee_sar * SAR - sa_price) * 240:,.0f}원")

    # ---------- 4) 참고: 한국 본사가 한국어로 읽는 경우 ----------
    kr_fee = 230 * 375
    kr_price = kr_fee * 0.20
    kr_review = 230 * 250 / 10
    r = model(price=kr_price, review=kr_review, K=sa_K, O=[0] * 5)
    print(f"\n참고(한국어 출력): 번역료 {kr_fee:,.0f}, 가격 {kr_price:,.0f}, 검수 {kr_review:,.0f}, 공헌 {r['cpage']:,.0f} ({r['margin']:.0%}), 손익분기 {r['be_cust']:.0f}곳, 한국 25곳 누적 {eok(r['cum'])}")


if __name__ == "__main__":
    main()
