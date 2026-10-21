# 공급 측 조사: 요구 수준과 구축·운영 비용 (Tashkeel Check)

조사일 2026-10-20. 웹 검색 30회, 원문 열람(fetch) 약 35회.

- **환율:** 1 USD = 1,462원, 1 SAR ≈ 390원, 1 EUR ≈ 1,600원. 환율표에 GBP가 없어서 GBP 수치는 원화로 바꾸지 않고 원래 통화로만 적었다. 모델에 넣으려면 GBP 환율을 따로 정해야 한다.
- **표기:** **직접**은 원문 페이지를 열어서 확인했다는 뜻이다. 열람 도구가 페이지를 요약해서 돌려주므로, 숫자를 다시 쓸 때는 원문을 한 번 더 확인한다. **요약**은 검색 스니펫이나 2차 요약만 봤다는 뜻이다. **추정**은 내 계산이고 산식을 함께 적었다. **[확인]**은 이 저장소 환경에서 직접 조회한 결과다.
- 이미 알고 있던 값(KOSA 응용SW개발자 6,943,457원, Sonnet 5.5 $2/$10, 사우디 공인 번역 0.167 SAR/단어, 한국 아→한 230원/단어, Bondok 2025, Tamas 2026)은 다시 찾지 않았다. 필요한 곳에서만 인용했다.

---

## 1. 고객과 표준·규제가 요구하는 수준은? (ISO, SOC 2, PDPL, NCA, 한국 개인정보보호법, 사우디 공인 번역 자격)

### Takeaway
이 도구에 직접 적용되는 강제 인증은 찾지 못했다. 실제로 걸리는 요구는 두 가지다. 첫째, 고객이 보낸 신분증·상업등기 같은 개인정보를 LLM API로 국외 이전할 때 지켜야 하는 절차다(한국 개인정보보호법 제28조의8, 사우디 PDPL 이전 규정의 SCC와 위험평가). 둘째, 엔터프라이즈 구매자가 흔히 묻는 ISO 27001·SOC 2 같은 보안 증빙이다. 사우디 공인 번역은 상무부(MOC) 면허를 받은 번역사나 사무소의 행위여서 소프트웨어가 대신할 수 없다. 데이터를 사우디 안에 두라는 의무는 정부기관과 핵심기반시설(CNI) 쪽에서만 확인됐다.

### Cited Findings

**사우디 PDPL (국외 이전)**
- SDAIA의 국외 이전 규정(Transfer Regulations)은 2024년 8월에 나왔다. 위험평가 가이드라인은 2025년 2월에 나왔다. 적정성(adequacy) 국가 목록은 2025-11 기준 아직 공개되지 않았고, 기사는 그동안 GDPR 적정성 결정을 참고하라고 권한다 — [King & Spalding, 2025-11-17, 직접](https://www.kslaw.com/insights/articles/international-personal-data-transfers-under-saudi-arabias-data-protection-law)
  - 원문 인용: "Given that SDAIA has not disclosed the list of approved jurisdictions"
- 적정성이 인정되지 않은 국가로 보낼 때 쓸 수 있는 보호조치는 세 가지다. Saudi SCC(표준계약조항), BCR(그룹 내부용), 인증서(Certificate of Accreditation)다. 보호조치에 기대어 이전할 때는 이전 전에 위험평가를 해야 한다. 외부 벤더로 보내는 경우에는 BCR을 쓸 수 없다 — 같은 출처
  - 원문 인용: "BCRs are not an available safeguard when an organization anticipates the transfer", "must also undertake a risk assessment prior to the transfer"
- "데이터 주체에게 직접 서비스나 혜택을 제공하는 경우"라는 예외도 있다. 이 예외는 인증서가 있어야 하고 민감정보는 보낼 수 없다 — 같은 출처
- PDPL은 2023-09-14에 시행됐고 유예기간은 2024-09-14에 끝났다. 국가 등록부 등록 의무는 공공기관, 개인정보 처리가 주업인 컨트롤러, 고위험 민감정보를 다루는 컨트롤러에 있다. 민감정보를 핵심 업무로 처리하면 DPO를 둬야 한다 — [Clyde & Co, 2024-09-10, 직접](https://www.clydeco.com/en/insights/2024/09/saudi-arabia-s-personal-data-protection-law-become)
- 제재: 민감정보를 해칠 의도로 공개하면 "imprisonment for up to two years and/or a fine up to SAR 3 million"이다(징역 최대 2년 또는 벌금 최대 300만 리얄, 약 11.7억 원). 그 밖의 위반은 "a fine not exceeding SAR 5 million"이다(최대 500만 리얄, 약 19.5억 원). 유출을 알게 되면 72시간 안에 SDAIA에 신고해야 한다. 이 페이지에는 데이터 현지화 의무가 명시돼 있지 않다 — [DLA Piper Data Protection Laws (Saudi Arabia), 확인일 2026-10-20, 직접](https://www.dlapiperdataprotection.com/?t=law&c=SA)

**사우디 NCA ECC/CCC와 데이터 상주**
- ECC는 정부기관과 그 계열, 그리고 핵심기반시설(CNI)을 소유·운영·호스팅하는 민간기업에 의무다. ECC-2:2024의 통제항목 4-1-3-2는 원격 접근으로 운영하는 보안관제센터를 사우디 안에 두라고 요구한다 — [Secure.com, 2026-07-28, 직접](https://www.secure.com/blog/compliance/ecc-data-residency)
  - 원문 인용: "Cybersecurity managed service centers for monitoring and operations that use remote access … must be fully located inside the Kingdom of Saudi Arabia"
- ECC-2:2024는 ECC 2018에 있던 "데이터를 사우디 안에서 호스팅·저장하라"는 의무를 삭제했다. 다만 다른 규정 때문에 현지화가 여전히 필요할 수 있다. 예를 들어 CST(통신우주기술위원회) 클라우드 규정은 정부기관 데이터를 CST에 등록된 사업자에게 맡기라고 하고, 이는 보통 사우디 내 데이터센터를 뜻한다 — [Bird & Bird, 2024, 요약(원문 403)](https://cm.twobirds.com/en/insights/2024/ksa-movement-in-saudi-arabias-cybersecurity-regulatory-regime)
- CCC-2:2024(클라우드 통제)는 정부기관과 CNI 민간 운영자에게 의무다 — [SecurityWall, 요약](https://securitywall.co/blog/ccc-cloud-cybersecurity-controls-saudi-arabia)

**한국 개인정보보호법 (국외 이전)**
- 국외 이전은 동의가 원칙이다. 다만 정보주체와의 계약 이행에 필요한 처리위탁·보관을 처리방침에 공개하거나 이메일 등으로 알린 경우, 이전받는 자가 ISMS-P 같은 인증을 받은 경우, 개인정보보호위원회가 적정성을 인정한 국가인 경우에는 동의가 필요 없다. EU는 2025-09-03에 적정성을 인정받았다. 과징금 상한은 전체 매출액의 3%이고, 특정한 경우(3년 안의 반복된 고의·중과실, 1천만 명 이상 피해, 시정명령 불이행)에는 10%까지 올라간다. 이 개정은 2026-09-11부터 시행된다. 유출 통지는 72시간 안에 해야 하고, 모든 처리자는 CPO를 지정해야 한다 — [DLA Piper (Korea), 확인일 2026-10-20, 직접](https://www.dlapiperdataprotection.com/?t=law&c=KR)
- 해외 클라우드(AWS 등)에 보관하는 것도 국외 이전에 해당한다. 제28조의8 제1항 제3호 요건(계약 이행 + 처리방침 공개)을 갖추면 동의가 필요 없다. 처리방침에 공개할 항목은 다섯 가지다. ① 이전 항목 ② 국가·시기·방법 ③ 이전받는 자의 명칭과 연락처 ④ 이용 목적과 보유 기간 ⑤ 거부 방법·절차와 거부의 효과 — [nepla 일문일답, 2024-08-14, 직접](https://www.nepla.ai/wiki/it-정보-방송통신/개인정보-위치정보-신용정보/-일문일답-해외-클라우드-aws-등-에서-개인정보를-보관-처리할-때-정보주체의-동의를-받아야-하는가-54gnvzpe81pr)

**사우디 공인 번역 자격**
- "translators and translation bureaus must be licensed by MOC" — [US ITA Country Commercial Guide, 2026-05-11, 직접](https://www.trade.gov/index.php/country-commercial-guides/saudi-arabia-licensing-requirements-professional-services)
- 샤리아 법원 소송절차법 제23조에 따르면 외국어 문서는 허가받은 사무소의 공인 번역을 함께 내야 한다 — 기존 조사 S60(대리), `docs/business/market/sources.csv`
- 문학·출판·번역위원회(LPTC) 규정은 번역의 모든 형태(서면·구두·시청각)를 위원회가 관장하는 분야로 정한다. 다만 번역사무소 면허나 번역사 인증 절차의 세부 내용은 찾지 못했다 — [qanoniah (위원회 조직규정), 요약](https://qanoniah.com/File/dJG8m4pa1LVJG9QLgr2bq5W60-تنظيم-هيئة-الأدب-والنشر-والترجمة)

**ISO 17100 / ISO 18587**
- iso.org 원문이 403으로 막혀서 적용 범위 조문을 확인하지 못했다. ISO 17100은 번역 업계 전용 표준으로 소개된다 — [LinguaLinx, 요약](https://lingualinx.com/blog/how-certified-translation-services-can-save-you-thousands-of-dollars)
- ISO 17100·18587 인증을 받은 기업의 사례 연구가 있다(살라망카대 학위논문, 기간 분석 포함). 본문 수치는 보지 못했다 — [GREDOS USAL, 요약](https://gredos.usal.es/handle/10366/163499)
- 전직 품질 감사인이라고 밝힌 ProZ 사용자는 "인증받은" 업체 상당수가 실제로는 표준을 따르지 않는다고 주장했다(일화) — [ProZ 포럼, 요약](https://www2.proz.com/forum/business_issues/365179-iso_9001_and_17100_certifications.html)

### Inferences
- 고객 쪽 흐름을 그려 보면 이렇다. 한국 중소기업(컨트롤러)이 문서를 올리면 Tashkeel Check(수탁자)를 거쳐 미국·글로벌 LLM API로 간다. 이것은 한국법상 국외 처리위탁에 해당한다. 그래서 파일럿 단계에서도 처리방침의 다섯 개 공개 항목과 위탁계약은 갖춰야 한다. 인증은 의무가 아니다.
- 사우디 법인(외국계)이 고객이면 Saudi SCC와 이전 전 위험평가가 사실상 기본 요건이다. 적정성 목록이 없으므로 한국이나 미국을 적정국으로 기대할 수 없다. 민감정보(사우디 PDPL에서 신분증 번호가 민감정보에 해당하는지는 미확인)를 보내면 요건이 더 무거워진다.
- 정부기관이나 CNI 고객이 아니면 사우디 내 호스팅이 법적 의무라는 근거는 찾지 못했다. 그래도 엔터프라이즈 조달에서 "사우디 리전"을 요구할 가능성은 있다. 이 부분은 [가설]이다.
- ISO 17100과 18587은 번역 서비스 제공자(TSP)의 공정 표준으로 알려져 있다(원문 미확인). 이 도구 자체가 인증 대상이 되기는 어렵다. 오히려 ISO 17100 공정의 "검토(revision)" 단계를 돕는 도구로 LSP에 파는 길이 있다. 이 부분은 [제안]이다.
- 공인 번역은 면허를 받은 사람이나 사무소의 서명·날인 행위다. 소프트웨어가 대신할 수 있다는 근거는 찾지 못했다. 이 제품은 "공인 번역에 맡기기 전 사전 점검" 위치에 머물러야 한다.

### Gaps
- ISO 17100(재검토자 요건, 원시 MT 제외 문구)과 ISO 18587(원시 MT 출력 적용 제외)의 원문 조문은 iso.org 403 때문에 확인하지 못했다.
- 엔터프라이즈·법무 구매자가 보안 질의서에서 실제로 무엇을 요구하는지(ISO 27001, SOC 2, 사우디 리전 여부)를 보여 주는 1차 자료는 찾지 못했다.
- 한국 기업이 사우디 측 인물(사우디 파트너의 신분증 등)의 개인정보를 처리할 때 PDPL이 역외 적용되는지는 미확인이다.
- 사우디 공인 번역사·사무소 면허의 세부 요건과 비용, 기계번역을 쓸 수 있는지에 대한 명시 규정을 찾지 못했다.
- NCA ECC-2:2024와 CCC-2:2024 원문(nca.gov.sa)은 열지 못했다. 2차 자료만 봤다.

---

## 2. 정확도와 품질 기준: 벤더는 무엇을 내세우고, 최신 연구 수준은 어디인가?

### Takeaway
QE·검증 벤더는 정확도나 재현율 수치를 공개하지 않는다. ModelFront 홈페이지에는 고객 사례(5배 가속) 말고는 숫자가 없다. 연구 쪽에서는 문맥이 있는 문장의 발음 부호 복원을 최신 LLM이 CER 약 2% 수준으로 해낸다. 반면 고유명사는 GPT-4o가 아랍어만 보고 36.7~55.9%, 영어를 함께 주면 73.0%에 그친다(Bondok 2025, 기지). 아랍어 이름을 로마자로 옮기는 작업의 2025~2026 벤치마크는 찾지 못했다.

### Cited Findings

**벤더가 내세우는 것**
- ModelFront 홈페이지에는 정확도·정밀도·자동 승인 비율 같은 수치가 없다. 정성적 문구와 고객 사례만 있다.
  - 원문 인용: "ModelFront takes responsibility for keeping human quality, and provides transparent monitoring to prove it.", "FARFETCH accelerates luxury fashion catalog translation by 5x."
  - 고객 명시: Booking.com, Questel, FARFETCH
  - [ModelFront, 확인일 2026-10-20, 직접](https://www.modelfront.com/)
- Nimdzi는 ModelFront를 이렇게 설명한다. "It works by automatically confirming machine translations that humans would confirm unedited". MTQE는 2019년, APE는 2024년으로 적혀 있다 — [Nimdzi Language Technology Radar, 직접](https://www.nimdzi.com/language-technology-radar/modelfront/)
- Straker의 단독 검증 제품 Verify는 채택이 "slower than anticipated"였다 — 기존 조사 S100(직접). straker.ai/verify는 이제 arbitr.ai/verify로 리디렉트되고, 그 주소는 404를 돌려준다(2026-10-20 관찰).

**최신 연구 수준: 문장 단위 발음 부호 복원**
- Mohamed & Mubarak의 EMNLP 2025 논문(2025-11-09)은 BiLSTM 모델로 WikiNews-2014에서 WER 3.12%, WikiNews-2024에서 WER 2.70%를 보고했다 — [HBKU 연구 포털, 직접](https://elmi.hbku.edu.qa/en/publications/advancing-arabic-diacritization-improved-datasets-benchmarking-an/)
- Toyin·Magdy·Aldarmaki의 LREC 2026 논문은 중의성 중심 데이터셋 MultiDiac으로 아랍어 CER을 쟀다. 결과는 아래와 같다 — [ACL Anthology 2026.lrec-1.40, PDF 표 4, 직접](https://aclanthology.org/2026.lrec-1.40.pdf)

  | 구분 | 모델 | 아랍어 CER (%) | 비고 |
  | --- | --- | --- | --- |
  | 대형 LLM | ChatGPT4o | 2.0 | |
  | 대형 LLM | DeepSeek-R1 | 2.6 | |
  | 대형 LLM | IBM granite | 3.2 | |
  | 대형 LLM | Command-a | 5.7 | |
  | 대형 LLM | Claude3.5 | 5.8 | |
  | 전용 모델 | CATT | 10.3 | |
  | 전용 모델 | Shakkelha | 11.5 | |
  | 아랍어 특화 소형 | Fanar-9B | 7.5 | |
  | 아랍어 특화 소형 | Allam | 20.8 | 표에는 "Allam-9B", 본문에는 "Allam-7B"로 적혀 있다 |
  | 아랍어 특화 소형 | Jais-13B | 61.9 | 환각 WER 75.5 |

  - 원문 인용: "many off-the-shelf LLMs outperform specialized diacritization models for both Arabic and Yoruba"
- NADI 2025 Subtask 3(방언 음성의 발음 부호 복원)에서 최고 시스템은 WER 55 / CER 13이었다 — [arXiv 2509.02038, 2025-09, 직접](https://arxiv.org/abs/2509.02038v2)
- KSAA-2026 Shared Task 2(음성 받아쓰기 발음 부호)에서 2위 팀은 DER 7.04, WER 24.39였다. 1위 수치는 찾지 못했다 — 검색 요약(원문 미열람)

**고유명사와 이름 로마자 표기**
- Bondok 등(2025)은 기지 값이라 다시 찾지 않았다.
- 2025년에 LLM의 아랍어 이름 로마자 정확도를 따로 잰 벤치마크는 찾지 못했다. 가장 가까운 것은 2026년 마그레브 이름 음역 벤치마크 DziriNames다 — [Hugging Face, 요약](https://huggingface.co/yacinebenak/DziriNames)

**작업자에게 요구하는 품질 기준(참고)**
- 아랍어 태깅 프로젝트 공고는 골드 샘플과 97% 이상 일치를 요구했다 — [Freelancer, 요약](https://www.freelancer.com/projects/translation/arabic-data-tagging-annotation)

### Inferences
- 문장은 최신 LLM이 거의 풀고 이름은 못 푼다. 이 대비는 PROJECT_PLAN의 [가설]을 외부 수치로 뒷받침한다. 다만 LREC 2026이 시험한 LLM은 2024년 세대(GPT-4o, Claude3.5)다. 2026년 모델의 이름 성능은 측정되지 않았다.
- 아랍어 특화 소형 모델(ALLaM, Jais-13B)은 발음 부호 복원에서 범용 대형 모델보다 크게 떨어졌다. 사우디 데이터 상주를 이유로 ALLaM이나 Jais를 고르면 정확도를 잃을 위험이 있다. 이 부분은 [가설]이며, 2026년 버전으로 다시 재야 한다.
- 고객이 요구하는 수준은 "정확도 몇 %"가 아니다. "신분증 표기와 정확히 일치하는가"라는 이진 기준이다(ADGM, SAMA 회람; 기존 조사 S77). 그래서 이 제품의 품질 지표는 모호 구간의 재현율과 근거 없는 확정 비율로 정의하는 편이 맞다. 벤더가 이런 지표를 공개하지 않으므로, 비교 기준은 우리가 직접 만들어야 한다.

### Gaps
- Unbabel QE, Phrase QPS, Straker Verify 등 QE 벤더의 정확도·재현율 공개 수치는 찾지 못했다(ModelFront는 숫자가 없음을 확인했다).
- 아랍어 → 라틴 문자 이름 음역의 2025~2026 공식 shared task와 리더보드를 찾지 못했다.
- KSAA-2026 1위 수치와 원문은 보지 못했다.

---

## 3. 인증·컴플라이언스 비용과 기간은? (ISO 27001, SOC 2, ISMS-P, 법률 검토, 배상책임보험)

### Takeaway
인원 25명 이하 스타트업 기준으로 정리하면 이렇다. SOC 2 Type 2 첫해 총액은 약 $28,000(약 4,094만 원)이고 6~12개월 걸린다. ISO 27001 심사비는 £6,250~8,750이고, 컨설팅이 £5,000~40,000 별도이며 약 6개월 걸린다. ISMS-P 간편인증 수수료는 600~1,100만 원이다(구축비 별도). 번역가 배상책임보험은 연 £100~ / $410~ 수준이다. 수치는 대부분 컴플라이언스 벤더나 컨설팅사 자료라서 견적의 범위로만 써야 한다.

### Cited Findings

**ISO 27001**
- 인원별 심사 일수와 비용(일당 £1,250 가정)은 다음과 같다. 1~10명은 5일 £6,250, 11~15명은 6일 £7,500, 16~25명은 7일 £8,750, 26~45명은 8.5일 £11,250이다. 표 값과 일당 곱이 맞지 않는 행이 있다(예: 8.5일 × £1,250 = £10,625). 사후 심사는 1·2년차에 최초 비용의 약 33%다. 컨설턴트는 £5,000~40,000(6~12개월), 일당 £800~1,500이다. 보통 약 6개월 걸린다 — [High Table, 최종 갱신 2026-10-06, 직접](https://hightable.io/briefing-on-iso-27001-certification-costs/)
- 소규모 기업의 Stage 1·2 심사비는 약 $14,000 + $16,000이다 — [Konfirmity, 요약](https://www.konfirmity.com/blog/iso-27001-audit-cost)
- 소기업 총비용은 $25,000~50,000이다 — 검색 스니펫, 요약(출처 페이지 불명확)

**SOC 2** — [Drata, 2026-03-25, 직접](https://drata.com/learn/soc-2/cost)
- Type 1 심사비(중소): "$7,500 to $15,000" (1,097만~2,193만 원). 1~3개월 걸린다.
- Type 2 심사비(중소): "$12,000 to $20,000" (1,754만~2,924만 원). 관찰 기간은 3~12개월이고 전체로는 6~12개월 걸린다.
- 갭 평가 "$5,000 - $25,000", 침투 테스트 "$5,000 - $15,000"
- 첫해 총액: 25명 스타트업 약 $28,000(4,094만 원), 100명 약 $75,000
- 플랫폼(Vanta·Drata) 연 $8,000~20,000(100명 미만) — [getagency 등, 요약](https://blog.getagency.com/articles/soc-2-audit-cost-for-startups). 벤더 계열 자료라 편향 가능성이 있다.

**ISMS·ISMS-P (한국)** — [보안뉴스, 2024-07-23, 직접](http://www.boannews.com/news/articleView.html?idxno=131534)
- 2024-07-24부터 중소기업 간편인증이 시행됐다. 대상은 ICT서비스 매출 300억 원 미만 중소기업, 또는 300억 원 이상 중기업 중 주요 정보통신설비가 없는 기업이다.
- 수수료:

  | 구분 | 기존 | 간편인증 | 인하 폭 |
  | --- | --- | --- | --- |
  | ISMS | 800~1,400만 원 | 400~700만 원 | 50% |
  | ISMS-P | 1,000~1,800만 원 | 600~1,100만 원 | 40% |

- 인증기준은 ISMS-P 기준 62~65개로 줄었다(기존 101개).
- ISMS-P 인증을 받은 수신자에게 보내는 국외 이전은 동의 예외에 해당한다 — DLA Piper(KR), 위와 같음

**법률 검토**
- 사우디 변호사 시급은 부티크 400~900리얄(15.6만~35.1만 원), 대형 현지 로펌 800~1,800리얄(31.2만~70.2만 원), 국제 로펌 1,500~3,500리얄(58.5만~136.5만 원)이다. 출처 스스로 추정치라고 밝혔다 — 기존 조사 S99, [Global Law Experts, 2026-08-18](https://globallawexperts.com/lawyer-fees-saudi-arabia/)
- 법무부는 해외 진출 중소·중견기업에 국제 법무 자문을 무료로 지원한다 — 기존 조사 S107(대리)

**배상책임보험**
- 영국 번역가 PI(보장 £1,000,000) 예시 견적은 프리랜서 £99.97/년, 소규모 Ltd £111.43/년이다. 2026년 3~6월에 산출됐다 — [Simply Business, 직접](https://www.simplybusiness.co.uk/business-insurance/translators-insurance/)
- ATA E&O 프로그램은 최저 연 $410(59.9만 원), 보장 한도 $250,000~2,000,000이다. 이 수치는 2021년 자료다 — [ATA Chronicle 2021, 요약](https://nxtbook.com/nxtbooks/chronicle/20210102/index.php?startid=40). 가입하려면 ATA 회원이면서 미국 거주자여야 한다 — [Alliant FAQ, 직접](https://alliant.com/risk-management/risk-solutions/customized-solutions/ata-professional-liability-insurance/faqs)
- 네덜란드 NGTV 회원 보험은 연 €405(64.8만 원)에 건당 €25만을 보장한다 — 기존 조사 S106(대리)

### Inferences
- 파일럿 단계에서는 인증이 필요 없다. 처리방침, 위탁계약, 국외 이전 공개 정도면 된다. 엔터프라이즈 단계에서는 SOC 2 Type 2와 ISO 27001 중 하나 이상이 사실상 입장권일 가능성이 높다. 이 부분은 [가설]이다. 둘 다 6~12개월이 걸리므로, 엔터프라이즈 판매 시점은 결정한 날로부터 최소 6~12개월 뒤가 된다.
- 한국 고객만 보면 ISMS-P 간편인증(수수료 600~1,100만 원)이 SOC 2보다 싸다. ISMS-P는 국외 이전 동의 예외 사유로도 쓸 수 있다. 다만 사우디 외국계 기업에게 ISMS-P가 통하는지는 근거가 없다.
- 번역가 PI 보험료는 싸다. 하지만 이 제품은 SaaS라서 기술 E&O·사이버 보험이 맞는 상품이다. 그 보험료는 찾지 못했다.

### Gaps
- 한국 인증기관의 ISO 27001 심사 견적과 KRW 기준 SOC 2 사례를 찾지 못했다.
- ISMS-P 인증 의무 대상 기준(매출·이용자 수)을 이번 조사에서 다시 확인하지 않았다.
- 한국 로펌의 개인정보 처리방침·이용약관·국외 이전 검토 비용(시급이나 패키지)을 찾지 못했다.
- SaaS·AI 기업의 기술 E&O·사이버 보험료를 찾지 못했다.
- ISO 17100 인증 비용은 신뢰할 만한 수치가 없었다. "$300~5,000"(자격 묶음, 블로그 추정)만 봤다.

---

## 4. 인프라 비용은? (LLM API, 아랍어 특화 모델, 사우디 리전)

### Takeaway
상위 범용 모델의 가격은 Anthropic Sonnet 5.5, OpenAI gpt-6-sol, Gemini 3.1 Pro가 모두 입력 $2/1M에 수렴했다(출력 $10~12). 소형 모델은 $0.10~0.75/1M이다. Anthropic과 OpenAI는 지역 처리(데이터 레지던시)에 10% 할증을 붙인다. 공개된 선택지는 미국 등 일부 지역뿐이고 사우디 상주 옵션은 확인되지 않았다. AWS와 Azure의 사우디 리전은 2026년 4분기 개시 예정이다. 이미 있는 GCP 담맘 리전은 Cloud SQL 기준으로 아이오와보다 약 1.6배 비싸다.

### Cited Findings

**범용 LLM API (1M 토큰당, 표준가)**
- Anthropic: 아래 표 — [Claude 가격 문서, 확인일 2026-10-20, 직접(원문 마크다운에서 grep)](https://platform.claude.com/docs/en/about-claude/pricing)

  | 모델 | 입력 | 출력 | 원화 환산 (입력/출력) |
  | --- | --- | --- | --- |
  | Sonnet 5.5 | $2 | $10 | 2,924원 / 14,620원 |
  | Haiku 5.5 (프롬프트 10만 토큰 이하) | $0.10 | $0.50 | 146원 / 731원 |
  | Opus 5.5 | $4 | $20 | 5,848원 / 29,240원 |
  | Fable 5.1 | $10 | $50 | — |

  - 캐시 히트: Sonnet 5.5 $0.10
  - Batch API는 입력·출력 50% 할인
  - 원문 인용: "specifying US-only inference through the `inference_geo` parameter incurs a 1.1x multiplier"
  - 1P에서 확인되는 지역 옵션은 global(기본)과 us뿐이다. Bedrock과 Google Cloud는 지역별 가격을 따로 정한다.
- OpenAI: 아래 표 — [OpenAI API 가격, 확인일 2026-10-20, 직접(요약 도구 경유)](https://developers.openai.com/api/docs/pricing)

  | 모델 | 입력 | 출력 | 원화 환산 (입력/출력) |
  | --- | --- | --- | --- |
  | gpt-6-sol | $2.00 | $10.00 | 2,924원 / 14,620원 |
  | gpt-6.1-sol | $2.00 | $10.00 | 캐시 입력 $0.10 |
  | gpt-6-astra | $10 | $50 | — |
  | gpt-5.4-mini | $0.75 | $4.50 | 1,097원 / 6,579원 |
  | gpt-5.4-nano | $0.20 | $1.25 | 292원 / 1,828원 |

  - Batch는 약 50% 할인
  - 2026-03-05 이후 출시된 모델은 지역 처리 엔드포인트에 10% 할증이 붙는다.
- Google Gemini: 아래 표 — [Gemini API 가격, 최종 갱신 2026-10-19, 직접(요약 도구 경유)](https://ai.google.dev/gemini-api/docs/pricing)

  | 모델 | 입력 | 출력 | 원화 환산 (입력/출력) |
  | --- | --- | --- | --- |
  | 3.1 Pro Preview (20만 토큰 이하) | $2.00 | $12.00 | 2,924원 / 17,544원 |
  | 3.8 Flash | $0.75 | $3.75 | 1,097원 / 5,483원 |
  | 3.1 Flash-Lite | $0.25 | $1.50 | 366원 / 2,193원 |
  | 2.5 Flash-Lite | $0.10 | $0.40 | 146원 / 585원 |

  - Batch 50% 할인
  - 3.8 Flash는 2027-01-01에 입출력 가격이 두 배로 오를 예정이다.

**아랍어 특화 모델**
- ALLaM 7B Instruct (preview)는 IBM에서 입력 $0.22 / 출력 $0.59 per 1M(322원 / 863원)이다. 컨텍스트는 4K다 — [pricepertoken, 갱신 2026-10-19, 직접(집계 사이트)](https://pricepertoken.com/pricing-page/model/ibm-allam-7b-instruct-preview). HUMAIN 공식 가격표는 찾지 못했다. 다른 집계 사이트는 ALLaM 34B를 "Free"로 표시해서 값이 서로 충돌한다 — [lmmarketcap, 요약](https://lmmarketcap.com/pricing-page/model/allam-34b)
- Jais 30B Chat은 Azure AI Foundry에서 입력 $3.20 / 출력 $9.71 per 1M(4,678원 / 14,196원)이다 — [LLM Reference, 요약](https://www.llmreference.com/model/jais-30b/microsoft-foundry). 같은 값을 FutureAGI는 "$3,200/M"으로 표기했다(단위 오류로 보임). 컨텍스트 8,192, 검증일 2026-08-06 — [FutureAGI, 직접](https://futureagi.com/llm-cost-calculator/azure-ai-foundry/jais-30b-chat)

**사우디 국내 클라우드**
- AWS 사우디 리전: "due to launch by December 2026"이다. 투자 규모는 53억 달러 이상이다 — [W.Media, 2026-09-01, 직접](https://w.media/aws-saudi-arabia-cloud-region-set-for-december-2026-launch/). 2024-03 발표 당시 가용영역 3개로 계획됐다 — [검색 요약](https://www.businesswire.com/news/home/20240304438993/en)
- Azure Saudi Arabia East(동부주): "customers will be able to run cloud workloads from its Saudi Arabia East datacenter region from Q4 2026". 가용영역은 3개다. Azure OpenAI·Foundry 제공 여부는 언급이 없다 — [Microsoft, 2026-02, 직접](https://news.microsoft.com/source/emea/2026/02/microsoft-confirms-saudi-arabia-datacenter-region-available-for-customers-to-run-cloud-workloads-from-q4-2026/)
- GCP 담맘(me-central2): Cloud SQL db-standard-2(Enterprise) 월 요금을 비교하면 아래와 같다. 이 페이지에는 날짜가 없다 — [Bytebase dbcost, 직접(제3자 집계)](https://www.bytebase.com/dbcost/cloudsql/instance/db-standard-2.md)

  | 리전 | 월 요금 | 원화 환산 |
  | --- | --- | --- |
  | 담맘 | $158 | 23.1만 원 |
  | 아이오와 | $99 | 14.5만 원 |
  | 서울 | $128 | 18.7만 원 |
  | 도하 | $120 | — |

- Holori 계산기(2026-02)는 담맘을 GCP 평균보다 약 34.6% 비싸다고 보지만, 표 값이 일관되지 않는다 — [Holori, 요약](https://calculator.holori.com/gcp-regions)

### Inferences
- 담맘과 아이오와의 가격 비는 158 / 99 = 1.60배이고, 담맘과 서울의 가격 비는 158 / 128 = 1.23배다. 이것은 관리형 DB 한 항목의 비율이다. 사우디 리전 할증을 1.2~1.6배 범위로 두는 것은 [추정]이다.
- 사우디 안에서 LLM 추론까지 처리하려면 선택지가 셋이다. ① ALLaM 등 현지 모델(가격 미공개, 정확도 위험; 2절 참고) ② 사우디 리전에 오픈 모델 자체 호스팅(GPU 비용 미조사) ③ 하이퍼스케일러 사우디 리전의 관리형 LLM(2026-10 기준 개시 전, 제공 모델 미확인). 지금 1P API로는 사우디 상주가 불가능해 보인다.
- 토큰 단가 자체는 파일럿 경제성에 거의 영향이 없다. 산식은 6절의 추정 표에 있다.

### Gaps
- Oracle Cloud 제다·리야드 리전의 현황과 가격은 조사하지 못했다(검색 예산 소진).
- AWS·Azure 사우디 리전의 가격표와 서비스 목록(Bedrock, Azure OpenAI 포함 여부)은 개시 전이라 확인할 수 없었다.
- HUMAIN의 ALLaM 공식 API 가격, 그리고 GCP 담맘 VM·GPU 공식 가격표는 열지 못했다.
- 이 제품이 문서 한 건에 실제로 쓰는 토큰 수는 측정되지 않았다(EXP 미실행).

---

## 5. 인력 비용은? (아랍어 검수자, 한국-아랍어 검수자, NLP 엔지니어, 어노테이션)

### Takeaway
한국 인공지능 개발자 인건비 기준은 KOSA 응용SW개발자 월 694만 원이다(4대보험·퇴직충당 포함). 정보보안전문가는 월 986만 원이다. 리야드 AI 엔지니어는 연 평균 약 23.8만 리얄(9,288만 원)이고, 중급은 월 1.5~2.5만 리얄(585만~975만 원)이다. 아랍어-영어 프리랜서는 ProZ 프로필 기준 단어당 $0.07~0.15, 시간당 $35~45가 흔하다. 아랍어 AI 어노테이션 공고는 시간당 $4~65로 폭이 넓다. 건당 어노테이션 단가는 찾지 못했다.

### Cited Findings

**한국 (KOSA)**
- 「2025년 적용 SW기술자 평균임금」(공표 2024-12-03, 적용 2025-01-01~12-31)의 직무별 월평균임금은 아래와 같다. 일평균임금은 월평균을 20.6일로 나눈 값이다. 기본급, 제수당, 상여금, 퇴직급여충당금, 법인부담 4대보험을 모두 포함한다 — [KOSA 공표 PDF, 직접(pdftotext로 추출)](https://files-scs.pstatic.net/2024/12/29/Yp9k9cqjwa/2025년_적용_SW기술자_평균임금_공표.pdf)

  | 직무 | 월평균임금 | 일평균임금 | 비고 |
  | --- | --- | --- | --- |
  | 응용SW개발자 | 6,943,457원 | 337,061원 | 포함 직무: 빅데이터개발자, 인공지능개발자 |
  | 데이터분석가 | 7,751,183원 | — | |
  | IT PM | 9,145,473원 | — | |
  | IT품질관리자 | 9,692,094원 | — | |
  | IT컨설턴트 | 9,706,020원 | — | 포함 직무: 정보보호컨설턴트 |
  | 정보보안전문가 | 9,857,100원 | — | 포함 직무: 정보보호관리자 |
  | IT테스터 | 3,570,557원 | — | |

- 2026년 적용분은 전년 대비 4.7% 올랐다는 제3자 블로그 글만 있다. 공식 PDF는 확인하지 못했다 — [04noti, 요약](https://04noti.com/2026%EB%85%84-%EC%86%8C%ED%94%84%ED%8A%B8%EC%9B%A8%EC%96%B4-%EA%B8%B0%EC%88%A0%EC%9E%90-%ED%8F%89%EA%B7%A0%EC%9E%84%EA%B8%88-%EB%85%B8%EC%9E%84%EB%8B%A8%EA%B0%80/)

**사우디**
- 리야드 AI 엔지니어의 평균은 "approximately SAR 238,145"(연 9,288만 원)다. 경력별 월급은 아래와 같다. 근거는 Glassdoor, LinkedIn, PayScale 집계다 — [Edoxi, 2026-08-05, 직접](https://www.edoxi.com/studyhub-detail/average-ai-engineer-salary-riyadh)

  | 경력 | 월급 | 원화 환산 |
  | --- | --- | --- |
  | 0~2년 | 10,000~15,000리얄 | 390만~585만 원 |
  | 2~5년 | 15,000~25,000리얄 | 585만~975만 원 |
  | 5년 이상 | 25,000~41,600리얄 이상 | 975만~1,622만 원 이상 |

- 다른 집계는 다음과 같다. Payscale AI Specialist 평균은 연 15만 리얄이다. Qureos는 ML 엔지니어를 연 174,120~308,565리얄로 본다 — [Payscale](https://www.payscale.com/research/SA/Job=Artificial_Intelligence_(AI)_Specialist/Salary), [Qureos](https://qureos.com/career-guide/most-in-demand-it-jobs-in-ksa-and-uae), 둘 다 요약. Hays와 Cooper Fitch 2026 가이드의 기술직 수치는 찾지 못했다(Gulf Business 403).

**아랍어-영어 번역가·검수자**
- ProZ 개인 프로필에서 흔한 요율은 단어당 $0.07~0.15(102~219원), 시간당 $35~45(5.1만~6.6만 원)다. 하단은 $0.02~0.03, 상단은 $0.25~0.40이다. 대부분 날짜가 없고, 날짜가 있는 하나는 2024-04다 — [ProZ 프로필 다수, 요약](https://www.proz.com/profile/5582)
- 사우디 공인 번역 중앙값은 0.167 SAR/단어(65원)이고 한국 아→한은 230원/단어다 — 기지 값

**어노테이션**
- Meridial의 "Language Alignment & Resource Partner (Arabic) - Freelance AI Trainer"(C1~C2 요구) 공고는 "We offer a pay range of $6-to- $65 per hour"를 제시한다(8,772~95,030원). 날짜는 없다 — [Greenhouse, 직접](https://job-boards.greenhouse.io/agency/jobs/4867028101)
- 다른 공고들(모두 요약):
  - 아랍어 태깅·평가: $6/시간, 주 20시간 이상, 골드 97% 일치 요구(마감) — [Freelancer](https://www.freelancer.com/projects/translation/arabic-data-tagging-annotation)
  - Welocalize 튀니지 아랍어·아라비지: $4/시간 — [startup.jobs](https://startup.jobs/ai-data-annotation-specialist-arabic-tunisia-arabizi-welocalize-6105152)
  - OpenTrain MSA 음성: $10~41/시간 — [OpenTrain](https://www.opentrain.ai/jobs/arabic-audio-linguist-for-ai-speech-models--cmqxfclx0000l0aks6e93l3nz)

### Inferences
- KOSA 금액은 "사업 대가 산정용 인건비"라서 실수령 연봉보다 높다. 그래도 회사 부담 원가로는 바로 쓸 수 있다.
- 리야드 중급 AI 엔지니어(585만~975만 원)는 KOSA 응용SW개발자(694만 원)와 비슷하거나 조금 높다. 사우디화(Nitaqat), 비자, 주거 수당 같은 부대 비용은 넣지 않은 값이다.
- 평가셋 구축 인력은 시급 $25~45 구간(ProZ 하단~중간)이 현실적이다. 이 부분은 [추정]이다. 고유명사 검수에는 아랍어 원어민이면서 로마자 표기 관행을 아는 사람이 필요해서 저가 어노테이션 공고($4~6)의 인력 풀과는 다를 가능성이 있다.

### Gaps
- Upwork의 아랍어 번역가 요율 페이지가 403이라 확인하지 못했다. ProZ 공식 요율 통계도 찾지 못했다.
- 한국어-아랍어 검수자(직접 검수) 시급·건당 단가를 찾지 못했다.
- UAE NLP 엔지니어 급여, 그리고 Hays·Michael Page·Cooper Fitch 원문의 기술직 행을 찾지 못했다.
- 이집트·요르단 프리랜서 요율을 따로 나눠 보지 못했다.
- 어노테이션 건당(항목당) 단가와 벤더 견적을 찾지 못했다.

---

## 6. 비교 대상은 첫 유료 고객과 엔터프라이즈 준비까지 얼마나 걸렸나? (팀·자금)

### Takeaway
공개된 시간표는 드물다. 확인된 것만 정리하면 이렇다. 베링랩은 2020년에 법인을 세우고 2021년 매출 4억 원, 2022년 매출 20억 원과 손익분기, 2023년 27억 원을 냈다. 다만 2012년부터 번역 사업을 해 왔다. BHSN은 2020년에 세워져 2025-03 기준 누적 160억 원을 투자받았고 대기업 고객이 있다. Unbabel은 2013년 창업 후 6년간 9,100만 달러를 모았지만 2025년 "relatively low value"로 TransPerfect에 팔렸다. BasisTech의 Rosette(이름 매칭)는 1995년 창업한 회사가 27년간 키워 2022년 Babel Street에 넘긴 제품이다.

### Cited Findings
- **베링랩:** 2020년 설립. 매출은 2021년 4억 원, 2022년 20억 원, 2023년 27억 원이고 "2022년부터 BEP를 넘긴 것으로" 전해진다. 2021년 네이버D2SF와 서울대기술지주에서 시드를 받았다. TIPS 5억 원은 지원금이다. 고객사는 법무법인 세종·광장 등 "100여개"다. 2024-07에 프리A 30억 원을 목표로 했고 투자 전 가치는 약 200억 원이었다. 제품은 법률 AI 번역 '베링AI'와 검수를 더한 '베링 AI플러스'다 — [딜사이트, 2024-07-19, 직접](https://dealsite.co.kr/articles/125499)
  - 2012년 번역 사업으로 시작해 2019년 AI를 접목했다는 채용공고 문구도 있다 — [원티드, 요약](https://www.wanted.co.kr/company/16245)
- **BHSN:** 2020년 설립. 2025-03에 시리즈B 100억 원을 받았다(알토스 후속, 한국산업은행, 우리금융캐피탈). 누적은 160억 원이다. 대기업 고객으로 CJ제일제당, 한화솔루션, 애경케미칼이 있다. 직원 수는 기사에 없다 — [파이낸셜뉴스, 2025-03-30, 직접](https://www.fnnews.com/news/202503301206121224)
- **ModelFront:** MTQE는 2019년, APE는 2024년이다(Nimdzi, 직접, 위와 같음). 설립 연도는 출처마다 다르다. CB Insights는 2019년(팔로알토), ToolRadar는 2020년이다. 시드 $100K, 직원 약 30명, APE 정식 출시 2026-02다 — [CB Insights](https://www.cbinsights.com/company/modelfront), [Signalbase](https://www.trysignalbase.com/news/funding/modelfront-raises-100k-in-seed-funding), [ToolRadar](https://toolradar.com/companies/modelfront-com), 모두 요약. 홈페이지 고객은 Booking.com, Questel, FARFETCH다(직접).
- **Unbabel:** 2013-08 창업, 2014년 말 YC. 투자는 아래와 같다 — [Wikipedia, 직접](https://en.wikipedia.org/wiki/Unbabel)

  | 시점 | 라운드 | 금액 |
  | --- | --- | --- |
  | 2014-05 | 시드 | $1.5M |
  | 2016년 말 | — | $5M |
  | 2018년 초 | 시리즈B | $23M |
  | 2019-09 | 시리즈C | $60M |
  | 누적 | | $91M (1,330억 원) |

  - 2022-12 직원 349명. 2025-08 TransPerfect에 인수됐다("relatively low value").
- **BasisTech / Rosette:** 1995년 MIT 졸업생들이 세웠다. Rosette에는 Name Translator와 Name Indexer 모듈이 있다. "Rosette was sold to Babel Street in 2022." 미국 정부기관이 번역 지원에 쓴다 — [Wikipedia, 직접](https://en.wikipedia.org/wiki/Basis_Technology). 인수 금액은 비공개다 — [BusinessWire 2022-11-28, 요약](https://www.businesswire.com/news/home/20221128005123/en)
- **Tarjama:** 2025-05에 Series A 1,500만 달러를 받았다. 2025년 매출은 2,000만 달러다 — 기존 조사 S90(직접)
- **Straker:** Verify 채택이 예상보다 느렸다. FY26 상반기 매출은 1,930만 NZ달러로 전년보다 15.3% 줄었다 — 기존 조사 S100(직접)

### Inferences
- 한국 리걸 AI 두 곳(베링랩, BHSN)은 모두 설립 1~2년 안에 매출이나 대기업 고객을 확보했다. 다만 베링랩은 기존 번역 사업과 고객 기반 위에서 출발했다. 아무것도 없는 상태에서 첫 유료 고객까지 걸리는 기간의 비교 기준으로 쓰기에는 편향이 있다.
- 이름 매칭·QE 전문 제품은 오래 걸리거나(Rosette) 독립 사업으로 남기 어려웠다(Unbabel 저가 매각, Straker Verify 부진). 단독 검증 제품의 시장 크기가 제한적이라는 기존 판단(긍정-근거-조사 6)과 맞는다.
- ModelFront 규모(시드 $100K, 약 30명)를 그대로 믿기는 어렵다. 둘 다 미검증 집계 값이다.

### Gaps
- 각 사가 첫 유료 고객을 받은 날짜와 그때의 팀 규모, 그리고 SOC 2·ISO 27001 취득 시점은 공개 자료에서 찾지 못했다.
- Tarjama(Arabic.AI) 설립 연도와 초기 팀, Straker Verify 출시 시점은 이번에 확인하지 못했다.
- Babel Street가 Rosette를 얼마에 샀는지와 Rosette 이름 매칭의 출시 연도를 찾지 못했다.

---

## 7. 라이선스는? (CAMeL Tools DB, Farasa, MADAMIRA, Qalsadi, 이름 데이터)

### Takeaway
CAMeL Tools 코드는 MIT다. 현재 쓰는 `morphology-db-msa-r13`과 `disambig-mle-calima-msa-r13`은 GPL v2다. 걸프(`glf-01`)와 레반트(`lev-01`) 형태 DB는 CC BY 4.0이다. `msa-s31`은 LDC 라이선스다[확인]. Farasa는 연구용만 무료이고 상용은 개별 협의다. MADAMIRA와 CJKI 이름 DB는 상용 조건과 가격이 공개돼 있지 않다.

### Cited Findings
- CAMeL Tools 코드: "CAMeL Tools is available under the MIT license." — [GitHub README, 직접](https://github.com/CAMeL-Lab/camel_tools)
- 로컬 `~/.camel_tools/catalogue.json`(v1.6.0)의 패키지 라이선스는 아래와 같다 [확인, 2026-10-20 조회]

  | 패키지 | 라이선스 |
  | --- | --- |
  | `morphology-db-msa-r13` | GPL v2 |
  | `morphology-db-egy-r13` | GPL v2 |
  | `disambig-mle-calima-msa-r13` | GPL v2 |
  | `disambig-mle-calima-egy-r13` | GPL v2 |
  | `morphology-db-glf-01` (Gulf) | CC BY 4.0 |
  | `morphology-db-lev-01` (Levantine) | CC BY 4.0 |
  | `morphology-db-msa-s31` | LDC |
  | `disambig-bert-unfactored-{msa,egy,glf,lev}` | MIT |

- 문서 페이지의 패키지 표에는 ner-arabert가 "AraBERT", sentiment-analysis-mbert가 "Apache 2.0"으로 나온다. 이 표에는 glf와 s31이 없다 — [camel-tools readthedocs packages, 직접](https://camel-tools.readthedocs.io/en/latest/reference/packages.html)
- Farasa 래퍼(farasapy) README에 따르면 래퍼는 MIT지만 원 툴킷은 "strictly permitted for research purposes only"이고 상용은 개발자에게 문의해야 한다 — [PyPI farasapy, 요약](https://pypi.org/project/farasapy/0.1.0/). HBKU 산학협력실은 Farasa를 라이선싱 기회로 게시해 두었다 — [HBKU, 요약](https://expertise.hbku.edu.qa/sites/default/files/2025-01/Farasa_0.pdf). QCRI 안내 페이지에는 등록 후 이메일로 소스를 준다는 내용만 있고 라이선스 문구는 없다 — [QCRI ALT, 직접](https://alt.qcri.org/how-to-use-farasa-packages/)
- MADAMIRA 페이지에는 라이선스 문구가 없다. "You can still download MADAMIRA for local use."라는 문장만 있고, 다운로드는 Columbia 기술이전 목록으로 연결된다 — [NYUAD CAMeL, 직접](https://camel.abudhabi.nyu.edu/madamira/)
- CJKI 아랍어 이름 자원:
  - DANA(아랍 이름의 아랍 문자 변이)는 "Over 220,000 vocalized variants"를 담고 있다. 가격은 페이지에 없다 — [CJK.org, 직접](https://www.cjk.org/data/arabic/proper/database-arab-names-in-arabic)
  - DAN(로마자 변이)은 650만 건 이상, DAFNA(외국 이름의 아랍어 표기)는 24만 건 이상이다. 라이선스 페이지 내용은 확인하지 못했다 — [CJK.org DAFNA](https://www.cjk.org/data/arabic/proper/dafna/), 요약

### Inferences
- GPL v2에는 네트워크 조항이 없다(AGPL과 다르다). 그래서 SaaS로만 제공하면 배포에 해당하지 않아 소스 공개 의무가 생기지 않는다고 흔히 해석한다. 하지만 엔터프라이즈 고객이 사우디 데이터 상주를 위해 온프레미스 설치를 요구하면 그것은 배포다. 그때 GPL v2 DB와 그 DB에 결합된 코드의 소스 공개 문제가 생긴다. 법률 검토가 필요하다. 이 부분은 [가설]이다.
- 걸프 DB(CC BY 4.0)는 출처만 표시하면 상용으로 쓸 수 있다. 하지만 표준 아랍어(MSA) 공문서 분석에서 MSA DB를 대신할 수 있는지는 측정되지 않았다. 이 부분은 [가설]이다. `disambig-bert-unfactored-msa`(MIT)가 내부에서 GPL DB를 불러오는지도 확인이 필요하다.
- 이름 사전은 CJKI처럼 규모가 큰 상용 DB가 있지만 가격이 공개돼 있지 않다. 고객별 이름 사전(계획된 다음 단계)을 자체 데이터로 쌓는 편이 초기에는 현실적이다. 이 부분은 [제안]이다.

### Gaps
- Qalsadi 라이선스는 조사하지 못했다(검색 예산 소진).
- MADAMIRA의 Columbia 상용 라이선스 조건과 가격, Farasa의 상용 라이선스 가격, LDC SAMA(s31) 라이선스 비용, CJKI DAN·DANA·DAFNA 가격을 찾지 못했다.

---

## 8. 모델 입력용 비용 항목과 단계별 추정은?

### Takeaway
파일럿(한국 중소기업)은 인증 없이 갈 수 있다. 창업자 인건비를 빼면 현금 지출은 평가셋, API, 보험을 합쳐 수백만 원대다(추정). 엔터프라이즈(사우디 외국계)는 SOC 2 또는 ISO 27001, PDPL SCC 법률 검토, 사우디 리전 호스팅이 더해진다. 그러면 인증과 법무에만 첫해 약 5천만~1억 원과 6~12개월이 든다(추정). 가장 큰 미지수는 사우디 안에서 LLM 추론을 어떻게 처리하느냐다.

### Cited Findings: 비용 항목 표

신뢰도 기준은 다음과 같다. **상**은 공식·1차 자료를 직접 확인했다는 뜻이다. **중**은 업계 자료나 집계를 직접 확인했거나 공식 자료를 요약으로만 봤다는 뜻이다. **하**는 요약, 일화, 충돌하는 자료라는 뜻이다.

**인력**

| 항목 | 단가 (원 통화) | 원화 | 단위 | 출처 (날짜, 확인) | 신뢰도 |
| --- | --- | --- | --- | --- | --- |
| 한국 AI·응용SW 개발자 | — | 6,943,457원 | 인·월 | KOSA 2025 적용 (2024-12-03, 직접) | 상 |
| 한국 정보보안전문가(정보보호관리자) | — | 9,857,100원 | 인·월 | KOSA 2025 적용 (직접) | 상 |
| 한국 데이터분석가 | — | 7,751,183원 | 인·월 | KOSA 2025 적용 (직접) | 상 |
| 리야드 AI 엔지니어 평균 | SAR 238,145 | 92,876,550원 | 인·년 | Edoxi (2026-08-05, 직접, 집계) | 중 |
| 리야드 AI 엔지니어 중급 | SAR 15,000~25,000 | 585만~975만 원 | 인·월 | Edoxi (직접) | 중 |
| 아랍어-영어 프리랜서 (단어) | $0.07~0.15 | 102~219원 | 단어 | ProZ 프로필 (날짜 미상, 요약) | 하 |
| 아랍어-영어 프리랜서 (시간) | $35~45 | 51,170~65,790원 | 시간 | ProZ 프로필 (요약) | 하 |
| 아랍어 AI 어노테이터 | $6~65 | 8,772~95,030원 | 시간 | Meridial 공고 (날짜 미상, 직접) | 중 |
| 아랍어 저가 어노테이션 | $4~6 | 5,848~8,772원 | 시간 | Welocalize, Freelancer (요약) | 하 |
| 사우디 공인 번역 | SAR 0.167 | 65원 | 단어 | 기지 값 | — |
| 한국 아→한 번역 | — | 230원 | 단어 | 기지 값 | — |

**LLM API (모두 확인일 2026-10-20)**

| 항목 | 단가 (원 통화) | 원화 | 단위 | 출처 (확인) | 신뢰도 |
| --- | --- | --- | --- | --- | --- |
| Claude Sonnet 5.5 | 입력 $2 / 출력 $10 | 2,924 / 14,620원 | 1M 토큰 | Anthropic (직접) | 상 |
| Claude Haiku 5.5 (10만 토큰 이하) | 입력 $0.10 / 출력 $0.50 | 146 / 731원 | 1M 토큰 | Anthropic (직접) | 상 |
| Claude Opus 5.5 | 입력 $4 / 출력 $20 | 5,848 / 29,240원 | 1M 토큰 | Anthropic (직접) | 상 |
| Claude US 상주 할증 | ×1.1 | — | 배수 | Anthropic (직접) | 상 |
| Batch API 할인 (3사 공통) | ×0.5 | — | 배수 | Anthropic, OpenAI, Google (직접) | 상 |
| OpenAI gpt-6-sol | 입력 $2 / 출력 $10 | 2,924 / 14,620원 | 1M 토큰 | OpenAI (직접, 요약 도구 경유) | 중 |
| OpenAI gpt-5.4-mini | 입력 $0.75 / 출력 $4.50 | 1,097 / 6,579원 | 1M 토큰 | OpenAI (직접) | 중 |
| OpenAI 지역 처리 할증 | +10% | — | 배수 | OpenAI (직접) | 중 |
| Gemini 3.1 Pro Preview | 입력 $2 / 출력 $12 | 2,924 / 17,544원 | 1M 토큰 | Google (갱신 2026-10-19, 직접) | 중 |
| Gemini 3.1 Flash-Lite | 입력 $0.25 / 출력 $1.50 | 366 / 2,193원 | 1M 토큰 | Google (직접) | 중 |
| ALLaM 7B (IBM) | 입력 $0.22 / 출력 $0.59 | 322 / 863원 | 1M 토큰 | pricepertoken (2026-10-19, 직접, 집계) | 하 |
| Jais 30B (Azure Foundry) | 입력 $3.20 / 출력 $9.71 | 4,678 / 14,196원 | 1M 토큰 | LLM Reference (요약), FutureAGI 단위 충돌 | 하 |

**클라우드**

| 항목 | 단가 (원 통화) | 원화 | 단위 | 출처 (확인) | 신뢰도 |
| --- | --- | --- | --- | --- | --- |
| GCP Cloud SQL db-standard-2, 담맘 | $158 | 230,996원 | 월 | Bytebase (날짜 미상, 직접) | 중 |
| GCP Cloud SQL db-standard-2, 서울 | $128 | 187,136원 | 월 | Bytebase (직접) | 중 |
| GCP Cloud SQL db-standard-2, 아이오와 | $99 | 144,738원 | 월 | Bytebase (직접) | 중 |

**인증·컴플라이언스**

| 항목 | 단가 (원 통화) | 원화 | 단위 | 출처 (확인) | 신뢰도 |
| --- | --- | --- | --- | --- | --- |
| SOC 2 Type 1 심사비 (중소) | $7,500~15,000 | 1,097만~2,193만 원 | 1회 | Drata (2026-03-25, 직접) | 중 |
| SOC 2 Type 2 심사비 (중소) | $12,000~20,000 | 1,754만~2,924만 원 | 1회·연 | Drata (직접) | 중 |
| SOC 2 첫해 총액 (25명) | 약 $28,000 | 4,094만 원 | 첫해 | Drata (직접) | 중 |
| SOC 2 갭 평가 | $5,000~25,000 | 731만~3,655만 원 | 1회 | Drata (직접) | 중 |
| 침투 테스트 | $5,000~15,000 | 731만~2,193만 원 | 1회·연 | Drata (직접) | 중 |
| 컴플라이언스 플랫폼 | $8,000~20,000 | 1,170만~2,924만 원 | 연 | getagency 등 (요약) | 하 |
| ISO 27001 심사비, 1~10명 | £6,250 (5일) | GBP 미환산 | 최초 1회 | High Table (2026-10-06, 직접) | 중 |
| ISO 27001 심사비, 16~25명 | £8,750 (7일) | GBP 미환산 | 최초 1회 | High Table (직접) | 중 |
| ISO 27001 사후 심사 | 최초 비용의 약 33% | — | 연 (1·2년차) | High Table (직접) | 중 |
| ISO 27001 컨설팅 | £5,000~40,000 | GBP 미환산 | 프로젝트 | High Table (직접) | 중 |
| ISO 27001 Stage 1+2 심사 | $14,000 + $16,000 | 4,386만 원 | 최초 1회 | Konfirmity (요약) | 하 |
| ISMS-P 간편인증 수수료 | — | 600만~1,100만 원 | 1회 | 보안뉴스 (2024-07-23, 직접) | 상 |
| ISMS 간편인증 수수료 | — | 400만~700만 원 | 1회 | 보안뉴스 (직접) | 상 |
| 사우디 변호사, 부티크 | SAR 400~900 | 15.6만~35.1만 원 | 시간 | Global Law Experts (2026-08-18, 기존 S99) | 중 |
| 사우디 변호사, 국제 로펌 | SAR 1,500~3,500 | 58.5만~136.5만 원 | 시간 | Global Law Experts (기존 S99) | 중 |
| 번역가 PI 보험 (영국, £1M 보장) | £99.97~111.43 | GBP 미환산 | 연 | Simply Business (2026년 3~6월 견적, 직접) | 중 |
| 번역가 E&O (ATA, 미국 거주자만) | $410~ | 599,420원~ | 연 | ATA Chronicle (2021, 요약) | 하 |
| 번역가 배상보험 (네덜란드 NGTV) | €405 | 648,000원 | 연 | 기존 S106 (대리) | 하 |

**기간**

| 항목 | 기간 | 출처 (확인) | 신뢰도 |
| --- | --- | --- | --- |
| SOC 2 Type 1 | 1~3개월 | Drata (직접) | 중 |
| SOC 2 Type 2 | 6~12개월 (관찰 3~12개월) | Drata (직접) | 중 |
| ISO 27001 | 약 6개월 (컨설팅 경로 6~12개월) | High Table (직접) | 중 |
| AWS 사우디 리전 개시 | 2026-12 예정 | W.Media (2026-09-01, 직접) | 중 |
| Azure 사우디 동부 개시 | 2026년 4분기 예정 | Microsoft (2026-02, 직접) | 상 |

### Inferences: 단계별 추정 (모두 [추정], 산식 포함)

**(a) 유료 파일럿 (한국 중소기업, 인증 없음, 글로벌 API 사용)**

| 항목 | 산식 | 금액 |
| --- | --- | --- |
| 엔지니어 인건비 | 1명 × 6개월 × 6,943,457원 | 41,660,742원 |
| 평가셋 | 500구간 × 검수자 2명 × 3분 = 50시간; 50시간 × $30 = $1,500 | 2,193,000원 |
| LLM API | 묶음당 입력 5만·출력 5천 토큰 가정(미측정); Sonnet 5.5로 0.05M × $2 + 0.005M × $10 = $0.15 | 묶음당 약 219원, 1,000묶음 약 21.9만 원 |
| 같은 조건, Haiku 5.5 | $0.0075 | 묶음당 약 11원 |
| 보험 | 번역가 PI 수준 | 연 £100~ / $410~ |
| 법무 | 처리방침의 국외 이전 공개 항목 정비 | 비용 미조사(Gap) |
| **합계** | 인건비 제외 | **약 240만 원 + 법무비** |
| **합계** | 인건비 포함 | **약 4,400만 원** |

- 평가셋 단가 $30은 ProZ 시간당 $35~45와 어노테이션 $6~65 사이에서 고른 가정값이다.
- 파일럿 기간 6개월도 가정이다. 베링랩과 BHSN이 설립 1~2년 안에 매출을 낸 사례를 상한 쪽 참고로만 썼다.

**(b) 엔터프라이즈 준비 (사우디 외국계, 첫해)**

| 항목 | 산식 | 금액 |
| --- | --- | --- |
| SOC 2 Type 2 첫해 | 25명 기준 $28,000 | 40,936,000원 |
| 또는 ISO 27001 | 심사 £6,250~8,750 + 컨설팅 £5,000~40,000 | GBP 미환산 |
| 또는 ISO 27001 (USD 근거) | Stage 1+2 $30,000 (요약 근거) | 43,860,000원 |
| PDPL SCC·이전 위험평가·약관 법률 검토 | 30시간 가정 × SAR 400~900 = SAR 12,000~27,000 | 468만~1,053만 원 |
| 사우디 리전 DB 할증 | Cloud SQL 1대 기준 ($158 − $99) × 1,462 | 월 86,258원 (리전 할증 1.2~1.6배 가정) |
| 인력: 엔지니어 | 3명 × 12개월 × 6,943,457원 | 249,964,452원 |
| 인력: 보안 담당 | 0.5명 × 12개월 × 9,857,100원 | 59,142,600원 |
| 기간 | SOC 2 Type 2(6~12개월)와 ISO 27001(약 6개월)을 동시에 진행 | 결정 후 6~12개월 |
| **합계** | 인증과 법무만 | **약 4,500만~5,200만 원** (SOC 2 하나 + 법무) |
| **합계** | ISO 27001과 ISMS-P를 더하면 | **약 1억 원 안팎** |
| **합계** | 인력 포함 (인력 3.09억 원 + 인증·법무) | **약 3.6억~4.2억 원** |

- 사우디 안에서 LLM 추론을 처리해야 하면 이 표에 없는 비용이 붙는다. 자체 GPU 호스팅이나 사우디 리전 관리형 LLM 비용이다. 미조사.

### Gaps
- 문서 한 묶음의 실제 토큰 수는 프로젝트 실험(EXP)으로 재야 한다. 위 API 비용은 가정이다.
- 사우디 리전 GPU와 관리형 LLM 가격, 기술 E&O 보험료, 한국 로펌 자문료, 어노테이션 건당 단가가 비어 있다. 모델 민감도 분석에서는 이 항목들을 변수로 남겨야 한다.
- GBP 항목은 환율표에 GBP가 없어서 원화로 바꾸지 않았다.
