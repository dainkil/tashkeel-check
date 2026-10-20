# 230만 원 검증이 8억 원 결정을 먼저 가른다

Tashkeel Check를 지금 수익 사업으로 시작할 근거는 이번 조사에서도 나오지 않았다. 이 도구 형태에 고객이 돈을 냈거나 내겠다는 직접 증거는 0건이고 [미확인], 사우디에 법인을 둔 한국 기업 전체(70~251곳)가 월 20장씩 사도 연 0.82억~2.94억 원이며, 급여를 넣은 손익분기 270곳은 지금 닿을 수 있는 7~25곳의 11~39배다 [계산]. 같은 일을 하는 제품은 0곳이지만 인접 제품 43곳과 월 약 2.9만~3.7만 원의 범용 LLM 좌석이 같은 예산을 먼저 가져가고, PIF 계열 HUMAIN의 투자를 받은 Arabic.AI가 계약서를 "read, check and draft"하는 에이전트를 예고했다 [문헌○]. 고충은 규정(근로계약 아랍어 우선, Qiwa 계약 기준 사우디화율, 이카마 이름이 어긋나면 은행 거래 불허)으로는 단단하지만, 손실 금액이나 빈도를 보여 주는 공개 자료는 하나도 없다. 공급 쪽에서는 유료 파일럿까지 현금 약 299만 원(인건비 포함 약 4,465만 원), 사우디 외국계 기업이 요구할 엔터프라이즈 준비에 3.55억~4.15억 원과 6~12개월이 든다 [계산]. 장당 단위 경제는 검수자 시급 하나에 달려 있어, 시급이 약 31달러를 넘으면 사우디 기준 가격(장당 4,873원)에서 장당 공헌이 음수가 된다 [계산]. 그래서 정직하게 남는 이유는 "지금 버는 사업"이 아니다. 결정적 검증(EXP-001·002와 사전 감사)이 약 230만 원으로 기본 시나리오 필요 자금 8.28억 원의 0.28%라는 옵션 가치, 아랍어 이름의 모호성 은폐를 재는 측정 장치 자체의 연구·과제 가치, 그리고 규정이 키우는 빈 틈새가 그 이유다. 유일한 흑자 조합인 수출바우처 경로는 지금까지 관찰된 사우디 대상 통번역 바우처 이용이 연 약 4.8건뿐이라, 가장 먼저 확인할 가정이 됐다 [계산].

## 읽는 법과 재현 방법

조사일은 2026-10-20이다. 다섯 갈래 조사 노트(경쟁사 IR·공시, 컨설팅·애널리스트 보고서, 경쟁 구도, 기사와 고충, 공급 비용)를 종합했다. 기존 [사업성 검토](../../feasibility.md)(사우디 기준), [사우디 가격·고객 수 조사](../saudi-price-customers.md), [긍정 근거 조사](../upside-evidence.md)의 수치는 다시 유도하지 않고 그대로 가져왔다. 환율은 프로젝트 값(1달러 1,462원, 1리얄 약 390원)을 쓴다. NZ달러·파운드·유로는 원래 통화로 두고, 원화로 바꾼 곳은 환율을 [가정]으로 적었다. 이 문서는 정확한 번역을 약속하는 제품을 평가하지 않는다. 제품이 약속하는 것은 "모호 구간을 얼마나 잡아내는가"이고, 그 포착률은 아직 실측하지 않았다(EXP-001·002 미실행).

| 표시 | 뜻 |
| --- | --- |
| [확인] | 이 저장소에서 직접 조회·계산했거나, 기존 문서가 원문을 다시 대조한 사실(sources.csv 확인=직접) |
| [문헌○] | 조사 노트가 원문을 열어 확인했다고 기록한 외부 자료(sources.csv 확인=대리). 인용 전에 원문을 다시 확인한다 |
| [요약] | 검색 요약이나 2차 인용으로만 본 값 |
| [단일] | 동적 페이지에서 한 번 조회해 재현하지 못한 값 |
| [가정] | 계산을 위해 둔 값. 근거가 아니다 |
| [계산] | 이 보고서의 스크립트가 낸 값. 입력의 [가정]을 물려받는다 |
| [가설] / [미확인] | 확인할 추정 / 아직 모르는 값 |

모든 계산은 [recalc_demand_supply.py](../recalc_demand_supply.py)가 낸다. 저장소 밖 디렉터리에서 `python3 -I /Users/muna/Documents/tashkeel-check/docs/business/market/recalc_demand_supply.py`로 실행한다. 표준 라이브러리만 쓰고, 기존 `recalc_economics.py`와 `recalc_upside.py`의 상수와 함수를 불러 쓴다. 실행 첫머리(0절)에서 기존 사우디 기본 시나리오(장당 공헌 2,939원, 손익분기 270곳, 5년 누적 −8.28억 원, NPV −3.07억 원)와 바우처 시나리오(5년 누적 +3.77억 원)를 그대로 재현하는지 assert로 확인한다. 아래 표 제목의 "스크립트 n절"이 출력의 해당 절이다. 입력값마다 라벨과 출처 ID가 주석으로 붙어 있고, 새 출처는 [sources.csv](../sources.csv)의 S110~S180이다.

## 1. 고객이 원한다는 직접 증거는 0건이고, 아랍어 문서를 늘리는 규정은 늘었다

이 도구 형태에 돈을 냈거나 내겠다는 공개 자료는 이번에도 찾지 못했다 [미확인]. 이 도구 형태란 아랍어를 못 읽는 책임자에게 이름 독법 후보와 근거를 보여 주고, 근거가 없으면 확정하지 않고 보류하는 검수다. 한국 쪽 기록은 오히려 언어를 애로로 꼽지 않는다. 무역협회의 수출기업 1,090개사 조사에서 언어·번역은 상위 애로에 없다 ([헤럴드경제, S103](https://biz.heraldcorp.com/article/10879858)) [문헌○]. 중소기업의 사우디 진출을 다룬 2025년 기사 두 건은 장벽으로 "현지 규제 장벽, 문화·종교적 이질성"만 든다 ([경북매일, S120](https://kbmaeil.com/article/20250626500123); [MTN, S121](https://news.mtn.co.kr/news-detail/2025100211444863905)) [문헌○]. 법무법인 지평의 2024년 사우디 세미나에서 한국 기업이 던진 질의 6개에도 아랍어나 번역은 없다 ([지평, S122](https://jipyong.com/kr/board/newsletters_main.php?seq=1992)) [문헌○]. 스웨덴 기업 31곳의 2026년 설문 보고서 본문에는 language, Arabic, translation이라는 단어가 나오지 않는다 ([Business Sweden, S123](https://www.business-sweden.com/49c3a4/contentassets/04f9bb4ef241400190cd770e38c27f65/business-climate-survey-saudi-arabia-2026-report.pdf)) [문헌○]. KOTRA는 2024년판 진출전략에서 규정 공지가 "아랍어로만 되어 있는 경우가 다분"하다고 썼다 ([KOTRA 23-173, S125](https://dl.kotra.or.kr/pyxis-api/2/digital-files/d18f72a6-5f75-4f7c-bbb8-f3bd0b37fa77)). 2026년판에서는 그 문장이 빠졌다 ([KOTRA 25-184, S41](https://dl.kotra.or.kr/pyxis-api/2/digital-files/34040e29-1f08-440d-8b99-2d52160cd0ba)) [문헌○]. 2025년판이 꼽은 애로는 "상업법, 투자법, RHQ 등 정부 정책과 규제의 변화"에 대한 "면밀한 모니터링"과 정보 부족이다 ([KOTRA 24-198, S110](https://dl.kotra.or.kr/pyxis-api/2/digital-files/fa211f0c-eeb0-470c-a5cb-f997417c8531)) [문헌○]. 한국 기업에게 아랍어 문제는 따로 떨어진 '언어 애로'가 아니라 규제·서류 부담 안에 묻혀 있다고 읽힌다 [가설].

반면 아랍어 원문 문서의 양과 법적 무게를 늘리는 제도는 2025~2026년에 잇따랐다. 사우디 노동법 제9조는 근로계약의 언어를 아랍어로 정하고, 두 판본이 충돌하면 아랍어 본문이 우선한다 ([Morgan Lewis, S116](https://www.morganlewis.com/blogs/shiftingsandsoflaborlaw/2025/12/navigating-employment-in-the-middle-east-ksa-part-1-takeaways)) [문헌○]. **HRSD는 2026-04-15부터 Qiwa에 전자 등록된 근로계약으로 사우디화율을 계산한다** ([Teamed, S118](https://www.teamed.global/gulf-employment-law/saudi-contracts-probation-notice-and-leave)) [문헌○]. 2025-04-03 시행된 상호법은 영문 상호를 "corresponding Arabic representations"로 심사한다 ([DWF, S119](https://dwfgroup.com/en/news-and-insights/insights/2025/4/saudi-commercial-register-law-and-law-of-trade-names)) [문헌○]. 2023-12-16 시행된 민사거래법은 기존 계약에도 소급 적용된다. 그래서 Covington은 사우디법이 준거법인 계약 전체를 체계적으로 다시 보라고 권고했다 ([Covington, S115](https://www.cov.com/-/media/files/corporate/publications/2023/12/key-features-of-the-new-saudi-civil-transactions-law.pdf)) [문헌○]. 문서를 받는 외국 기업도 늘었다. 지역본부(RHQ) 라이선스는 2024년 상반기 약 517곳 ([KOTRA 24-198, S110](https://dl.kotra.or.kr/pyxis-api/2/digital-files/fa211f0c-eeb0-470c-a5cb-f997417c8531)) [문헌○], 2025년 9월 660곳 ([Mubasher, S114](https://en.sharikatmubasher.com/media-hub/news/21505092/al-falih-saudi-arabia-to-host-over-1000-rhqs-soon?lang=en)) [요약], 2026년 1월 700곳 이상 ([Okaz, S54](https://www.okaz.com.sa/economy/na/2232934)) [문헌○]으로 늘었다. 같은 장관 발언에서 사우디에서 영업하는 외국 기업은 5.2만 곳을 넘는다 [요약]. 사우디 번역업 상업등기는 7,964건으로 1년 새 20% 늘었다 ([Okaz, S89](https://www.okaz.com.sa/economy/na/2268624)) [확인].

GCC 기업의 AI 도입 설문도 정확성 불신을 수치로 보여 준다. McKinsey가 GCC 임원 139명에게 물은 2025년 조사에서 한 기능 이상에 AI를 쓰는 조직은 84%였지만, 확산 단계에 이른 곳은 31%였다. **응답자의 53%가 출력 부정확성을 가장 큰 도입 장애 중 하나로 꼽았고**, 위험·법무·컴플라이언스 기능의 정기 사용은 약 22%에 그쳤다 ([McKinsey, S111](https://gccbdi.org/sites/default/files/2025-11/The-state-of-AI-in-GCC-countries-In-pursuit-of-scale-and-value.pdf)) [문헌○]. Deloitte의 GCC 세무·재무·법무 조사에서는 비도입 비율이 2024년 52%에서 2025년 29%로 줄었고, 38%가 정확도·품질 개선을 우선순위로 꼽았다 ([Deloitte, S112](https://www.deloitte.com/middle-east/en/about/press-room/gcc-leaders-accelerate-genai-adoption-in-tax-finance-and-legal-functions.html)) [문헌○]. Strategy&는 아랍어가 "contracts, customer interaction, and public administration"을 떠받치는데도 "document-processing tools misinterpret text"라고 썼다 ([Strategy&, S113](https://www.strategyand.pwc.com/m1/en/industries/technology/from-automation-to-advantage/from-automation-to-advantage.pdf)) [문헌○]. 그러나 셋 다 자기보고 설문이거나 정성 서술이고, 아랍어 고유명사를 따로 묻지 않았다. 의향의 신호일 뿐 지불의 증거는 아니다.

수요를 상향식으로 세면 아래와 같다. 고객 한 곳이 월 20장을 맡기면 연 1,169,600원을 낸다. 같은 문서를 사우디 공인 번역에 맡기면 5,848,000원이므로, 고객이 아끼는 돈은 연 4,678,400원이다 [계산]. 한국 쪽 모수는 KOTRA의 1968~2023 누적 신규 법인 285곳 ([S110](https://dl.kotra.or.kr/pyxis-api/2/digital-files/fa211f0c-eeb0-470c-a5cb-f997417c8531)) [문헌○]에 2024~2026년 상반기 신규 61곳을 더하면 346곳이다. 수출입은행 누적 343곳 [단일]과 3곳 차이라서, 단일 조회였던 343곳·251곳을 독립 자료가 일부 뒷받침한다 [계산].

**표 1. 상향식 수요 (스크립트 1절)**

| 각도 | 모수 | 월 장수 | 장당 가격 | 100% 점유 시 연 매출 | 닿을 수 있는 몫 |
| --- | --- | --- | --- | --- | --- |
| A1 사우디 법인 한국 기업 (KOTRA 활동 기업) | 70곳 [확인, [S43](https://www.hankookilbo.com/news/article/A2026010707560001645)] | 20장 [가정] | 4,873원 [가정] | 0.82억 원 | 10%면 7곳, 0.08억 원 [계산] |
| A1 같은 정의 (수출입은행 정상 법인) | 251곳 [단일, [S40](https://stats.koreaexim.go.kr/sub/countryStatistics.do?code=사우디아라비아)] | 20장 | 4,873원 | 2.94억 원 | 10%면 25곳, 0.29억 원 [계산] |
| A1′ 같은 251곳, 한국어 출력 가격 | 251곳 | 20장 | 17,250원 [가정] | 10.39억 원 | 25곳, 1.04억 원 [계산] |
| A2 중동 수출기업 1만4천 곳의 1%, 바우처 정가 | 140곳 [모수 확인 [S93](https://www.heraldk.com/article/2026030821342030155), 1%는 가정] | 20장 | 16,244원 [가정] | 5.46억 원 | 1% 자체가 [가정] |
| A2′ 중동 의존 수출기업 1,063곳의 10%, 바우처 정가 | 106곳 [모수 확인 [S44](https://www.korea.kr/briefing/pressReleaseView.do?newsId=156747363), 10%는 가정] | 20장 | 16,244원 | 4.14억 원 | 10% 자체가 [가정] |
| A3 사우디 외국인 보유 상업등기 | 38,640곳 [확인, [S50](https://mc.gov.sa/ar/mediacenter/Documents/MCQ2-2025.pdf)] | 5장 [가정] | 4,873원 | 112.98억 원 | 상한. 아랍어를 못 읽는 책임자 비율 [미확인] |
| A3′ 위에서 이집트·예멘 몫 38.1%를 뺀 값 | 23,907곳 [계산, 몫은 S56 문헌○] | 5장 | 4,873원 | 69.90억 원 | 상한 |
| A3″ 영업 외국 기업 5.2만 곳에서 같은 몫을 뺀 값 | 32,172곳 [계산, 모수 요약] | 5장 | 4,873원 | 94.07억 원 | 상한 |
| A3‴ 지역본부(RHQ) 기업 | 700곳 [문헌○, S54] | 20장 [가정] | 4,873원 | 8.19억 원 | 기존 경로의 5년차 해외 고객 100곳 [가정] |

한국 쪽 모수는 어느 정의를 써도 작다. 100%를 다 잡아도 사우디 기준 가격에서는 연 3억 원을 넘지 않는다. 한국어 출력 가격으로 바꿔야 10억 원대가 된다. 기존 SOM(5년차 한국 25곳과 해외 100곳)은 연 1.46억 원이다 [계산]. 큰 숫자는 모두 사우디 현지 외국계(A3)에서 나온다. 그러나 그 안에서 아랍어를 못 읽는 책임자가 있는 기업의 비율은 공개 자료로 정할 수 없다 [미확인]. 2024년 3분기 투자 라이선스의 적어도 38.1%가 아랍어권인 이집트·예멘 투자자 몫이었다는 점만 확인된다 [문헌○].

**표 2. 하향식 교차 확인 (스크립트 2절)**

| 교차 확인 | 값 | 읽는 법 |
| --- | --- | --- |
| 기존 TAM 상한 ÷ Nimdzi 중동 언어 서비스 수요 11억 달러 ([S01](https://www.nimdzi.com/nimdzi-100-2026/)) | 115.9억 ÷ 16,082억 원 = 0.72% [계산] | 천장 아래에 있다는 확인뿐이다 |
| A3 문서량(월 193,200장)을 사람이 번역할 때의 연 지출 ÷ Statista 사우디 번역 시장(2024, 2,899만 달러) ([S127](https://jahs.qu.edu.sa/index.php/jah/article/download/2749/2569/5267)) | 565억 ÷ 424억 원 = 1.33배 [계산, Statista 값은 요약] | 가정한 문서량만으로 사우디 번역 시장 전체를 넘는다 |
| 번역업 등기 7,964건 × 1명 [가정] × 월 110장 [가정] × 번역료 | 연 2,562억 원 = Nimdzi 중동의 16%, Statista 사우디의 6.0배 [계산] | Statista 값의 정의가 좁다 |
| Statista 사우디 번역 시장 ÷ 번역업 등기 | 등기 1건당 연 5,321,871원 [계산] | 사무소 하나의 매출로 보기 어렵다 |
| Astute GCC 번역 서비스(2023, 21.9억 달러) ([S128](https://www.globenewswire.com/news-release/2024/09/30/2955300/0/en/GCC-Translation-Service-Market-Valuation-to-Hit-US-3-807-85-Million-By-2032-UAE-to-Remain-at-Top-thanks-to-Economic-and-Social-Factors-Says-Astute-Analytica.html)) | 32,002억 원 = Statista의 76배, Nimdzi 중동의 1.99배 [계산, 요약] | 시장조사기관끼리 두 자릿수 배 어긋난다 |
| TAM 상한 ÷ Ken Research 사우디 리걸테크 ([S129](https://www.kenresearch.com/gcc-legal-technology-market.md), [S180](https://www.kenresearch.com/ksa-legal-technology-market-report)) | 2.1%(2025, 3.8억 달러) ~ 4.0%(2024, 2억 달러, 페이지 스스로 'illustrative') [계산] | 신뢰도 낮음 |
| A2의 국고 몫 ÷ 2026 수출바우처 예산 1,502억 원 ([S126](https://hellot.net/news/article.html?no=108100)) | 3.82억 원 = 0.25% [계산, 예산은 요약] | 예산은 제약이 아니다 |
| 관찰된 사우디 대상 통번역 바우처 이용 ([S32](https://www.exportvoucher.com)) | 23건 ÷ 4.8년 = 연 4.8건. A2의 140곳은 그 29배 [계산, 단일 조회 기반] | 수요 쪽이 제약이다 |

하향식 수치는 상한을 정해 주지 못한다. 시장조사기관의 사우디·GCC 번역 시장 추정은 76배까지 벌어진다. 우리가 가정한 현지 문서량(외국인 등기 3.9만 곳 × 월 5장)은 그중 가장 작은 추정(Statista)을 혼자 넘는다. 둘 중 하나가 틀렸다. Statista 값이 좁은 정의이거나, 월 5장 가정이 과하다. 손에 쥔 숫자 가운데 가장 단단한 신호는 오히려 수요 쪽 제약이다. 한국 중소기업이 정부 돈 70%를 받고도 사우디 대상 통번역을 산 기록은 2022년 이후 23건, 연 약 4.8건이다. 언어와 분량은 기록에 없다 [단일]. 바우처 시나리오의 손익분기 56곳은 중동 수출기업 1만4천 곳의 0.40%에 불과하다. 그러나 관찰된 구매 빈도에 견주면 12배다 [계산].

## 2. 같은 일을 하는 제품은 0곳이지만, 예산은 인접 43곳과 LLM 좌석이 먼저 가져간다

경쟁 조사는 검색 30회 범위에서 이름이 확인된 곳만 셌다. 같은 일, 곧 문서 속 아랍어 이름의 모호한 독법을 표시하고 후보와 근거를 비아랍어 독자에게 보여 주며 근거가 없으면 보류하는 제품은 0곳이었다 [문헌○, 검색 범위 한정]. 인접 제품은 43곳이고, 모두 다른 구매자를 겨냥한다.

**표 3. 경쟁 범주 (경쟁 구도 노트 7절)**

| 범주 | 관계 | 이름 확인 | 주 구매자 | 이름 독법·보류 기능 |
| --- | --- | --- | --- | --- |
| 이름 독법 후보 + 근거 + 보류 (비아랍어 독자용) | 직접 | 0곳 | — | — |
| 걸프 법률 AI (글로벌 6, 지역 15) | 인접, 같은 예산 | 21곳 | 아랍어를 읽는 변호사·사내 법무 | 확인된 곳 없음 |
| 번역 품질 추정·검증 | 인접 | 9곳 | 로컬라이제이션팀, 번역사 | 세그먼트·문서 점수. 다중 엔진 서비스는 다수결로 고름 |
| 아랍어 이름 매칭·음역 데이터 | 인접·부품 | 8곳 | 은행 준법팀, OEM | 매칭 점수. 후보 생성용 데이터(CJKI)는 있음 |
| 아랍어 특화 AI (번역·문서) | 인접·채널 | 4곳 | 아랍어권 기업·정부 | 확인 안 됨 |
| 모음 복원 API | 인접·부품 | 1곳 (+오픈소스 2) | 개발자 | 한 가지 답을 냄 |
| 한국 업체의 아랍어 법률 문서 서비스 | — | 0곳 (6곳 확인) | — | — |
| 범용 번역 2, 범용 LLM 4, 사람 번역 | 대체재 | — | 전부 | 프롬프트나 사람 판단에 따름 |

가장 붐비는 곳은 걸프 법률 AI다. 지역 업체들은 아랍어 원문 이해와 이중언어 계약 검토를 판다. 예를 들어 사우디의 Clauze.AI는 전 White & Case 리야드 사무소장이 세웠고 그 로펌의 전략투자를 받았다 ([Zawya, S144](https://www.zawya.com/en/press-release/companies-news/clauze.ai-launches-as-the-first-enterprise-legal-ai-platform-built-for-saudi-arabia-and-the-region-483577)) [문헌○]. 레바논의 HAQQ는 월 30·100·300달러 요금제를 공개한다 ([HAQQ, S142](https://www.haqq.ai/blog/best-legal-ai-mena-law-firms-2026.html)) [문헌○]. 지역 목록은 이해당사자인 HAQQ 한 곳의 집계에 크게 기댄다 ([HAQQ, S141](https://haqq.ai/blog/legal-ai-mena-2026.html)). 글로벌 쪽에서는 LexisNexis가 2026-06-24 GCC 6개국 법률 콘텐츠로 중동판을 내며 "multi-million-dollar" 투자를 밝혔다. 다만 아랍어를 명시하지는 않았다 ([LexisNexis, S139](https://www.lexisnexis.com/community/pressroom/b/news/posts/lexisnexis-introduces-trusted-legal-ai-for-the-middle-east-powered-by-regional-legal-intelligence)) [문헌○]. 이들 법률 AI의 고객은 아랍어를 읽는 사람이다. 그래서 기능이 겹친다기보다 같은 예산을 두고 다툰다. HAQQ는 AI 법률 번역을 "a draft to be audited"로 다루라고 권하면서도, 점검 목록(의무 동사, 정의어, 숫자·날짜, 부정, 관할)에 고유명사 표기를 넣지 않았다 ([HAQQ, S143](https://www.haqq.ai/blog/ai-legal-translation-arabic-english)) [문헌○]. 이름 독법이 업계 점검 항목으로 아직 자리 잡지 않았다는 신호다. 수요가 없다는 신호일 수도 있다.

이름 매칭 쪽은 돈이 오래전부터 붙은 시장이다. 영국 G-Cloud 14 가격 문서에는 Rosette Name Translator 연간 라이선스가 언어당 £158,189로 실려 있다 ([UK Digital Marketplace, S147](https://assets.applytosupply.digitalmarketplace.service.gov.uk/g-cloud-14/documents/701282/388528207503081-pricing-document-2025-09-12-1334.pdf)) [요약]. CJKI는 아랍 인명과 로마자 변형 데이터(DAN), 외국 이름의 아랍어 표기 24만 건 이상(DAFNA)을 라이선스로 판다 ([CJKI, S146](https://www.cjk.org/data/arabic/proper/dafna/)) [문헌○]. 그러나 이 도구들의 출력은 "두 이름이 같은 사람인가"라는 매칭 점수다. 문서 속 이름의 독법 후보와 근거를 독자에게 보여 주지 않는다. 경쟁자라기보다 부품 공급처다.

자금은 아랍어 특화 AI로 몰린다. **2026-09-01 PIF 소유의 HUMAIN이 Arabic.AI(구 Tarjama)에 전략투자를 했다**(금액 비공개). 첫 공동 제품 가운데 하나가 "read, check and draft contracts, tenders and filings"하는 문서 에이전트다 ([Wamda, S130](https://www.wamda.com/en/2026/09/arabicai-secures-strategic-investment-humain)) [문헌○]. Arabic.AI는 이미 Contract Reviewer를 팔고 "700+ retained clients"를 내세우지만, 이름 음역이나 불확실성 표시는 언급하지 않는다 ([Arabic.AI, S131](https://arabic.ai)) [문헌○]. 이 회사는 2025년 매출 2,000만 달러에 Series A 1,500만 달러를 받았다 ([Enterprise AM, S90](https://enterpriseam.com/uae/2025/05/22/tarjama-secures-usd-15-mn-in-series-a-round-to-expand-arabic-ai/)) [확인]. 가장 그럴듯한 진입자다. 같은 회사가 번역관리시스템(Cleverso)에 검수 부품을 붙일 채널 후보이기도 하다 [가설].

**표 4. 고객이 견주는 가격 (스크립트 3절)**

| 비교 대상 | 가격 | 사우디 기준 장당 4,873원과의 관계 |
| --- | --- | --- |
| Google 문서 번역 | 장당 $0.08 = 117원 [확인, [S06](https://cloud.google.com/translate/pricing)] | 도구가 41.7배 비쌈 [계산] |
| TAUS 품질 추정 | 장당 약 €0.9 ≈ 1,440원 [문헌○, [S09](https://web.archive.org/web/20260612111722/https://www.taus.net/pricing/). 1유로 1,600원은 가정] | 3.4배 [계산] |
| MachineTranslation.com (22개 모델 다수결) | 건당 $1.50부터 = 2,193원 [문헌○, [S145](https://www.machinetranslation.com/translation/english-arabic)] | 2.2배 [계산] |
| Claude Pro, ChatGPT Business(연 결제) | 월 $20 = 29,240원 [문헌○ [S149](https://claude.com/pricing), 요약 [S151](https://elephas.app/resources/chatgpt-business-pricing)] | 6.0장 값. 바우처 정가로는 1.8장 [계산] |
| Claude Team Standard(월 결제), M365 Copilot Business | 월 $21~25.20 = 30,702~36,842원 [문헌○, [S149](https://claude.com/pricing), [S150](https://www.microsoft.com/en-us/microsoft-365-copilot/pricing)] | 6.3~7.6장 값 [계산] |
| arbitr Govern | 월 $100 = 146,200원 [문헌○, [S135](https://www.arbitr.ai/pricing)] | 30장 값 [계산] |
| 사우디 공인 번역 | 장당 24,367원 [확인] | 도구는 그 20% |
| 국내 아랍어→한국어 번역 | 장당 86,250원 [확인] | 바우처 정가 16,244원은 그 19% |

가격 위치가 애매하다. 장당 4,873원은 기계 번역과 품질 추정보다 2.2~41.7배 비싸고, 사람 번역보다는 싸다. 범용 LLM 좌석 하나가 사우디 기준 6~7.6장 값이다. 그래서 월 20장을 맡기는 고객의 도구 비용(97,467원)은 Claude Pro 좌석의 3.3배다 [계산]. 고객이 "LLM에 직접 이름 후보를 물어보기"를 택하면 좌석 하나로 끝난다. 이 도구가 좌석과 다투려면 근거 수집과 보류 규칙을 일관되게 지킨다는 측정값을 팔아야 한다. 그 측정값이 EXP-002의 C0~C3 비교다(미실행).

상장사 공시는 이 범주의 운명을 가장 직접 보여 준다. Straker는 단독 검증 제품 Verify를 "the next-tier premium verification service"로 냈다. 그러나 FY26 상반기 Verify 구독 매출 증분은 NZ$0.2m였고, 발표 자료에는 "6 customers looking at customer models and Verify combined"라고 적혔다 ([Straker 반기 발표, S133](https://hermes-cdn.investorhub.com/announcement-pdfs/asx/7280100.pdf)) [문헌○]. 회사는 Verify를 단일 플랫폼 arbitr로 흡수하고 있다(완료 목표 FY27 3분기). FY26 매출은 NZ$38.8m로 14% 줄었다 ([Straker 연차보고서 2026, S132](https://hermes-cdn.investorhub.com/announcement-pdfs/asx/7710252.pdf)) [문헌○]. 그런데도 회사는 2026-09-29 사명을 Arbitr로 바꾸며 "AI did not remove that need. It multiplied the volume and moved the risk to the moment content goes live"라고 썼다 ([Arbitr 사명 변경 공시, S134](https://hermes-cdn.investorhub.com/announcement-pdfs/asx/7758530.pdf)) [문헌○]. 연차보고서는 "Agents prepare; humans approve what ships"를 우선순위로 적었다. 동시에 단어당 과금은 AI 원가 하락과 함께 무너진다며 구독·크레딧으로 옮겼다. Managed Services 매출은 효율 개선분을 고객에게 넘기면서 28.8% 줄었다 ([S132](https://hermes-cdn.investorhub.com/announcement-pdfs/asx/7710252.pdf)) [문헌○]. 반대 방향의 신호도 있다. RELX의 Legal 부문은 2026년 상반기 £959m로 기초 성장 10%를 냈다 ([RELX 반기 발표, S138](https://www.relx.com/~/media/Files/R/RELX-Group/documents/results/interim-presentations/2026-first-half-presentation.pdf)) [문헌○]. CFO는 AI 기능을 고정 구독으로 팔고, 토큰 원가가 "less than 1% of our overall cost base"라고 말했다 ([RELX 녹취, S137](https://www.relx.com/~/media/Files/R/RELX-Group/documents/investors/transcripts/first-half-results-2026-transcript.pdf)) [문헌○]. RWS는 번역 부문(Transform)이 4.6% 줄었지만 사람 서비스 매출 비중이 "higher than anticipated"였다고 공시했다 ([RWS 반기, S136](https://www.investegate.co.uk/announcement/rns/rws-holdings--rws/half-year-financial-report/9612324)) [문헌○]. 정리하면, 단어·장 단위로 파는 번역 대비 할인 상품은 단가 하락에 휩쓸린다. 법률 워크플로 안의 "신뢰할 수 있는 AI"는 구독료를 받는다. 검증만 떼어 판 상품은 팔리지 않았다.

한국에서는 경쟁 공백이 사실로 보인다. 베링랩 사이트의 지원 언어 문구에 아랍어가 없고 ([베링랩, S148](https://www.beringlab.com)) [문헌○], 플리토의 2025 사업보고서와 수시공시에는 중동·사우디 매출이나 계약이 없다. 아랍어는 "영어-아랍어와 같은 희소 언어 조합"을 학습 데이터로 판다는 한 문장으로만 나온다 ([플리토 2025 사업보고서, S140](https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260319000117)) [문헌○]. 이 공백이 기회인지 수요 부재인지는 공개 자료로 가를 수 없다. 그럴듯한 진입 경로는 셋이다. Arabic.AI–HUMAIN의 "check" 에이전트에 이름 검증이 붙는 경우, 법률 번역과 후편집 조직을 갖춘 베링랩이 아랍어를 더하는 경우, 범용 LLM이 불확실한 고유명사 표시를 기본 동작으로 넣는 경우다 [가설]. 이번 자료에 셋 다 진입 신호는 없다.

## 3. 고충은 규정에 적혀 있고, 손실 금액은 아직 아무도 세지 않았다

**표 5. 고객 고충 (기사·고충 노트 9절 요약)**

| # | 누가 | 문서 | 무엇이 잘못되나 | 비용·빈도 근거 | 근거 강도 |
| --- | --- | --- | --- | --- | --- |
| P1 | 사우디 법인의 외국인 직원과 HR·GRO | 이카마, 여권, 은행 서류 | 아랍어 이름과 영문 이름이 어긋나 계좌 개설·거래가 막힘 | 건수·금액 통계 없음. 수정은 무료이고 몇 분 걸린다는 경험담 | 규정 [확인, [SAMA 회람 S77](https://www.rulebook.sama.gov.sa/ar/node/6961)] + 2026년 정부 전자 서비스 + 일화 |
| P2 | UAE 비자·EID 신청자와 기업 PRO | 여권, 비자 신청서, EID | 나라마다 여권의 아랍어 음역이 달라 성이 불일치하고 신청이 보류됨 | 수정 1회당 2~7영업일, EID는 5~7영업일 추가 [문헌○] | 업체 블로그 1건 |
| P3 | 사우디 법인의 비아랍어권 HR 관리자 | Qiwa 근로계약(추가 조항 최대 27개 × 1,000자) | 충돌 시 아랍어 우선. 2026-04-15부터 사우디화율이 Qiwa 계약 기준 | 수치 없음. Nitaqat 등급이 비자·근로허가 갱신과 연결 | 법령·로펌 자료 [문헌○] |
| P4 | 사우디 법인 설립·변경 담당자 | 상업등기, 상호 | 영문 상호를 아랍어 대응 표기로 심사. 변경 시 15일 안에 갱신 | 반려 사례·비용 없음 | 법령 요약 [문헌○] |
| P5 | 정부 발주 사업의 건설·플랜트 기업 | 정부조달 표준계약 | 표준 양식 15건 중 영문본은 7건. 영문본 분쟁 조항이 구법 잔재로 보임 | 번역 원인 분쟁 비용 수치 없음 | 2020년 기고 [문헌○] |
| P6 | 분쟁 당사자 | 중재조항 번역본 | 결함 있는 아랍어 번역으로 하급심이 중재조항을 달리 해석 | 상고심까지 감. 금액 미상 | 판례 1건 [확인, 기존 조사] |
| P7 | 사우디 진출 한국 기업 | 규정 공지, 통관 서류 | 공지가 아랍어로만 나오고 세관마다 기준이 다름 | 수치 없음 | KOTRA 2024년판에만 있음 [문헌○] |
| P8 (범위 밖) | 수출 중소기업 | 제품 라벨 | 아랍어 라벨이 필수(한국어·영어→아랍어 방향) | 성약까지 약 7개월(사례 1건) | KOTRA 사례 [문헌○] |

출처: P1은 SAMA 회람 외에 [Arab News 2012, S155](https://www.arabnews.com/node/415068), [expat.com, S159](https://www.expat.com/en/forum/middle-east/saudi-arabia/546613-i-tried-opening-a-account-in-anb-but-refused-bcoz-of-name-spelling.html), [KSA Expats, S152](https://ksaexpats.com/?p=51779), [AJEL, S153](https://english.ajel.sa/news/l2hzxgy26), [Life in Saudi Arabia, S154](https://lifeinsaudiarabia.net/change-name-iqama-saudi-arabia/). P2는 [Dubai South Business Hub, S156](https://dubaisouthbh.com/blogs/typing-errors-on-a-visa-application-and-how-to-fix-them), P3는 [Morgan Lewis, S116](https://www.morganlewis.com/blogs/shiftingsandsoflaborlaw/2025/12/navigating-employment-in-the-middle-east-ksa-part-1-takeaways)·[Paul Hastings, S117](https://www.paulhastings.com/insights/practice-area-articles/saudi-arabia)·[Teamed, S118](https://www.teamed.global/gulf-employment-law/saudi-contracts-probation-notice-and-leave), P4는 [DWF, S119](https://dwfgroup.com/en/news-and-insights/insights/2025/4/saudi-commercial-register-law-and-law-of-trade-names), P5는 [KOTRA 해외시장뉴스, S158](https://dream.kotra.or.kr/kotranews/cms/news/actionKotraBoardDetail.do?SITE_NO=3&MENU_ID=130&CONTENTS_NO=1&bbsGbn=246&bbsSn=246&pNttSn=186066), P6는 [K&L Gates, S76](https://www.klgates.com/Dubai-Court-of-Cassation-Holds-Clause-Providing-for-Court-Provisional-Measures-Not-a-Waiver-of-Arbitration-Agreement-2-18-2025), P7은 [KOTRA 23-173, S125](https://dl.kotra.or.kr/pyxis-api/2/digital-files/d18f72a6-5f75-4f7c-bbb8-f3bd0b37fa77), P8은 [KOTRA 25-184, S41](https://dl.kotra.or.kr/pyxis-api/2/digital-files/34040e29-1f08-440d-8b99-2d52160cd0ba)에서 왔다.

가장 단단한 고충은 이름이다. 제품의 핵심 기전과도 정확히 겹친다. 이카마의 "Usman"을 "Othman"으로 고치지 못해 ANB 지점 두세 곳에서 계좌 개설을 거부당한 사례가 있다 [문헌○, 일화]. 하나의 아랍어 철자(عثمان)가 여러 로마자로 갈라지는 문제다. 사우디 정부는 2026년에 이 수정을 서비스로 만들었다. 7월에는 기업용 Muqeem에 "Translated Name Correction"을, 9월 무렵에는 국민용 Absher에 영문 이름 수정을 열었다 [문헌○]. 수정 수요가 서비스를 만들 만큼 있다는 간접 신호다. 그러나 같은 자료는 Jawazat 방문 수정이 무료이고, Muqeem 수정은 "After 2 minutes" 반영됐다고 전한다 [문헌○, 일화]. 고치는 일 자체는 싸다. 비용은 서명·제출 뒤에야 불일치를 발견해 생기는 거래 차단과 재제출에서 나온다. 그 비용을 금액으로 만든 자료는 없다 [미확인].

고충의 주인도 좁혀진다. 이름 수정은 고용주의 GRO가 Muqeem에서 하므로 처리자는 사우디 법인의 HR·GA 부서다. 이것은 "사우디에 법인을 둔 한국 기업" 가설과 맞는다. 다만 한국인 주재원 본인의 이름은 여권 로마자가 기준이라 문제가 덜하다. 위험이 큰 쪽은 아랍어 원문만 있는 사우디 상대방(회사·개인)의 이름이다 [가설]. 그 유형의 분쟁 사례는 찾지 못했다. 중소 수출기업에게 실제로 보이는 아랍어 요건은 라벨(P8)이다. 번역 방향이 반대라서 지금 제품의 근거로 쓸 수 없다. 2026년 3월 KOTRA에 늘어난 법률 자문 요청도 원인은 전쟁에 따른 공기 지연·지체상금이었고, 언어가 아니었다 ([한국경제, S124](https://www.hankyung.com/article/202603098366i)) [문헌○].

제도는 "AI 번역 + 면허 번역사 검증"으로 굳어지는 중이다. UAE 검찰은 사법 번역용 AI "Bayan"을 시범 운영하면서도 "all translations issued for judicial purposes remain subject to validation by licensed translators"라고 밝혔다 ([Gulf News, S157](https://gulfnews.com/uae/uae-public-prosecution-launches-bayan-smart-translation-centre-1.500305922)) [문헌○]. 비아랍어권 관리자는 공인 번역본을 받아도 그 안의 이름과 조항이 맞는지 스스로 확인할 수단이 없다. 이 빈자리가 Tashkeel Check의 위치다. 공인 번역사의 서명을 대체하지 않고, 그 앞뒤에서 하는 내부 검토다.

## 4. 유료 파일럿은 현금 약 299만 원, 엔터프라이즈 준비는 3.55억 원 이상과 6~12개월이 든다

고객이 요구하는 수준은 단계마다 다르다. 한국 중소기업 대상 파일럿에는 강제 인증이 없다. 다만 문서를 해외 LLM API로 보내는 순간 개인정보 국외 처리위탁이 된다. 계약 이행에 필요한 이전을 처리방침에 공개하면 동의 없이 갈 수 있다. 위반 과징금 상한은 전체 매출액의 3%다 ([DLA Piper, S169](https://www.dlapiperdataprotection.com/?t=law&c=KR)) [문헌○]. 사우디 외국계 기업이 고객이면 요구가 무거워진다. SDAIA는 적정성 국가 목록을 공개하지 않았다. 그래서 Saudi SCC와 이전 전 위험평가가 사실상 기본이고, 외부 벤더로 보낼 때는 BCR을 쓸 수 없다 ([King & Spalding, S168](https://www.kslaw.com/insights/articles/international-personal-data-transfers-under-saudi-arabias-data-protection-law)) [문헌○]. 정부기관·핵심기반시설이 아닌 민간 고객에게 사우디 안 호스팅을 의무로 정한 규정은 찾지 못했다 [미확인]. 그래도 엔터프라이즈 조달에서 요구할 수는 있는데, Anthropic API의 지역 옵션은 global과 us뿐이고 ([Claude API 가격, S161](https://platform.claude.com/docs/en/about-claude/pricing)) [문헌○] 사우디 상주 옵션을 내건 1P LLM API는 확인되지 않았다. AWS와 Azure의 사우디 리전은 2026년 4분기에야 열린다 ([W.Media, S171](https://w.media/aws-saudi-arabia-cloud-region-set-for-december-2026-launch/); [Microsoft, S172](https://news.microsoft.com/source/emea/2026/02/microsoft-confirms-saudi-arabia-datacenter-region-available-for-customers-to-run-cloud-workloads-from-q4-2026/)) [문헌○]. 공인 번역은 상무부 면허를 받은 번역사·사무소의 행위다 ([US ITA, S170](https://www.trade.gov/index.php/country-commercial-guides/saudi-arabia-licensing-requirements-professional-services)) [문헌○]. 소프트웨어가 대신할 수 없으므로 제품은 "공인 번역 전후의 내부 점검"에 머물러야 한다.

품질 요구는 "정확도 몇 %"가 아니라 "신분증 표기와 정확히 같은가"라는 이진 기준이다([SAMA 회람, S77](https://www.rulebook.sama.gov.sa/ar/node/6961), ADGM 공증 안내) [확인]. 그래서 이 제품의 품질 지표는 모호 구간 포착률과 근거 없는 확정 비율이어야 한다. 품질 추정 벤더는 이런 수치를 공개하지 않는다. 기술 수준은 프로젝트의 가설과 같은 방향이다. 중의성 중심 데이터셋에서 문맥이 있는 문장의 모음 복원은 GPT-4o가 CER 2.0%까지 한다. 같은 표에서 아랍어 특화 소형 모델은 ALLaM 20.8%, Jais-13B 61.9%였다 ([Toyin 외 LREC 2026, S102](https://aclanthology.org/2026.lrec-1.40/)) [문헌○]. 반면 모음 없는 고유명사는 GPT-4o가 아랍어만 보고 36.7~55.9%만 맞혔다 ([Bondok 외, S70](https://arxiv.org/html/2505.02656v3)) [확인]. 문장은 거의 풀리고 이름은 안 풀린다. 다만 이것은 2024년 세대 모델의 결과이고, 2026년 모델의 이름 성능은 아무도 재지 않았다 [미확인]. 사우디 데이터 상주를 이유로 현지 소형 모델을 고르면 정확도를 잃을 위험이 있다 [가설]. 라이선스도 걸린다. 지금 쓰는 형태소 DB `morphology-db-msa-r13`은 GPL v2이고, 걸프 DB `glf-01`은 CC BY 4.0이다 ([확인], 로컬 catalogue; [CAMeL Tools 문서, S178](https://camel-tools.readthedocs.io/en/latest/reference/packages.html)). SaaS로만 제공하면 배포가 아니라는 해석이 흔하다. 그러나 엔터프라이즈 고객이 온프레미스 설치를 요구하면 GPL 의무가 생긴다 [가설, 법률 검토 필요].

**표 6. 장당 운영비와 검수자 시급 민감도 (스크립트 4절)**

| 검수자 시급 가정 | 시급 | 장당 검수(6분) | 장당 변동비(API 310원 포함) | 4,873원(사우디 기준)에서 공헌 / 손익분기 | 16,244원(바우처 정가) | 17,250원(한국어 출력) |
| --- | --- | --- | --- | --- | --- | --- |
| 기존 모델: 사우디 단어 단가 환산 41.7리얄 [가정] | 16,248원 | 1,625원 | 1,935원 | 2,939원 / 270곳 | 14,310원 / 56곳 | 15,315원 / 52곳 |
| 이전 판: 두바이 100디르함 [가정] | 39,809원 | 3,981원 | 4,291원 | 582원 / 1,364곳 | 11,954원 / 66곳 | 12,959원 / 61곳 |
| 평가셋 작업자 $30 [가정] | 43,860원 | 4,386원 | 4,696원 | 177원 / 4,479곳 | 11,548원 / 69곳 | 12,554원 / 63곳 |
| ProZ 아랍어-영어 프리랜서 $35 [요약, [S164](https://www.proz.com/profile/5582)] | 51,170원 | 5,117원 | 5,427원 | **−554원 / 없음** | 10,817원 / 73곳 | 11,823원 / 67곳 |
| ProZ 아랍어-영어 프리랜서 $45 [요약] | 65,790원 | 6,579원 | 6,889원 | **−2,016원 / 없음** | 9,355원 / 85곳 | 10,361원 / 77곳 |
| 한국어-아랍어 검수자 230원 × 시간당 250단어 [가정] | 57,500원 | 5,750원 | 6,060원 | −1,187원 / 없음 | 10,184원 / 78곳 | 11,190원 / 71곳 |

장당 원가는 사실상 검수자 시간이다. API는 Sonnet 5.5 표준가로 장당 307원이다. 모델 상수는 310원을 쓴다. Batch로 돌리면 154원, US 전용 추론이면 338원, Haiku 5.5면 15원이다 [계산, 단가는 [S161](https://platform.claude.com/docs/en/about-claude/pricing) 문헌○, 장당 토큰은 가정]. 프로젝트가 설정한 OpenAI 모델도 같은 $2/$10이다 ([OpenAI, S162](https://developers.openai.com/api/docs/pricing)) [문헌○]. Gemini 3.1 Pro도 입력 $2라서 상위 모델 가격은 한곳에 모여 있다 ([Google, S163](https://ai.google.dev/gemini-api/docs/pricing)) [문헌○]. 기존 모델에서 검수 원가는 장당 변동비의 84%다. **사우디 기준 가격에서 장당 공헌이 0이 되는 검수자 시급은 45,633원, 약 31.2달러다** [계산]. 기존 모델의 시급 16,248원은 사우디 공인 번역의 단어 단가에서 거꾸로 환산한 값이다. 실제로 그 값에 아랍어-영어 검수자를 구할 수 있는지는 확인되지 않았다. ProZ 프로필에서 흔한 시급(35~45달러)은 그 3.1~4.0배다 [요약]. 그 시급이면 사우디 기준 가격에서는 장마다 적자가 난다. 바우처 정가나 한국어 출력 가격에서는 같은 시급으로도 손익분기가 67~85곳에 머문다 [계산].

**표 7. 단계별 구축·운영 비용 (스크립트 5·6절)**

| 단계 | 항목 | 산식 | 금액 [계산] |
| --- | --- | --- | --- |
| 유료 파일럿 (한국 중소기업, 인증 없음) | 엔지니어 | 1명 × 6개월 [가정] × 6,943,457원 [확인, [S160](https://files-scs.pstatic.net/2024/12/29/Yp9k9cqjwa/2025년_적용_SW기술자_평균임금_공표.pdf)] | 41,660,742원 |
| | 평가셋 | 500구간 × 2명 × 3분 = 50시간 × $30 [가정] | 2,193,000원 |
| | 무료 진단 | 5곳 × 20장 × (310원 + 1,625원) [가정] | 193,477원 |
| | 보험 | 번역가 E&O 최저 연 $410 [요약, 2021, [S174](https://nxtbook.com/nxtbooks/chronicle/20210102/index.php?startid=40)] | 599,420원 |
| | 처리방침·국외 이전 법무 | — | [미확인] |
| | 합계 | 현금(인건비 제외) / 인건비 포함 | 2,985,897원 / 44,646,639원 |
| 엔터프라이즈 준비 (사우디 외국계, 첫해) | SOC 2 첫해 | 25명 스타트업 $28,000 [문헌○, [S165](https://drata.com/learn/soc-2/cost)] | 40,936,000원 |
| | ISO 27001 심사 | Stage 1+2 $30,000 [요약, [S179](https://www.konfirmity.com/blog/iso-27001-audit-cost)]. 영국 기준은 £6,250~8,750 + 컨설팅 £5,000~40,000 [문헌○, [S166](https://hightable.io/briefing-on-iso-27001-certification-costs/)] | 43,860,000원 |
| | ISMS-P 간편인증 | 수수료 [문헌○, [S167](http://www.boannews.com/news/articleView.html?idxno=131534)] | 6,000,000~11,000,000원 |
| | PDPL SCC·위험평가·약관 검토 | 30시간 [가정] × 부티크 변호사 400~900리얄 [문헌○, [S99](https://globallawexperts.com/lawyer-fees-saudi-arabia/)] | 4,678,400~10,526,400원 |
| | 인력 | 엔지니어 3명 + 보안 0.5명 × 12개월 [가정] | 3.09억 원 |
| | 사우디 리전 DB 할증 | 담맘 $158 − 아이오와 $99 [문헌○, [S173](https://www.bytebase.com/dbcost/cloudsql/instance/db-standard-2.md)] | 월 86,258원 (손익분기 물량 기준 장당 16원) |
| | 합계 | 인증·법무(SOC 2 하나) / 인증 셋 다 / 인력 포함 | 0.46억~0.51억 / 0.95억~1.06억 / 3.55억~4.15억 원 |
| | 기간 | SOC 2 Type 2 6~12개월, ISO 27001 약 6개월 [문헌○] | 파일럿 6개월 뒤 시작하면 첫 엔터프라이즈 판매는 12~18개월째 |

같은 6개월을 기존 모델의 고정비(2명 + 기타)로 버티면 95,321,484원이다 [계산]. 사우디 안에서 LLM 추론까지 처리해야 하면 자체 GPU 호스팅이나 사우디 리전 관리형 LLM 비용이 붙는다. 이 비용은 표에 없다 [미확인]. 비교 사례도 짧은 길을 보여 주지 않는다. 베링랩은 2020년에 법인을 세워 2021년 매출 4억 원, 2022년 20억 원과 손익분기, 2023년 27억 원을 냈다. 그러나 2012년부터 해 온 번역 사업과 고객 기반 위에서 출발했다 ([딜사이트, S175](https://dealsite.co.kr/articles/125499)) [문헌○]. BHSN은 2025년 3월까지 누적 160억 원을 투자받았다 ([파이낸셜뉴스, S176](https://www.fnnews.com/news/202503301206121224)) [문헌○]. 품질 추정 전문 Unbabel은 9,100만 달러를 모은 뒤 2025년 TransPerfect에 "relatively low value"로 팔렸다 ([Wikipedia, S177](https://en.wikipedia.org/wiki/Unbabel)) [문헌○]. Straker는 Verify와 자체 소형 모델에 연 NZ$1.9m~2.3m의 개발비를 자본화했고, FY26에 소프트웨어 개발 자산 NZ$3.0m을 손상 처리했다 ([S132](https://hermes-cdn.investorhub.com/announcement-pdfs/asx/7710252.pdf)) [문헌○]. 연구인력 70명을 둔 플리토의 2025년 연구개발비는 13.2억 원이었다 ([S140](https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260319000117)) [문헌○]. 검증 전문 제품은 오래 걸리거나 독립 사업으로 남지 못했다.

## 5. 손익분기 270곳과 닿을 수 있는 7~25곳 사이의 간격

**표 8. 손익분기 대 닿을 수 있는 고객 (스크립트 6·7절)**

| 경로 | 손익분기 고객 (월 20장) | 닿을 수 있는 고객 | 간격 [계산] |
| --- | --- | --- | --- |
| 사우디 기준 가격, 급여 있음 | 270곳 | 한국 쪽 7~25곳(후보의 10%) / 후보 전부 70~251곳 | 11~39배 / 1.1~3.9배 |
| 같은 가격, 검수자 시급 31.2달러 초과 | 없음(장마다 적자) | — | — |
| 한국어 출력 가격 17,250원 | 71곳 | 7~25곳 / 70~251곳 | 2.8~10.1배 / 0.28~1.01배 |
| 대학생 팀(급여 없음) | 34곳 | 7~25곳 / 70~251곳 | 1.4~4.9배 / 0.14~0.49배 |
| 바우처 정가 16,244원 | 56곳 | 관찰된 사우디 대상 통번역 바우처 이용 연 4.8건 | 12배 |
| 사우디 외국계 엔터프라이즈 | 인증·법무를 1년에 회수하려면 65~73곳, 인력까지면 503~511곳 | RHQ 700곳, 기존 경로의 5년차 해외 100곳 [가정] | 월 5장이면 각 259~292곳, 2,012~2,045곳 |

**표 9. 시나리오별 필요 자금 (스크립트 7절)**

| 시나리오 | 5년 누적 | 필요 자금(누적 최저점) | 월 고정비 몇 개월분 | 첫 흑자 연차 |
| --- | --- | --- | --- | --- |
| 사우디 기본 | −8.28억 원 | 8.28억 원 | 52개월 | 없음 |
| 사우디 기본, 해외 고객 0곳 | −9.11억 원 | 9.11억 원 | 57개월 | 없음 |
| 사우디 기본, 검수자 $35 | −11.65억 원 | 11.65억 원 | 73개월 | 없음 |
| 대학생 팀 | +0.05억 원 | 0.48억 원 | 24개월(월 200만 원 기준) | 4년차 |
| 바우처 + 중동 수출기업 1% | +3.77억 원 | 1.96억 원 | 12개월 | 3년차 |
| 바우처 + 1%, 해외 고객 0곳 | +2.94억 원 | 1.97억 원 | 12개월 | 3년차 |
| 바우처 + 1%, 검수자 $35 | −2.55억 원 | 3.37억 원 | 21개월 | 4년차 |
| 대학생 팀 + 바우처 | +1.87억 원 | 0.16억 원 | 8개월(월 200만 원 기준) | 2년차 |

간격은 두 군데서 생긴다. 첫째는 고객 수다. 사우디 기준 가격에서는 한국 쪽 후보를 전부 얻어도 손익분기에 닿지 않는다. 가격 기준을 한국어 출력이나 바우처로 바꿔야 손익분기가 후보 안으로 들어온다. 둘째는 검수자 원가다. 이번 조사에서 새로 드러난 위험이다. 기존 문서의 흑자 조합(바우처 + 1%)도 검수자를 ProZ 하단 시급으로 구하면 5년 누적 −2.55억 원으로 돌아선다 [계산]. 해외 엔터프라이즈 경로는 준비비 자체가 장벽이다. 인증과 법무만 1년에 회수하려 해도 월 20장 고객 65~73곳이 필요하다. 기존 계획이 5년차에야 해외 100곳을 가정했다는 점에 비추면, 엔터프라이즈 준비는 한국 쪽에서 수요가 확인된 뒤의 일이다.

## 6. 해야 할 이유는 싼 검증과 측정 가치이고, 사업성은 그 검증이 가린다

지금 수익이 나는 사업이라는 이유는 성립하지 않는다. 사우디 기본 시나리오의 NPV는 −3.07억 원이고, 5년 동안 한 해도 흑자가 없다. 아래 다섯 이유는 강한 것부터 적었다. 앞의 둘은 결과와 상관없이 성립하고, 뒤의 셋은 싼 검증이 맞다고 확인해 줘야 성립하는 조건부 이유다.

**표 10. 이 프로젝트를 해야 하는 이유**

| 이유 | 근거 | 성립 조건 | 반증(이것이 나오면 이유가 사라진다) |
| --- | --- | --- | --- |
| 1. 결정적 검증이 싸다(옵션 가치) | EXP-001은 형태소 분석기만 써서 API 0원. EXP-002 360회는 11.16만 원 이하. 사전 감사 검수자 219.3만 원. 합계 230.46만 원은 기본 시나리오 필요 자금 8.28억 원의 0.28%, 월 고정비의 15% [계산]. 실험 장치는 구현을 마쳤고 테스트 50개가 통과한다 [확인] | 중단 임계값을 실험 전에 적고, 결과가 나쁘면 실제로 접는다. M5 50% 기준은 이미 확정돼 있다 [확인] | 실제 서류 표본을 구하는 데 수개월이 걸려 검증 비용이 커지는 경우. 실험을 계속 미루는 경우 |
| 2. 측정 결과 자체가 자산이다(연구·과제 가치) | 2025~2026년 아랍어 이름 로마자 표기 벤치마크를 찾지 못했다 [문헌○]. "모호할 수 있다"는 지시의 효과를 아랍어 이름에서 잰 연구도 없다 [확인, 긍정 근거 조사]. 이름은 36.7~55.9%, 문장은 CER 2.0%라는 간격이 측정할 가치를 보여 준다. PROJECT_PLAN 7절은 이 문서들이 과제 보고서에 들어간다고 적는다 [확인] | EXP-001·002를 사전 등록대로 실행한다. 합성 문서 결과를 실제 서류의 포착률로 쓰지 않는다 | 같은 측정을 한 공개 연구가 먼저 나오면 새로움은 줄어든다. 과제 가치는 남는다 |
| 3. 빈 틈새에 규정 순풍이 분다 | 직접 경쟁 0곳, 인접 43곳 [문헌○]. Qiwa 계약 기준 사우디화율(2026-04-15), 상호법(2025-04-03), 민사거래법 소급, 영문 이름 수정 전자 서비스(2026-07·09). RHQ 517→660→700곳 이상 [문헌○·요약] | 빈 이유가 수요 부재가 아니어야 한다. 인터뷰에서 아랍어 원문 문서를 매달 받는다는 답이 나와야 한다(사업성 검토 다음 순서 1단계) | 인터뷰 3곳 모두 아랍어 원문을 거의 다루지 않는 경우. Arabic.AI–HUMAIN의 "check" 에이전트나 베링랩이 이름 검증을 넣는 경우. 범용 LLM이 불확실 고유명사 표시를 기본 동작으로 넣는 경우 |
| 4. 업계의 가치가 검증 계층으로 옮겨 간다(단, 부품으로) | Straker→Arbitr "Agents prepare; humans approve what ships". RELX Legal 기초 성장 10%(고정 구독). RWS 사람 서비스 비중 "higher than anticipated". UAE Bayan도 면허 번역사 검증 유지 [문헌○] | 단독 제품이 아니라 번역관리시스템·법률 AI·번역사의 ISO 17100 검토 공정 안에 API나 OEM 부품으로 들어간다 [가설] | Straker Verify처럼 반기 증분 NZ$0.2m에 그친 뒤 통합되는 경우. 제휴처 후보(Arabic.AI Cleverso, 이름 매칭 벤더, LSP)가 관심을 보이지 않는 경우 |
| 5. 가격 기준을 바꾸면 숫자가 돈다(바우처·한국어 출력) | 바우처 정가에서 장당 공헌 14,310원, 손익분기 56곳. 바우처 + 중동 수출기업 1%면 5년 누적 +3.77억 원, NPV −0.23억 원 [계산] | 도구가 "통·번역을 목적으로 하는 서비스"로 인정된다([공고, S95](https://www.motir.go.kr/attach/down/aa4abe331409819421ff269b271f06a6/1f4394efb1288cd7006bff8e374a4410/778bdbf5db9ced7c8fd52756c00bf0cd)). 아랍어 원문을 매달 받는 중소기업이 140곳 있다. 검수자를 시급 약 1.6만 원에 구한다 | 인정이 거부되는 경우. 긴급바우처는 통번역을 의무 사용처에서 뺐고, 충북 사업은 AI 단순 번역을 정산하지 않는다 [문헌○, [S104](https://grant-documents.thevc.kr/291737_%EB%B6%99%EC%9E%84.+2026+%EC%88%98%EC%B6%9C%EA%B8%B0%EC%97%85+%EC%99%B8%EA%B5%AD%EC%96%B4+%ED%86%B5_%EB%B2%88%EC%97%AD+%EC%A7%80%EC%9B%90+%EC%82%AC%EC%97%85+%EB%AA%A8%EC%A7%91_%ED%86%B5%EB%B2%88%EC%97%AD+%EA%B8%B0%EC%97%85+%EB%AA%A8%EC%A7%91+%EA%B3%B5%EA%B3%A0%EB%AC%B8.pdf)]. 관찰된 구매가 계속 연 5건 안팎인 경우. 검수자 시급이 $35면 이 시나리오도 −2.55억 원이 된다 |

반대 증거는 이 표의 3~5번 이유에 몰려 있다. 이 도구 형태에 돈을 낸다는 직접 증거가 없다. 가장 가까운 상장사 사례(Straker Verify)는 채택이 "slower than anticipated"였고 ([S100](https://bulletin.webull.com/qbd/announcement/20251126/499501031/83d2290439c0e307fd0491ee4e85d7b0.pdf)) [확인], 단독 제품은 플랫폼에 흡수됐다. 한국 쪽 설문·기사·세미나 어디에도 언어는 상위 애로로 나오지 않는다. 무료 대체재 위험도 실재한다. GPT-4.1은 모호한 문장을 한 가지로 읽는 경향이 있었지만, 지시문에서 모호성 가능성을 언급하자 "improved quickly"했다 ([Tamas, S101](https://aclanthology.org/2026.neollm-1.7/)) [확인]. 기성 LLM이 전용 모음 복원 모델보다 낫다는 결과도 있다 ([S102](https://aclanthology.org/2026.lrec-1.40/)) [문헌○]. 사용자가 "이름 후보를 나열하라"고 쓰기만 해도 기능의 상당 부분을 흉내 낼 수 있다는 뜻이다. Nimdzi는 고객이 AI 물량을 쓸모 있게 만드는 데 필요한 사람의 감독에 "refuse to pay"한다고 기록했다 ([S01](https://www.nimdzi.com/nimdzi-100-2026/)) [확인]. 이카마 이름 수정은 무료에 몇 분이면 끝난다. 가장 그럴듯한 진입자(Arabic.AI–HUMAIN)는 사우디 기업 고객에게 대량 배포할 돈과 채널을 이미 가졌다. 이 증거들은 3~5번 이유를 반증할 후보이고, 1~2번 이유는 건드리지 않는다.

그래서 정직한 정리는 이렇다. 이 프로젝트를 지금 하는 비즈니스적 이유는 "이 사업이 돈을 번다"가 아니다. "돈을 벌지 판정하는 비용이 8.28억 원짜리 결정의 0.28%"라는 것이고, 그 판정 과정이 연구·과제 결과물로도 남는다는 것이다. 사업 쪽 이유(3~5번)는 가설이다. 가설을 가르는 순서도 비용 순으로 정해진다. EXP-001(무료)이 이름에서 분석기 후보가 나오는지를 보여 준다. 인터뷰와 바우처 요건 확인(거의 무료)이 수요와 가격 기준을 정한다. EXP-002(약 11만 원)가 "지시만으로 충분한가", 곧 무료 대체재 위험을 잰다. 검수자 시급 확인이 단위 경제의 부호를 정한다.

## 결론

이번 조사로 사업 판단의 병목이 옮겨 갔다. 이전 검토에서는 "가격이 낮다"가 문제였다. 이제는 검수자 원가와 판매 경로가 먼저다. 기존 모델은 검수자를 사우디 번역 단어 단가에서 거꾸로 환산한 시급 1.6만 원으로 두었는데, 날짜 없는 ProZ 프로필 몇 곳에서 본 아랍어-영어 프리랜서 시급(35~45달러)은 그 3~4배다 [요약, 근거 약함]. 그 시급이면 사우디 기준 가격(장당 4,873원)에서는 장마다 적자다. 사우디·이집트 현지 검수자가 더 싸게 구해질 수도 있으므로, 이것은 확인할 위험이지 확인된 사실이 아니다. 사우디 기준 가격이 살아남으려면 검수 시간을 장당 6분보다 크게 줄이거나, 사람 검수를 기본 가격에서 떼어 Arbitr처럼 별도 과금해야 한다. 그러니 "장당 검수 시간"은 사전 감사에서 잴 여러 값 가운데 하나가 아니라, 사업의 부호를 정하는 값이 됐다. 수요 쪽에서는 바우처 경로가 유일한 흑자 조합이다. 그런데 관찰된 사우디 대상 통번역 바우처 구매가 연 5건 안팎이라는 사실이 그 시나리오의 가장 약한 고리를 드러냈다.

경쟁 지형이 주는 함의는 이 도구가 회사보다 기능에 가깝다는 것이다. 같은 일을 하는 제품이 없다는 사실, 검증만 떼어 판 상장사 제품이 팔리지 않았다는 사실, 신뢰를 파는 법률 플랫폼이 구독료로 자란다는 사실을 함께 놓으면 그렇게 읽힌다. 가장 현실적인 상업 경로는 단독 SaaS가 아니다. 아랍어 이름 모호성을 재고 표시하는 측정된 부품을 번역관리시스템, 걸프 법률 AI, 한국 번역사의 검토 공정에 넣는 것이다. 그 부품의 값어치는 "모호 구간을 몇 % 잡는가"라는 공개 측정값에서 나온다. 그 측정값을 만드는 데 드는 돈이 230만 원이다.

## 부록 A. 기존 문서와 어긋나거나 새로 바뀐 점

| 항목 | 기존 문서 | 이번 노트·계산 | 영향 |
| --- | --- | --- | --- |
| 검수자 시급 | 시급 16,248원(41.7리얄, 사우디 번역 단어 단가 × 시간당 250단어) [가정] | ProZ 아랍어-영어 프리랜서 $35~45(51,170~65,790원) [요약]. 평가셋 작업자 가정 $30 | 사우디 기준 가격에서 장당 공헌 −554~−2,016원. 손익분기 정의 불가 |
| 장당 API 토큰 | 장당 입력 3만·출력 1.5만 토큰(310원) | 공급 노트는 "묶음당" 입력 5만·출력 5천 토큰(약 219원)을 썼다 | 단위가 장과 묶음으로 다르다. 이 보고서는 기존 310원을 유지했다. 어느 쪽이든 원가의 16% 이하다 |
| 사용 모델 | 사업성 검토는 Claude Sonnet 5.5로 계산 | PROJECT_PLAN의 설정 모델은 OpenAI `gpt-6.1-sol`이고 단가는 같은 $2/$10 [문헌○] | 숫자는 바뀌지 않는다 |
| 사우디 신규 법인 연도별 수 | 수출입은행 2023년 13곳, KOTRA 2026년판 12곳 | KOTRA 2025년판 2023년 12곳, 1968~2023 누적 285곳 | 285 + 61 = 346곳으로 수출입은행 누적 343곳과 3곳 차이. 343·251곳을 일부 뒷받침한다 |
| RHQ 수 | 700곳 이상(2026-01, 장관 발언) | 517곳(2024 상반기, KOTRA), 660곳(2025-09, 요약), 676곳(2025년 말, 출처 미상) | 같은 증가 추세. 공식 원자료(MISA Monitor)는 여전히 미확인 |
| 베링랩 아랍어 지원 | 2024-07 보도 기준 없음, 현재 [미확인] | 2026-10-20 사이트 문구에 아랍어 없음 [문헌○] | 국내 공백을 한 번 더 확인 |
| KOSA 인건비 | 2025년 적용 6,943,457원 | 2026년 적용분이 4.7% 올랐다는 제3자 글만 있음 [요약] | 반영하면 고정비가 조금 오른다. 공식 PDF 확인 전에는 바꾸지 않았다 |
| 사우디 TAM의 현지 문서량 | 외국인 등기 38,640곳 × 월 5장 [가정] | 그 물량을 사람이 번역하면 연 565억 원으로, Statista 사우디 번역 시장 424억 원을 넘는다 | 월 5장 가정이나 Statista 정의 가운데 하나가 틀렸다. 현지 TAM 112.98억 원은 상한으로만 쓴다 |
| 시장조사기관 추정치 | Nimdzi 중동 11억 달러만 사용 | GCC·사우디 번역 시장 추정이 76배까지 어긋남(Astute, Statista). Ken Research는 같은 회사 안에서 사우디 리걸테크를 2억·3.8억 달러로 다르게 적음 | 하향식 TAM의 근거로 쓰지 않는다 |
| Arabic.AI 첫 제품 공개 시점 | — | Wamda(2026-09-01)는 첫 제품이 "LEAP 2026"에서 공개된다고 썼다. 노트는 날짜가 맞지 않을 수 있다고 적었다 | 진입 시점은 [미확인]으로 둔다 |
| 노트의 환율 | 1유로 약 1,600원, 1파운드 약 1,868원은 프로젝트 값이 아님 | 이 보고서는 TAUS 한 곳만 1유로 1,600원으로 바꾸고 [가정]으로 표시했다. 파운드와 NZ달러는 바꾸지 않았다 | — |

## 부록 B. 출처

본문에 링크로 붙였다. 새로 인용한 자료 71건은 [sources.csv](../sources.csv)의 S110~S180에 추가했다. "확인" 칸은 기존 정의를 따랐다. 조사 노트의 에이전트가 원문을 연 자료는 "대리", 검색 요약이나 2차 인용으로만 본 자료는 "요약"이다. 이 보고서를 쓰면서 원문을 다시 대조한 새 자료는 없으므로 "직접"은 없다. 기존 S01~S107은 고치지 않았다.
