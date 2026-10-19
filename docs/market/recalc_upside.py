"""긍정 근거 조사(2026-10-16)가 여는 시나리오 계산. 사우디 기본 시나리오와 같은 모델을 쓴다.

모든 입력은 [가정]이다. 근거는 docs/market/긍정-근거-조사.md 참고.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from recalc_economics import (API, BASE_K, BASE_O, DIAG_PAGES, CONV, FIXED_M,  # noqa: E402
                              OS_CAC_MULT, RATE, SAR, eok, model, scale)

FEE_SAR = 62.5
SA_PRICE = FEE_SAR * 0.20 * SAR             # 4,873원
SA_REVIEW = 0.1667 * 250 * SAR / 10         # 1,625원
SA_K = scale(BASE_K, 251 * 0.10 / 100)      # 5년차 한국 25곳
VOUCHER_SHARE = 0.30                         # 수출바우처 중소기업 자부담(국고 70%)
ME_EXPORTERS = 14_000                        # KOTRA 사장 발언, 중동 수출기업 수


def model_split(pk, po, review=SA_REVIEW, docs=20, K=SA_K, O=BASE_O, fixed_m=FIXED_M, review_k=None):
    """한국 고객과 해외 고객의 장당 가격(과 검수 원가)을 따로 두는 모델. 나머지는 recalc_economics.model과 같다."""
    rk = review if review_k is None else review_k
    ck, co = pk - API - rk, po - API - review
    cac_kr = DIAG_PAGES / CONV * (API + rk)
    cac_os = DIAG_PAGES / CONV * (API + review) * OS_CAC_MULT
    fixed = fixed_m * 12
    cum, npv, prevK, prevO, rows = 0, 0, 0, 0, []
    for y, (k, o) in enumerate(zip(K, O), 1):
        rev = (k * pk + o * po) * docs * 12
        contrib = (k * ck + o * co) * docs * 12
        cf = contrib - fixed - (k - prevK) * cac_kr - (o - prevO) * cac_os
        cum += cf
        npv += cf / (1 + RATE) ** y
        rows.append((y, k, o, rev, cf, cum))
        prevK, prevO = k, o
    return dict(rows=rows, cum=cum, npv=npv)


def line(name, r):
    y5 = r["rows"][-1]
    print(f"{name}: 5년차 고객 한국 {y5[1]:.0f} 해외 {y5[2]:.0f}, 5년차 매출 {y5[3] / 1e8:.2f}억, "
          f"5년차 CF {eok(y5[4])}억, 누적 {eok(r['cum'])}억, NPV {eok(r['npv'])}억")


def main():
    # 0) 재현 확인: 가격을 같게 두면 기존 사우디 기본 시나리오와 같아야 한다
    base = model(price=SA_PRICE, review=SA_REVIEW, K=SA_K)
    split = model_split(SA_PRICE, SA_PRICE)
    assert abs(base["cum"] - split["cum"]) < 1 and abs(base["npv"] - split["npv"]) < 1
    line("기본(재현)", split)

    # 1) 수출바우처: 한국 고객 자부담이 지금과 같은 4,873원이 되도록 정가를 올림
    pk_v = SA_PRICE / VOUCHER_SHARE
    print(f"\n바우처 정가 {pk_v:,.0f}원 (고객 자부담 {pk_v * VOUCHER_SHARE:,.0f}원)")
    line("1 바우처, 고객 경로 그대로", model_split(pk_v, SA_PRICE))

    # 2) 고객 풀: 중동 수출기업 1만4천 곳의 1%를 5년차 한국 고객으로
    K_pool = scale(BASE_K, ME_EXPORTERS * 0.01 / 100)
    line("2 중동 수출기업 1%, 기본 가격", model_split(SA_PRICE, SA_PRICE, K=K_pool))

    # 3) 1+2
    line("3 바우처 + 1%", model_split(pk_v, SA_PRICE, K=K_pool))
    line("3' 바우처 + 1%, 해외 0곳", model_split(pk_v, SA_PRICE, K=K_pool, O=[0] * 5))
    # 한국 고객이 한국어로 읽어 한국어-아랍어 검수자(단어당 230원 × 시간당 250단어 × 6분)가 필요한 경우
    line("3k 바우처 + 1%, 한국 고객 검수 5,750원", model_split(pk_v, SA_PRICE, K=K_pool, review_k=230 * 250 / 10))

    # 4) 법률 검토 시간 기준: 부티크 변호사 시급 400리얄의 15분 = 100리얄을 문서 한 건 가치로, 그 20%
    p_law = 100 * 0.20 * SAR
    line(f"4 변호사 15분 기준 장당 {p_law:,.0f}원", model_split(p_law, p_law))

    # 5) 대학생 팀(고정비 월 200만 원)
    line("5 대학생 팀 + 바우처", model_split(pk_v, SA_PRICE, fixed_m=2_000_000))
    line("5' 대학생 팀 + 바우처, 해외 0곳", model_split(pk_v, SA_PRICE, fixed_m=2_000_000, O=[0] * 5))

    # 6) 바우처 조건에서 해외 0곳으로 5년 누적 0이 되려면 한국 고객이 5년차에 몇 곳이어야 하나
    lo, hi = 0, 5000
    for _ in range(60):
        mid = (lo + hi) / 2
        if model_split(pk_v, SA_PRICE, K=scale(BASE_K, mid / 100), O=[0] * 5)["cum"] < 0:
            lo = mid
        else:
            hi = mid
    print(f"\n6 바우처, 해외 0곳에서 5년 누적 0: 5년차 한국 고객 {hi:.0f}곳 "
          f"(중동 수출기업의 {hi / ME_EXPORTERS:.1%})")
    ck_v = pk_v - API - SA_REVIEW
    print(f"  바우처 장당 공헌이익 {ck_v:,.0f}원, 손익분기 고객 {FIXED_M / ck_v / 20:.0f}곳(급여 있음)")


if __name__ == "__main__":
    main()
