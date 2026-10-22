# 아랍어 문서 검수 도구 경쟁 구도

- 조사일: 2026-10-20. 웹 검색 30회, 원문 열람 20회 시도(17회 성공, 3회 실패: chatgpt.com 403, amlwatcher.com 본문 없음, wam.ae 본문 없음).
- 비교 대상: Tashkeel Check는 아랍어를 못 읽는 문서 책임자를 위한 검수 도구다. 아랍어→영어 번역에서 독법·로마자 표기가 모호한 구간(특히 인명·회사명·지명, 표 칸·서명란 같은 짧은 필드)을 표시한다. 근거 없이 철자를 확정하지 않고 "보류"하며 후보를 나열한다. 번역기가 아니다.
- 확인 표기
  - **직접**: 이번 조사에서 원문 페이지를 열어 내용을 대조했다.
  - **요약**: 검색 결과 요약이나 2차 자료만 봤다. 원문을 열지 않았다.
  - **기존**: 이 저장소의 이전 조사(`docs/business/market/upside-evidence.md`, `docs/business/market/sources.csv`의 S번호)에 이미 기록된 내용이다. 이번에 다시 열지 않았다. 사용자가 "이미 알려진 것"으로 준 항목도 여기에 넣었다.
- 환율: 1 USD = 1,462원, 1 EUR ≈ 1,600원, 1 SAR ≈ 390원. 원래 통화를 함께 적었다. GBP는 지정 환율이 없어 환산하지 않았다.
- 사실은 "Cited Findings"에, 해석은 "Inferences"에 나눴다. 업체 자체 블로그(특히 HAQQ)는 이해당사자 자료다.

## 1. 아랍어 특화 AI 번역·문서 AI 기업: 제품, 2024~2026 투자, 가격, 법률·기업 문서 기능

### Takeaway
이 범주는 자금이 가장 많이 몰리는 곳이다. Tarjama/Arabic.AI는 PIF 계열 HUMAIN의 전략투자(2026-09, 금액 비공개)를 받았고 계약·입찰 문서를 "read, check and draft"하는 에이전트를 내놓겠다고 했다. 그러나 확인한 어느 회사도 공개 가격이 없고, 고유명사 독법 모호성이나 불확실성 표시·보류 기능을 내세우지 않는다. 구매자도 아랍어를 읽는 기업이다.

### Cited Findings
**Tarjama / Arabic.AI (UAE, 창업자 Nour Al Hassan)**
- 2026-09-01, HUMAIN(PIF 소유)이 Arabic.AI에 전략투자를 했다. "The investment value was not disclosed." 투자 목적은 "accelerate the deployment of Arabic.AI's solutions to Saudi enterprise customers at scale" — [Wamda, "Arabic.AI secures strategic investment from HUMAIN", 2026-09-01, 직접](https://www.wamda.com/en/2026/09/arabicai-secures-strategic-investment-humain)
- 같은 발표에 따르면 첫 공동 제품은 세 가지다. Arabic-first 번역관리시스템 "Cleverso", 문서고 디지털화 엔진, 그리고 "read, check and draft contracts, tenders and filings"하는 문서 에이전트(조항 단위 추출, 자동 준법 점검)다. "the first solutions set to be unveiled at LEAP 2026" — [Wamda, 2026-09-01, 직접](https://www.wamda.com/en/2026/09/arabicai-secures-strategic-investment-humain)
- Arabic.AI 사이트의 제품 구성: Contract Reviewer, Doc Drafting, MENA Tender Builder, Document Summarizer, MENA Legal Q&A 등 에이전트, Translate(100+ 언어쌍), OCR, 22개 방언 음성인식, Pronoia LLM. "700+ retained clients", 유지율 98%를 내세운다. 가격은 없고 "Book a demo"만 있다. 이름 음역이나 신뢰도 표시는 언급하지 않는다. 근거 추적성은 "Every citation is traceable."라고 쓴다 — [Arabic.AI 홈페이지, 확인일 2026-10-20, 직접](https://arabic.ai)
- 2025-05 Series A 1,500만 달러(약 219억 원), Global Ventures 주도. 2025년 매출 2,000만 달러(약 292억 원). Nimdzi 2026 93위 — [Enterprise AM, 2025-05-22, 기존(S90)](https://enterpriseam.com/uae/2025/05/22/tarjama-secures-usd-15-mn-in-series-a-round-to-expand-arabic-ai/); [Wamda Capital, 요약](https://wamdacapital.com/news/tarjama-raises-15m-in-series-a-round-to-expand-arabic-ai-for-enterprise-use-across-mena/)
- 본사와 창업 연도는 자료마다 다르다. Wamda 기사는 "founded in the UAE in 2008"로 썼다. Wamda Capital은 UAE 본사에 2009년 창업으로 쓴다. HAQQ 보고서는 Arabic.AI 본사를 요르단으로 적었다 — [Wamda, 직접](https://www.wamda.com/en/2026/09/arabicai-secures-strategic-investment-humain); [Wamda Capital, 요약](https://wamdacapital.com/news/tarjama-raises-15m-in-series-a-round-to-expand-arabic-ai-for-enterprise-use-across-mena/); [HAQQ, 직접](https://haqq.ai/blog/legal-ai-mena-2026.html)

**HUMAIN (사우디, PIF 소유)**
- HUMAIN Chat은 2025-08-26 출시됐다. ALLaM 34B 기반이고 "now available exclusively to users inside the Kingdom"이다. 기능은 웹 검색, 방언 음성 입력, 아랍어·영어 전환이다. 기사에 가격, 번역, 문서 업로드 언급은 없다 — [Sharikat Mubasher, 2025-08-26, 직접](https://sharikatmubasher.com/media-hub/news/21503216/humain-launches-ai-chat-app-powered-by-allam-34b-in-saudi-arabia?lang=en)
- ALLaM을 Microsoft Foundry와 Microsoft 365 Copilot에 올릴 계획이 보도됐다 — [Middle East AI News, 요약](https://www.middleeastainews.com/p/humain-arabic-models-coming-to-microsofts)
- 집계 사이트 LM Market Cap은 IBM watsonx의 ALLaM 1 13B Instruct 가격을 입력·출력 모두 100만 토큰당 약 1.80달러(약 2,632원)로 적었다. IBM 원문으로 확인하지 못했다 — [LM Market Cap, 요약·미검증](https://lmmarketcap.com/reports/allam)
- HUMAIN Chat이나 ALLaM의 기업용 공개 가격은 찾지 못했다 — [검색 결과 요약](https://lmmarketcap.com/reports/allam)

**Inception42 / Core42 (G42, UAE)**
- Seraj는 Microsoft와 함께 만든 "Arabic-first enterprise AI model"이다. OpenAI GPT-4.1에 아랍어 데이터로 중간 학습을 더했다. Core42의 주권 AI 플랫폼 Compass로 제공한다. 대상 산업에 법률 서비스와 정부가 있다. 용례로 "document understanding, summarisation, translation, question answering"을 든다. 가격과 번역 방식 설명은 없다 — [Middle East AI News, 2026-07-02, 직접](https://www.middleeastainews.com/p/inception42-advances-arabic-ai-for-enterprise)
- Jais 3는 2026-10-15 발표됐다. 9억~3,750억 파라미터 공개 모델 6종과 Jais Speech로 구성된다 — [WAM, 2026-10-15, 요약(원문 본문 수집 실패)](https://www.wam.ae/en/article/c2r7j2m-mbzuai-inception42-launch-jais-arabic-models)

**기타 아랍어 AI 스타트업 (번역 전업 아님)**
- Intella(사우디): 2025-09 Series A 1,250만 달러(약 183억 원), Prosus 주도. 대화형 에이전트와 전사 중심이고 번역 전업이 아니다 — [Enterprise AM, 2025-09-03, 요약](https://enterpriseam.com/ksa/2025/09/03/intella-raises-usd-12-5-mn-to-scale-its-arabic-first-ai-platform/)
- Lucidya(사우디): 2025-07 Series B 3,000만 달러(약 439억 원), Wa'ed Ventures 참여. 고객경험 분석이다 — [Bloomberg Government, 요약](https://news.bgov.com/private-equity/aramcos-vc-arm-backs-record-ai-funding-round-for-saudi-startup)
- Misraj AI(사우디 코바르)의 Lahjawi는 15개 방언 간 번역과 방언→표준아랍어 변환 연구다(2025 워크숍 논문) — [ACL Anthology 2025.wacl-1.2, 요약](https://aclanthology.org/2025.wacl-1.2.pdf)
- 사우디에서 2025년 번역 전업 AI 스타트업의 투자 소식은 검색에서 나오지 않았다 — [검색 결과 요약](https://enterpriseam.com/ksa/2025/09/03/intella-raises-usd-12-5-mn-to-scale-its-arabic-first-ai-platform/)

### Inferences
- 가장 큰 위협은 Arabic.AI+HUMAIN 연합이다. "check contracts" 에이전트를 사우디 기업에 대량 배포하겠다고 했다. 다만 고객은 아랍어를 읽는 기업이고, 출력은 조항 추출과 준법 점검이다. "아랍어를 못 읽는 사람에게 이름 독법 후보를 보여 주는" 기능은 공개 자료에 없다.
- 이 범주 회사들은 Tashkeel Check의 경쟁자이면서 판매 채널·부품 공급자 후보다. 번역관리시스템(Cleverso)에 검수 부품으로 들어가는 경로를 생각할 수 있다. 아직 가설이다.
- 공개 가격이 하나도 없다. 기업 영업 견적 시장이라는 뜻이다. 장당 공개 가격을 거는 소규모 도구와 가격을 직접 비교할 대상이 없다.

### Gaps
- Mawdoo3, "Lahajati", "Kalimat"는 검색에서 해당 이름의 회사·제품을 찾지 못했다. 철자가 다를 수 있다.
- HUMAIN·Arabic.AI·Inception42의 기업용 가격, Tarjama 법률 번역의 장당 가격은 공개 자료에서 찾지 못했다.
- Wamda 기사(2026-09-01)는 첫 제품이 "LEAP 2026"에서 공개된다고 썼다. LEAP 2026의 실제 개최일은 확인하지 않았다. 날짜가 맞지 않을 수 있다.
- MAGNiTT 데이터는 열람하지 못했다.

## 2. 기계번역·품질 추정(QE)·검증 업체: 위험 구간 표시 여부와 가격

### Takeaway
위험 구간을 표시하는 상품은 이미 많다(이번 집계 9곳). 그러나 모두 세그먼트·문서 단위 품질 점수다. 아랍어 고유명사의 독법을 따로 다루거나 후보를 나열한다는 자료는 찾지 못했다. 다중 엔진 서비스는 다수결로 조용히 고른다. 가격은 장당 수백~천여 원 수준이라 Tashkeel Check의 가정 가격(장당 4,900원)보다 낮다.

### Cited Findings
- **DeepL**: 아랍어(표준아랍어, MSA)를 번역기·데스크톱/모바일 앱·브라우저 확장·API·문서 번역·용어집에 지원한다. 격식 옵션은 "will be available at a later date"였다. "The release supports Modern Standard Arabic." 이름 처리는 언급이 없다 — [DeepL 블로그 "DeepL welcomes Arabic", 최종 수정 2024-01-25, 직접](https://www.deepl.com/en/blog/deepl-welcomes-arabic)
- **DeepL 가격**(독일 표시, 연간 결제, 부가세 포함): Individual 월 €7.49(약 11,984원, 파일 3개/월), Team 사용자당 월 €24.99(약 39,984원, 파일 20개), Business 사용자당 월 €49.99(약 79,984원, 파일 100개), Enterprise 견적 — [DeepL Pro 가격 페이지, 확인일 2026-10-20, 직접](https://www.deepl.com/en/pro)
- **Google Cloud Translation** 문서 번역은 장당 0.08달러(약 117원)다 — [Google Cloud, 기존(S06)](https://cloud.google.com/translate/pricing)
- **MachineTranslation.com**: "22 of the leading AI models (including DeepL, ChatGPT, Claude, Gemini, and 18 others)"이 같은 문장을 번역한다. "The translation the majority of models agree on is selected by default." 다른 결과를 낸 모델은 "outvoted"된다. 이견을 사용자에게 보여 주는지, 이름을 따로 다루는지는 페이지에 없다. 사람 검증을 옵션으로 판다. 가격은 "from $1.50 per translation"(약 2,193원), "as low as $9.50 for 24-hour or monthly unlimited"(약 13,889원). PDF·DOCX 등 70MB까지, 오른쪽→왼쪽 배치 유지 — [MachineTranslation.com 영어→아랍어 페이지, 확인일 2026-10-20, 직접](https://www.machinetranslation.com/translation/english-arabic)
- **Phrase QPS**: MQM 기준 0~100 품질 점수를 예측한다. Phrase TMS 전 에디션, Language AI API, Strings에서 쓸 수 있다. 문서 단위 점수도 낸다. 아랍어 전용 언급과 별도 가격은 결과에 없었다 — [Phrase 지원 센터, 요약](https://support.phrase.com/hc/en-us/articles/5709672289180); [Phrase 블로그, 요약](https://phrase.com/blog/posts/phrase-quality-performance-score/)
- **ModelFront**: 검증된 단어에 과금하는 QE — [ModelFront 가격, 기존(S10)](https://modelfront.com/pricing)
- **TAUS Estimate API**: 장당 약 €0.9(약 1,440원) 환산 — [TAUS 가격(보관본), 기존(S09)](https://web.archive.org/web/20260612111722/https://www.taus.net/pricing/)
- **Smartling**: 2026-01 환각 탐지와 "LQA Agent"를 발표했다. AI 번역과 AI+사람 번역 물량이 2025년에 218% 늘었다고 밝혔다 — [Smartling, 2026-01-28, 기존(S91)](https://www.smartling.com/company-news/growth-in-ai-translation-in-2025)
- **Straker Verify**: "While uptake of the standalone Verify product has been slower than anticipated". 반기 매출 1,930만 NZ달러, 전년 대비 −15.3% — [Straker FY26 상반기 ASX 공시, 2025-11-26, 기존(S100)](https://bulletin.webull.com/qbd/announcement/20251126/499501031/83d2290439c0e307fd0491ee4e85d7b0.pdf)
- **Unbabel**은 2025-08 TransPerfect에 인수됐다(조건 비공개). **ContentQuo**는 알려진 외부 투자가 없다 — [기존(긍정-근거-조사.md 6절), 요약]
- **Intento**는 여러 MT 엔진을 연결해 언어·콘텐츠별로 고르게 하는 번역관리 플랫폼으로 소개된다. 아랍어나 품질 에이전트 언급은 찾지 못했다 — [G2 판매자 페이지, 요약](https://www.g2.com/es/sellers/intento)

### Inferences
- "위험한 곳을 표시한다"는 일반 기능은 이미 번역관리시스템과 QE 업체가 기본 기능으로 묶고 있다(Phrase는 전 에디션 포함, Smartling은 에이전트로). 일반적인 "번역 위험 표시"로는 차별점이 되지 않는다. 차별점은 "아랍어 이름 독법"이라는 좁은 축과 "보류+후보+근거"라는 출력 형식에만 있다.
- 다중 엔진 다수결(MachineTranslation.com)은 Tashkeel Check과 반대 설계다. 모델들이 같은 로마자 표기에 합의해도 그 표기가 문서 당사자의 공식 철자라는 보장은 없다. 이것은 해석이고 측정하지 않았다.
- 가격 비교(계산): 장당 4,900원은 Google 문서 번역(117원)의 약 42배, TAUS QE(1,440원)의 약 3.4배, MachineTranslation.com 건당 최저가(2,193원)의 약 2.2배다. DeepL Business는 파일당 약 800원(€49.99÷100)인데, 파일은 여러 장일 수 있어 장당 비교는 더 불리하다.
- Straker Verify의 판매 부진은 "독립형 검증 상품"을 따로 사는 수요가 약하다는 반대 증거다(기존 기록과 같은 해석).

### Gaps
- Lilt, Lokalise(AI LQA), Pairaphrase, ContentQuo 제품 세부, Amazon Translate, Microsoft Translator의 아랍어 문서 기능과 가격은 검색 예산 때문에 조사하지 못했다.
- DeepL API의 문자당 가격은 가격 페이지에 없었다(별도 문서).
- 어느 QE 업체도 아랍어 고유명사 오류를 따로 잡는지 공개 평가를 찾지 못했다.

## 3. 아랍어 이름 매칭·음역·모음 복원 도구와 API

### Takeaway
아랍어 이름 변형 문제는 제재·AML 스크리닝 시장에서 오래전부터 돈이 붙어 있다(Babel Street, NetOwl, World-Check, Dow Jones, FOCAL, AML Watcher, sanctions.io, CJKI). 이 도구들의 출력은 "두 이름이 같은 사람인가"라는 매칭 점수다. 문서 속 이름의 "읽는 법 후보와 근거"를 비아랍어 독자에게 보여 주지 않는다. 후보 생성에 가까운 부품(CJKI ARAN/DAN, Rosette Name Translator)은 있다. 그러나 개발자용 라이선스 데이터·API다.

### Cited Findings
- **CJK Dictionary Institute(일본)**: DAN("Arab personal names and their romanized variants"), DANA(아랍 문자 변형), DAFNA(외국 이름의 아랍어 표기, "over 240,000 such names and their variants", 재현율을 위해 오기를 일부러 포함), DAPNA(지명). DAN의 용도로 기계번역, 준법·위험관리, 변형 정규화, 개체명 인식을 든다. 가격은 별도 라이선스 페이지다 — [CJKI DAFNA 페이지, 확인일 2026-10-20, 직접](https://www.cjk.org/data/arabic/proper/dafna/)
- CJKI의 ARAN은 "romanizes unvocalized Arabic names into various romanization systems"이다. DAN은 이름 수백만 건과 변형을 로마자와 완전 모음 표기 아랍어로 담는다고 소개된다. Wikipedia 요약은 650만 건 이상이라고 쓴다 — [CJKI 논문·Wikipedia 검색 요약, 요약](https://en.wikipedia.org/wiki/CJK_Dictionary_Institute)
- **Babel Street(구 Basis Technology Rosette)**: 영국 G-Cloud 14 가격 문서에 Rosette Name Translator(RNT) 연간 라이선스 £158,189가 있다. 언어별 가격이고 연 2,400만 호출 기준이다 — [UK Digital Marketplace G-Cloud 14 가격 문서, 2025-09-12, 요약](https://assets.applytosupply.digitalmarketplace.service.gov.uk/g-cloud-14/documents/701282/388528207503081-pricing-document-2025-09-12-1334.pdf)
- 2016년(오래된 자료) 요르단 의료 소프트웨어 AFAQ가 환자 이름의 아랍어↔영어 변환에 Rosette를 통합했다 — [PR Newswire, 2016, 요약](https://www.prnewswire.co.uk/news-releases/basis-technology-powers-afaq-electronic-medical-records-592003201.html)
- Babel Street Match는 OEM으로 팔린다: "many software providers that offer name matching functionality white label Babel Street Match" — [Babel Street, 2023-09-26, 기존(S84)](https://www.babelstreet.com/landing/the-partner-opportunity-for-babel-street-match)
- **NetOwl**: ق의 k/q 표기, ع의 생략, "Abd al-Rahman"/"Abdul Rahman"/"Abdurrahman" 같은 분절 차이를 다룬다. "We have found it more accurate to match directly between the names in two different scripts." 대상은 아랍어 이름 DB를 OFAC 같은 라틴 문자 명단과 대조하는 은행이다. 모음 누락, 후보 독법 출력, 가격은 언급이 없다 — [NetOwl, "The Challenges of Arabic Name Matching for AML", 게시일 미표기(© 2026), 직접](https://www.netowl.com/the-challenges-of-arabic-name-matching-for-aml/)
- **LSEG World-Check**: 아랍어를 포함한 40종 이상의 비라틴 문자로 원문자 이름 스크리닝을 하고, 이것이 "reduces reliance on transliteration"한다고 쓴다 — [LSEG World-Check 자료, 2023-04-26, 요약](https://developers.lseg.com/content/dam/devportal/api-families/customer-and-third-party-screening/world-check-data-file/overview/20230426world-check-making-the-most-of-the-data.pdf). Advanced 등급에서만 제공 — [기존(긍정-근거-조사.md 2절)]
- **Dow Jones Risk & Compliance**: FY2025 매출 3억3,700만 달러(약 4,927억 원), +15% — [기존(긍정-근거-조사.md 2절), 대리]
- **FOCAL by Mozn(사우디)**: "patented Arabic-first AI designed to match complex Arabic names" — [FOCAL, 기존(S85)](https://www.getfocal.ai/products/customer-screening)
- **AML Watcher**: 아랍어 이름 매칭 페이지 제목이 "Reduce 44% More Than Traditional Tools"다. 본문은 수집하지 못해 방법을 확인하지 못했다 — [AML Watcher, 요약(제목만)](https://amlwatcher.com/arabic-name-matching/)
- **무료·오픈소스**: `arabnamer`(PyPI)는 오프라인 아랍어 이름 음역·유사도로 함자·타슈킬·타 마르부타 변형을 맞춘다. `arabic_roman_conv`(Flutter)는 سيف→"Saif"처럼 한 가지 표기를 낸다 — [depscope(arabnamer), 요약](https://depscope.dev/pkg/pypi/arabnamer); [GitHub arabic_roman_conv, 요약](https://github.com/1saifj/arabic_roman_conv)
- **Omlyar**(라틴→아랍 문자 변환, 무료)는 "Treat the result as a suggestion and confirm official or personally preferred spellings before use."라고 안내한다. 방향이 Tashkeel Check과 반대다 — [Omlyar, 요약](https://www.omlyar.com/)
- 미국 정보공동체 표준 ICS-630-01(2015)은 아랍어 인명 표기 규칙이다. 이름의 변형이 주는 "forensic information"을 없애려는 것이 아니라고 밝힌다 — [Interscript, 요약](https://interscript.org/systems/odni-ara-Arab-Latn-2015)
- **모음 복원(타슈킬) API**
  - Zyla Labs의 Arabic Diacritization API는 JSON 텍스트를 받아 모음 표기 텍스트를 돌려준다. 기업 가격은 최소 연 1만 달러(약 1,462만 원)이고, 정확도는 공개하지 않는다 — [Zyla Labs, 요약](https://www.zylalabs.com/api-marketplace/nlp/arabic+diacritization+api/812)
  - 오픈소스 `ichkil`(MIT)이 있다 — [PyPI, 요약](https://pypi.org/project/ichkil/)
  - `libtashkeel`에는 모델이 불확실하면 격 어미에 수쿤을 쓰는 taskeen 옵션이 있다 — [lib.rs, 요약](https://www.lib.rs/crates/libtashkeel_base)
  - Google은 2010년 Tashkeel API를 발표했다(오래된 자료, 현재 운영 여부 미확인) — [Google Arabia 블로그, 2010-06, 요약](https://arabia.googleblog.com/2010/06/tashkeel-api-is-now-launched.html)
  - Noqta의 아랍어 NLP API는 "coming soon"이다 — [Noqta, 요약](https://noqta.tn/en/services/category/arabic-nlp)

### Inferences
- 스크리닝 업체의 구매자(은행 준법팀)는 재현율과 경보 효율을 산다. "보류" 출력은 그 업무 흐름에 맞지 않는다는 이전 판단을 이번 자료도 바꾸지 않는다. 이 시장은 경쟁자라기보다 "이름 문제에 돈이 붙는다"는 근거이고 부품 공급처다.
- CJKI ARAN/DAN은 Tashkeel Check의 "후보 열거" 단계에 가장 가까운 상용 부품이다. 자체 사전을 만드는 대신 라이선스하는 선택지가 있다. 가격은 확인해야 한다.
- 모음 복원 도구는 한 가지 답을 조용히 고른다. libtashkeel의 taskeen 옵션은 불확실할 때 덜 단정적으로 쓰는 드문 예다. 다만 격 어미에 한정되고 이름 독법 후보를 보여 주지 않는다.

### Gaps
- LexisNexis Bridger, Dow Jones의 아랍어 이름 처리 방식, sanctions.io의 세부는 이번에 조사하지 못했다.
- CJKI·Babel Street·NetOwl·World-Check의 현재 상용 가격은 공개 자료에서 확인하지 못했다(RNT £158,189는 영국 조달 프레임워크 가격으로, 상용가와 다를 수 있다).
- 이 도구들이 문서 검수(비아랍어 독자에게 후보 표시)에 쓰인 사례는 찾지 못했다.

## 4. 걸프 지역에서 팔리는 법률 AI (글로벌 업체와 사우디·UAE 스타트업)

### Takeaway
가장 붐비는 범주다(이번 집계 글로벌 6곳 + 지역 15곳). 글로벌 업체(Harvey, Legora, CoCounsel, Lexis+ AI, Spellbook)는 공개 페이지에서 아랍어를 내세우지 않는다. 지역 업체(HAQQ, Clauze.AI, Malakah, Qaanoon.AI 등)는 아랍어 원문 이해와 이중언어 계약 검토를 판다. 어느 쪽도 이름 독법이나 음역 검수를 내세우지 않는다. 구매자는 아랍어를 읽는 변호사·사내 법무팀이다.

### Cited Findings
- **Harvey**: Al Tamimi & Company가 지역 로펌 최초로 Harvey와 파트너십을 맺고 배치를 시작했다 — [Al Tamimi, 날짜 미확인, 요약](https://www.tamimi.com/news/al-tamimi-company-and-harvey-announce-strategic-partnership-to-enhance-legal-services-with-artificial-intelligence-2). Stephenson Harwood와 CMS의 중동 사무소에서도 쓴다 — [HAQQ, "State of Legal AI in MENA 2026", 2026-05-22(수정 2026-06-11), 직접](https://haqq.ai/blog/legal-ai-mena-2026.html)
- HAQQ의 비교(2026-07-22 점검)에 따르면 Harvey, Legora, CoCounsel, Lexis+ AI, Spellbook은 공개 페이지에 아랍어나 중동 관할을 언급하지 않는다. 가격은 모두 비공개다(Harvey "Request a Demo", Lexis+ AI는 가격이 "varies based on factors such as the size of your organization", Spellbook은 "determined by the number of team members on a license"). Luminance는 "Contract analysis at volume"으로만 적고 아랍어는 점검하지 않았다. HAQQ는 이해당사자이고 자기 제품을 1위로 놓았다 — [HAQQ, "Best Legal AI for MENA and Arabic Law Firms (2026)", 2026-07-09(수정 07-22), 직접](https://www.haqq.ai/blog/best-legal-ai-mena-law-firms-2026.html)
- Harvey 기업가치는 HAQQ 보고서 안에서 "valued at $15.5B after a September 2026 round"로 적혀 있다. 그런데 보고서 게시일은 2026-05-22(수정 06-11)여서 날짜가 맞지 않는다. 검색 요약은 같은 보고서에서 "$11B"를 인용했다. 이 수치는 쓰지 않는다 — [HAQQ, 직접](https://haqq.ai/blog/legal-ai-mena-2026.html)
- **Luminance**는 사우디·아랍어 관련 공식 자료가 검색에서 나오지 않았다 — [검색 결과 요약](https://ipsnews.net/business/wp-json/wp/v2/posts/240209)
- **HAQQ(레바논)**
  - 2026년 초 300만 달러(약 43.9억 원)를 유치했다. "7,000+ clients"를 주장한다 — [HAQQ, 직접](https://haqq.ai/blog/legal-ai-mena-2026.html)
  - 가격: Chat 무료 등급 이후 월 30·100·300달러(약 4.4만·14.6만·43.9만 원), eFirm 사용자당 월 25·60달러(약 3.7만·8.8만 원) — [HAQQ, 직접](https://www.haqq.ai/blog/best-legal-ai-mena-law-firms-2026.html)
  - 법률 번역 글에서 "AI output is not admissible on its own", "treat the output as a draft to be audited, not an answer to be trusted"라고 쓴다. 점검 목록은 의무 동사, 정의어, 숫자·날짜, 부정, 관할이다. 고유명사·음역은 다루지 않는다 — [HAQQ, "AI legal translation Arabic English", 2026-06-11, 직접](https://www.haqq.ai/blog/ai-legal-translation-arabic-english)
- **Clauze.AI(사우디)**
  - 창업자 Waad Alkurini는 전 White & Case 리야드 사무소장이다. White & Case가 전략투자를 했다(금액 비공개, 이 로펌의 첫 중동 기술 투자).
  - 기능은 계약 검토, 실사, 위험·의무 식별, 아랍어·영어 문서 동시 검토다. 사우디 내 데이터 보관과 온프레미스 배치를 내세운다. 번역은 별도 기능으로 언급하지 않는다.
  - "The platform's bilingual capability is a foundational design principle, not a feature."
  - 출처: [Zawya 보도자료, 날짜 미표기, 직접](https://www.zawya.com/en/press-release/companies-news/clauze.ai-launches-as-the-first-enterprise-legal-ai-platform-built-for-saudi-arabia-and-the-region-483577)
- **Malakah(사우디, 2023 창업)**: 프리시드 60만 달러(약 8.8억 원). 노동법 중심이고 아랍어·영어를 지원한다 — [Sharikat Mubasher, 2025-02경, 요약](https://en.sharikatmubasher.com/media-hub/news/21469039/saudi-malakah-secures-600000-in-pre-seed-funding)
- **Qaanoon.AI(사우디, 2024 말 창업)**: 사우디 법령 질의응답 — [검색 결과 요약](https://sharikatmubasher.com/news/article/21573616/saudi-legal-ai-startup-clauzeai-secures-white-case-investment?lang=en)
- **기타 지역 업체**(HAQQ 보고서 목록): Qanooni(UAE, 작성·검토·리서치), Beveron(카타르, 계약 수명주기), Uniqarn(쿠웨이트, 이중언어 리서치·작성), Infiniteware(바레인, 노동법 챗봇), Lexzur(아랍어 UI, 실무·계약 관리), Jurisphere.ai(220만 달러), Saga(UAE/요르단, 160만 달러), 사우디 Shwra·Bynh·Baeynh·Signit(이름만). 보고서는 "no VC report tracks MENA legal tech as a category"라고 쓴다 — [HAQQ, 직접](https://haqq.ai/blog/legal-ai-mena-2026.html)
- Arabic.AI도 "Contract Reviewer", "MENA Legal Q&A" 에이전트를 판다 — [Arabic.AI, 직접](https://arabic.ai)

### Inferences
- 법률 AI는 아랍어 원문을 읽는 사람의 생산성 도구다. Tashkeel Check의 목표 사용자(아랍어를 못 읽는 한국 본사 담당자)는 이들의 주 고객이 아니다. 기능 경쟁보다 "같은 예산을 두고 다투는" 경쟁이다. 사우디 법인 법무팀이 Clauze.AI나 HAQQ를 이미 쓰면 별도 검수 도구 예산이 남지 않을 수 있다(가설).
- HAQQ의 "draft to be audited" 같은 메시지는 검수 필요성을 업계가 인정한다는 근거다. 그러나 점검 목록에 이름이 빠져 있다. 이름 독법이 업계 점검 항목으로 아직 자리 잡지 않았다는 신호로 읽을 수 있다. 수요가 없다는 신호일 수도 있다. 둘을 구분하려면 인터뷰가 필요하다.

### Gaps
- Luminance, Lexis+ AI Middle East, CoCounsel의 아랍어 지원을 1차 자료로 확인하지 못했다(HAQQ의 점검만 있음).
- 지역 법률 AI의 실제 고객 수와 가격은 HAQQ 외에는 공개되지 않았다.
- Al Tamimi–Harvey 파트너십 발표일을 확인하지 못했다.

## 5. 한국 업체: 아랍어 법률·문서 역량과 중동 사업

### Takeaway
확인한 한국 업체 중 아랍어 법률 문서 번역·검수를 공개적으로 파는 곳은 없다. 베링랩 사이트에는 아랍어가 없고, BHSN은 아시아로 확장 중이다. 플리토는 아랍어 음성 데이터를 모은다. 국내 경쟁 공백은 사실로 보이나, 기회인지 수요 부재인지는 이 자료로 가를 수 없다.

### Cited Findings
- **베링랩**
  - 사이트의 지원 언어 문구는 "Multilingual support for Korean, Chinese, Spanish, Indonesian, and more"이고 아랍어 언급은 없다.
  - 제품은 BeringAI Translator(계약서·소송 서류, Word·PDF 서식 유지), BeringAI+(1,000명 이상 언어전문가 후편집), API, 엔터프라이즈 엔진이다. 과금은 "Pay only for the number of words"이고 단가는 표시되지 않았다.
  - 사무소는 서울·싱가포르이고 중동 언급은 없다.
  - 출처: [beringlab.com, 확인일 2026-10-20, 직접](https://www.beringlab.com)
  - 2024-07 보도는 아랍어 미지원이었다 — [기존(사용자 제공)]
  - 채용 공고는 "아시아와 유럽의 12개 주요 언어", "300곳 이상의 고객사"라고 쓴다 — [원티드, 요약](https://www.wanted.co.kr/company/16245)
- **BHSN(앨리비)**: 일본 법인 설립 뒤 중국, 베트남, 인도네시아로 넓혀 "아시아 대표 비즈니스 리걸AI"를 목표로 한다. 중동 언급은 찾지 못했다 — [벤처스퀘어, 요약](https://www.venturesquare.net/1041948/); [헬로티, 요약](https://hellot.net/news/article.html?no=104365)
- **플리토**: 앱의 '아케이드' 기능으로 아랍어 음성 데이터 수집 프로젝트를 시작했다. "30개 이상의 방언"을 다룬다 — [벤처스퀘어, 2026-02경, 요약](https://www.venturesquare.net/?p=1038336)
- **XL8**: 실시간 번역 자막 '이벤트캣'은 42개 언어를 지원한다. 아랍어 포함 여부와 중동 사업은 확인되지 않았다 — [벤처스퀘어, 요약](https://www.venturesquare.net/957916/)
- **국내 사람 번역**: 크몽에 "아랍어 현지 원어민검수" 번역 상품이 있다(40개국 언어, 원어민 300여 명 협업 주장) — [크몽, 요약](https://kmong.com/gig/114159). 국내 아랍어 번역료는 장당 약 8.6만 원이다 — [기존(긍정-근거-조사.md 5절)]

### Inferences
- 한국 시장에서 "아랍어 원문을 한국 담당자가 확인한다"는 일은 지금 사람 번역사(장당 약 8.6만 원)나 범용 LLM이 맡는다. 전용 도구는 없다.
- 베링랩은 법률 번역과 사람 후편집 조직을 이미 갖췄다. 아랍어를 추가하면 가장 빨리 들어올 수 있는 국내 업체다. 진입 신호는 이번 자료에 없다.

### Gaps
- 트위그팜과 한컴은 조합 검색 1회("XL8 트위그팜 한컴 아랍어 중동")에서 관련 결과가 하나도 없었다. 엘박스와 로앤컴퍼니는 검색 예산 때문에 검색하지 않았다.
- 베링랩의 현재 지원 언어 전체 목록과 단가 페이지는 열지 않았다.

## 6. 범용 LLM 제품이 대체재로서 하는 일: 아랍어 문서 번역 기능, 좌석 가격, 아랍어 이름 처리 평가

### Takeaway
가장 강한 대체재다. 사용자당 월 약 2.6만~3.7만 원이면 ChatGPT, Claude, Copilot으로 아랍어 문서를 번역하고 "이 이름을 어떻게 읽을 수 있나"를 물을 수 있다. 공개 평가에서 GPT-4o는 아랍어 고유명사 모음 복원 정확도가 73%였다. 문제는 실제로 있다. 그러나 이전 조사에서 LLM은 모호성을 짚어 달라고 지시하면 금방 짚었다.

### Cited Findings
- **Claude**: Pro 월 20달러(연간 17달러), Team Standard 월 25달러(연간 20달러), Team Premium 월 125달러(연간 100달러), Enterprise 좌석 20달러+API 사용료(20석 최소) — [claude.com/pricing, 확인일 2026-10-20, 직접](https://claude.com/pricing). 원화로 Pro 29,240원, Team Standard 29,240~36,550원.
- **Microsoft 365 Copilot Business**: 연간 결제 사용자당 월 18달러(프로모션, 정가 21달러), 월 결제 25.20달러(약 26,316원/30,702원/36,842원). 프로모션은 2026-07-01~12-31, 기존 Microsoft 365 Business 고객 한정이다. 가격 페이지에 번역 기능 언급은 없다 — [Microsoft 365 Copilot 가격, 확인일 2026-10-20, 직접](https://www.microsoft.com/en-us/microsoft-365-copilot/pricing)
- Copilot의 아랍어 지원은 2024년 상반기 추가 예정으로 보도됐다. Word에서 문서 전체를 아랍어로 번역하는 기능은 Microsoft 공식 자료로 확인하지 못했다 — [Office Watch 등 검색 요약, 요약](https://office-watch.com/?p=64840)
- **ChatGPT Business**: 연간 사용자당 월 20달러, 월 결제 25달러(2석 최소). 2026-04-02에 좌석당 5달러를 내렸다는 2차 자료가 있다. OpenAI 가격 페이지는 403으로 열지 못했다 — [Elephas, 2026-09-11 갱신, 요약](https://elephas.app/resources/chatgpt-business-pricing); [eesel, 요약](https://www.eesel.ai/blog/chatgpt-work-pricing)
- **HUMAIN Chat**(사우디 한정, ALLaM 34B)은 1절 참조 — [Sharikat Mubasher, 2025-08-26, 직접](https://sharikatmubasher.com/media-hub/news/21503216/humain-launches-ai-chat-app-powered-by-allam-34b-in-saudi-arabia?lang=en)
- **고유명사 평가**: Bondok 외(Habash 연구실)는 아랍어 고유명사 모음 표기 데이터셋을 만들었다. 모음 없는 아랍어와 영어 표기를 주고 GPT-4o로 완전 모음 복원을 시험한 결과 "Achieving 73% accuracy, our results underscore both the difficulty of the task". 모음 누락이 "creating ambiguity in pronunciation and interpretation"하며 "especially for transliterated named entities of foreign origin"이라고 쓴다 — [arXiv 2505.02656, "Proper Name Diacritization for Arabic Wikipedia", 2025-05-05(v3 2025-06-23), 직접](https://arxiv.org/abs/2505.02656v1)
- 아랍어 "Abu-" 브랜드명을 AI가 프롬프트별로 어떻게 번역하는지 다룬 논문이 있다. 제목만 확인했다 — [ResearchGate, 요약(제목만)](https://www.researchgate.net/publication/395795921_Can_Artificial_Intelligence_AI_Translate_Arabic_Abu-Brand_Names_with_Different_Prompts)
- 아랍어→영어 음역에서 같은 이름이 40가지 이상 표기로 갈린다는 연구가 있다 — [검색 요약, 요약](https://uot.edu.ly/publication_item.php?pubid=321). 자음 겹침(geminate)을 홑자음으로 적는 경향은 Alharbi & Shariq(2024)가 지적했다 — [World Journal of English Language, 2024, 요약](https://www.sciedupress.com/journal/index.php/wjel/article/viewFile/25689/16045)
- 이전 조사 기록
  - GPT-4.1은 모호한 문장을 한 가지로만 읽는 경향이 있었다. 그러나 "the recognition of ambiguity improved quickly when the possibility of ambiguity was explicitly referenced in the instruction" — [Tamas, NeoLLM 2026, 기존(긍정-근거-조사.md 6절)]
  - "many off-the-shelf LLMs outperform specialized diacritization models" — [Toyin 외, LREC 2026, 기존(대리, 초록)]

### Inferences
- 손익분기(계산): LLM 좌석 1개(약 2.9만~3.7만 원/월)는 장당 4,900원 기준으로 6~8장 값이다. 장당 1.6만~1.7만 원 기준이면 약 2장 값이다. 한 달에 몇 장 이상 검수하는 고객은 "LLM에 직접 물어보기"가 금전상 더 싸다. Tashkeel Check이 좌석 가격과 다투려면 결과의 신뢰성(근거, 보류 규칙, 재현성)을 팔아야 한다.
- GPT-4o의 73%는 "이름을 조용히 틀리는" 위험이 실제로 있다는 근거다. 다만 모음 복원 과제이지 아랍어→영어 로마자 표기 과제가 아니다. 문서 속 이름의 정답률로 바로 옮길 수 없다.
- 프롬프트로 모호성 인식이 좋아진다는 이전 기록은 가장 큰 대체 위험이다. 사용자가 "이름 후보를 나열하라"고 쓰기만 하면 기능의 상당 부분을 흉내 낼 수 있다. 차이는 근거 수집과 "보류" 규칙을 일관되게 지키는 데에 있다. 이것은 C0 대비 측정으로 확인해야 할 가설이다.

### Gaps
- Gemini(Google AI Pro, Workspace), Google Docs 문서 번역의 아랍어 품질·가격은 이번에 조사하지 못했다.
- ChatGPT·Claude·Gemini가 아랍어 계약서 속 인명·회사명을 어떻게 로마자로 옮기는지 직접 비교한 공개 평가는 찾지 못했다.
- OpenAI 가격은 1차 출처로 확인하지 못했다.

## 7. 경쟁자 수(직접·인접·대체), 붐비는 범주와 빈 범주, 같은 일을 하는 제품이 있는가

### Takeaway
이번 조사 범위에서 Tashkeel Check과 같은 일을 하는 제품은 **0곳**이다. 같은 일이란 문서 번역 속 아랍어 이름의 모호한 독법을 표시하고, 후보와 근거를 비아랍어 독자에게 보여 주고, 근거가 없으면 보류하는 것이다. 인접 경쟁은 약 43곳(법률 AI 21, 번역 품질 추정 9, 이름 매칭·데이터 8, 아랍어 특화 AI 4, 모음 복원 1)이다. 대체재는 범용 번역 2, 범용 LLM 4, 사람 번역이다. 붐비는 곳은 법률 AI와 이름 스크리닝이다. 빈 곳은 "비아랍어 독자용 이름 독법 검수"와 "보류 출력"이다. 다만 빈 범주는 수요 부재의 신호일 수도 있다(Straker Verify 판매 부진).

### Cited Findings
"같은 일을 하는 제품"을 찾으려고 확장 검색("tool flags ambiguous Arabic names in translation review candidates")과 한국어 검색("아랍어 계약서 번역 검수 AI 서비스")을 했다. 해당 제품은 나오지 않았다. 가장 가까운 결과도 반대 방향 변환기의 경고 문구(Omlyar), 학술 연구, 사람 번역 상품이었다 — [Omlyar, 요약](https://www.omlyar.com/); [ResearchGate, Alharbi & Shariq 2024, 요약](https://www.researchgate.net/publication/380188229_Transliteration_of_Arabic_WordsPhrase_into_English_An_Exploration_of_Ambiguity_Markers); [크몽, 요약](https://kmong.com/gig/114159)

#### 범주별 개수 (이번 조사에서 이름이 확인된 곳만 셈)

| 범주 | 관계 | 개수 | 혼잡도 | 이름 독법·음역 특화 | 불확실성 표시·보류 |
| --- | --- | --- | --- | --- | --- |
| 이름 독법 후보+근거+보류 (비아랍어 독자용) | 직접 | 0 | 빈 곳 | — | — |
| 걸프 법률 AI (글로벌 6, 지역 15) | 인접 | 21 | 붐빔 | 없음(확인된 곳 없음) | 없음. HAQQ는 "draft to be audited"를 권고만 함 |
| 번역 품질 추정·검증 | 인접 | 9 | 붐빔(번역관리시스템 기본 기능화) | 없음 | 세그먼트·문서 단위 점수. 다중 엔진은 다수결 |
| 아랍어 이름 매칭·음역 데이터 (상용) | 인접·부품 | 8 (+Bridger 미조사) | 붐빔(AML 시장) | 있음(변형 매칭, ARAN은 다중 로마자화) | 매칭 점수. 독법 후보 표시는 확인 안 됨 |
| 아랍어 특화 AI(번역·문서) | 인접·채널 | 4 | 자금 집중 | 확인 안 됨 | "traceable citation"만 확인 |
| 모음 복원 API (상용) | 인접·부품 | 1 (+오픈소스 2, 출시 예정 1) | 희박 | 모음 복원(이름 특화 아님) | libtashkeel taskeen 옵션만 부분적 |
| 한국 업체(아랍어 법률 문서) | 인접 | 0 (확인한 6곳 중, 엘박스·로앤컴퍼니 미조사) | 빈 곳 | — | — |
| 범용 번역(DeepL, Google) | 대체 | 2 (+Microsoft·Amazon 미조사) | — | 없음 | 없음 |
| 범용 LLM(ChatGPT, Claude, Copilot, HUMAIN Chat) | 대체 | 4 (+Gemini 미조사) | — | 프롬프트에 따라 | 프롬프트에 따라 |
| 사람 번역(사우디 공인, 국내 번역사) | 대체 | 다수 | — | 사람 판단 | 번역자 주석 |

#### 전체 경쟁자 요약표

가격의 원화 환산은 1 USD = 1,462원, 1 EUR = 1,600원 기준이다. "—"는 공개 자료에서 찾지 못했다는 뜻이다. 글로벌 대기업(DeepL, Google, Phrase, Smartling, Babel Street, LSEG, Dow Jones, Harvey, Luminance, Legora, Spellbook, OpenAI, Anthropic, Microsoft 등)의 본사 칸은 일반적으로 알려진 사실을 적은 것이다. 이번에 출처를 열어 확인하지 않았다. 각 행의 근거 링크는 1~6절의 해당 항목에 있다.

| # | 이름 | 범주 | 하는 일 | 아랍어 | 이름·음역·모음 모호성 | 불확실성 표시·보류 | 대상 구매자 | 공개 가격 | 투자·매출 | 본사·시장 | 확인 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Tarjama / Arabic.AI | 아랍어 특화 AI | 번역(100+쌍), OCR, Contract Reviewer 등 에이전트, Pronoia LLM, Cleverso 번역관리시스템(예정) | 예 | 언급 없음 | "traceable" 인용만 | 아랍어권 기업·정부 (700+ 고객 주장) | — (데모 예약) | Series A $15m(2025-05, 약 219억 원), 2025 매출 $20m(약 292억 원), HUMAIN 전략투자(2026-09, 비공개) | UAE(요르단 표기 자료도 있음), 사우디 확장 | 직접+기존 |
| 2 | HUMAIN (PIF) | 아랍어 특화 AI | ALLaM 34B, HUMAIN Chat, Arabic.AI와 문서 에이전트 공동 개발 | 예 | 언급 없음 | 언급 없음 | 사우디 소비자·기업 | — (watsonx ALLaM 13B $1.80/100만 토큰, 미검증) | PIF 소유 | 사우디 | 직접+요약 |
| 3 | Inception42 / Core42 (G42) | 아랍어 특화 AI | Seraj(GPT-4.1 기반, Compass), Jais 3 공개 모델 | 예 | 언급 없음 | 언급 없음 | 법률·금융·정부 등 기업 | — | — | UAE | 직접+요약 |
| 4 | Misraj AI (Lahjawi) | 아랍어 특화 AI | 방언 간 번역 연구 | 예 | 해당 없음 | 해당 없음 | — | — | — | 사우디 | 요약 |
| 5 | DeepL | 범용 번역 | 번역기, 문서, API, 용어집 (MSA) | 예(2024~) | 언급 없음 | 없음 | 개인·기업 | Individual €7.49(약 1.2만 원), Team €24.99(약 4.0만 원), Business €49.99(약 8.0만 원)/사용자·월 | — | 독일, 세계 | 직접 |
| 6 | Google Cloud Translation | 범용 번역 | 문서 번역 API | 예 | — | — | 개발자·기업 | $0.08/장(약 117원) | — | 미국 | 기존 |
| 7 | MachineTranslation.com | 품질·다중 엔진 | 22개 모델 다수결, 사람 검증 옵션 | 예 | 언급 없음 | 다수결로 선택("outvoted") | 개인·SMB | $1.50/건~(약 2,193원), $9.50 24시간/월 무제한(약 1.4만 원) | — | 미확인 | 직접 |
| 8 | Phrase QPS | 품질 추정 | MQM 기반 0~100 점수, 문서 점수 | 미확인 | 없음 | 세그먼트·문서 점수 | 로컬라이제이션팀 | TMS 전 에디션 포함, 별도가 — | — | 독일 | 요약 |
| 9 | ModelFront | 품질 추정 | 세그먼트 위험 예측 | 미확인 | 없음 | 세그먼트 표시 | 번역사·기업 | 검증 단어당 과금 | — | 미국 | 기존 |
| 10 | TAUS Estimate API | 품질 추정 | QE 점수 API | 미확인 | 없음 | 점수 | 번역 업계 | 약 €0.9/장(약 1,440원) | — | 네덜란드 | 기존 |
| 11 | Smartling LQA Agent | 품질 검증 | LQA 에이전트, 환각 탐지 | 미확인 | 없음 | 오류 표시 | 기업 로컬라이제이션 | — | — | 미국 | 기존 |
| 12 | Straker Verify | 품질 검증 | 독립형 검증 상품 | 미확인 | 없음 | 검증 | 기업 | — | 반기 매출 NZ$19.3m(−15.3%), Verify "slower than anticipated" | 뉴질랜드 | 기존 |
| 13 | Unbabel (TransPerfect) | 품질 추정 | QE+번역 | 미확인 | 없음 | 점수 | 기업 | — | 2025-08 인수(조건 비공개) | 포르투갈/미국 | 기존 |
| 14 | ContentQuo | 품질 관리 | LQA 플랫폼 | 미확인 | 없음 | 평가 | 로컬라이제이션팀 | — | 알려진 외부 투자 없음 | 미확인 | 기존 |
| 15 | Intento | 번역 관리 | 다중 MT 엔진 선택 | 미확인 | 없음 | 미확인 | 기업 | — | — | 미국 | 요약 |
| 16 | Babel Street (Rosette, Match) | 이름 매칭·음역 | 이름 매칭 OEM, Rosette Name Translator | 예 | 예(이름 변환) | 매칭 점수 | 정부·금융·OEM | RNT 연 £158,189/언어(영국 G-Cloud 14, 2,400만 호출) | — | 미국 | 요약+기존 |
| 17 | NetOwl | 이름 매칭 | 교차 문자 직접 매칭 | 예 | 예(표기·분절 변형) | 언급 없음 | 은행 AML/KYC | — | — | 미확인 | 직접 |
| 18 | LSEG World-Check | 이름 스크리닝 | 40+ 비라틴 문자 원문자 스크리닝 | 예 | 음역 의존을 줄임 | 매칭 | 금융 준법 | — (Advanced 등급) | — | 영국 | 요약+기존 |
| 19 | Dow Jones R&C | 이름 스크리닝 | 위험·준법 데이터 | 미확인 | 미확인 | 매칭 | 금융 준법 | — | FY2025 매출 $337m | 미국 | 기존 |
| 20 | FOCAL by Mozn | 이름 스크리닝 | "Arabic-first" 이름 매칭 | 예 | 예 | 매칭 | 사우디 금융 | — | — | 사우디 | 기존 |
| 21 | AML Watcher | 이름 스크리닝 | 아랍어 이름 매칭("Reduce 44%") | 예 | 예(주장) | 미확인 | 금융 준법 | — | — | 미확인 | 요약 |
| 22 | sanctions.io | 이름 스크리닝 | 제재 명단 스크리닝 | 미확인 | 미확인 | 매칭 | 준법팀 | — | — | 미확인 | 기존 |
| 23 | CJK Dictionary Institute | 이름 데이터 | DAN·DANA·DAFNA·DAPNA, ARAN(다중 로마자화) | 예 | 예(변형·모음 표기 형태) | 데이터(후보 생성 가능) | MT·준법·검색 개발사 | 라이선스(비공개) | — | 일본 | 직접+요약 |
| 24 | Zyla Labs Diacritization API | 모음 복원 | 텍스트 모음 복원 | 예 | 모음(이름 특화 아님) | 없음 | 개발자 | 기업 최소 연 $10,000(약 1,462만 원) | — | 미확인 | 요약 |
| 25 | Harvey | 법률 AI(글로벌) | 법률 AI | 공개 언급 없음 | 없음 | 없음 | 대형 로펌 (Al Tamimi, 중동의 Stephenson Harwood·CMS) | — (데모) | 기업가치 수치 자료 간 충돌 | 미국 | 요약+직접(HAQQ) |
| 26 | Luminance | 법률 AI(글로벌) | 계약 분석 | 미확인 | 없음 | 없음 | 기업 법무 | — | — | 영국 | 요약 |
| 27 | Legora | 법률 AI(글로벌) | 협업 검토 | 공개 언급 없음 | 없음 | 없음 | 중대형 법무팀 | — | — | 스웨덴 | 직접(HAQQ) |
| 28 | Thomson Reuters CoCounsel | 법률 AI(글로벌) | 리서치·검토·작성 | 공개 언급 없음 | 없음 | 없음 | 법무 | — | — | 미국(호스팅 지역은 영국·호주·캐나다로 명시) | 직접(HAQQ) |
| 29 | Lexis+ AI | 법률 AI(글로벌) | 판례 리서치 | 공개 언급 없음 | 없음 | 없음 | 법무 | — ("varies") | — | 미국·영국 판례 DB 강점 | 직접(HAQQ) |
| 30 | Spellbook | 법률 AI(글로벌) | Word 계약 작성 | 공개 언급 없음 | 없음 | 없음 | 거래 변호사 | — (인원 기준) | — | 캐나다 | 직접(HAQQ) |
| 31 | HAQQ | 법률 AI(지역) | 리서치·작성·실무관리 | 예(아랍어 원문) | 없음 | 감사 권고만 | 소형·중형 로펌 | 월 $30·100·300, eFirm $25·60/사용자 | $3M(2026 초), "7,000+ clients" 주장 | 레바논, 중동 전역 | 직접 |
| 32 | Clauze.AI | 법률 AI(지역) | 이중언어 계약 검토·실사 | 예 | 언급 없음 | 언급 없음 | 사우디 사내 법무·로펌 | — | White & Case 전략투자(비공개) | 사우디 | 직접 |
| 33 | Malakah | 법률 AI(지역) | 법률 상담, 계약 작성 | 예 | 없음 | 없음 | 사우디 개인·기업 | — | 프리시드 $600K | 사우디 | 요약 |
| 34 | Qaanoon.AI | 법률 AI(지역) | 사우디 법령 Q&A | 예 | 없음 | 없음 | 일반 | — | — | 사우디 | 요약 |
| 35 | Lexzur | 법률 AI(지역) | 실무·계약 관리 | 아랍어 UI | 없음 | 없음 | 로펌·사내 법무 | — | — | 미확인 | 직접(HAQQ) |
| 36~45 | Qanooni, Beveron, Uniqarn, Infiniteware, Jurisphere.ai, Saga, Shwra, Bynh, Baeynh, Signit | 법률 AI(지역) | 작성·검토·리서치·CLM 등 | 일부 이중언어 | 언급 없음 | 언급 없음 | 로펌·기업 | — | Jurisphere $2.2M, Saga $1.6M, 나머지 비공개 | UAE·카타르·쿠웨이트·바레인·사우디 | 직접(HAQQ 목록) |
| 46 | 베링랩 | 한국 | 법률·특허 AI 번역, 후편집 | 사이트에 없음 | 없음 | 사람 후편집 | 로펌·법무팀 | 단어당(단가 미표시) | — | 서울·싱가포르 | 직접+기존 |
| 47 | BHSN (앨리비) | 한국 | 기업 법률 AI | 확인 안 됨 | 없음 | — | 기업 법무 | — | 스케일업 팁스 R&D 최대 12억 원 | 한국·일본·아시아 | 요약 |
| 48 | 플리토 | 한국 | 언어 데이터·번역 | 아랍어 음성 데이터 수집 | 없음 | — | AI 데이터 구매자 | — | — | 한국 | 요약 |
| 49 | XL8 | 한국 | 실시간 번역 자막(42개 언어) | 미확인 | 없음 | — | 행사·방송 | — | — | 한국·미국 | 요약 |
| 50 | ChatGPT Business | 범용 LLM | 문서 번역·질의 | 예 | 프롬프트 의존 | 프롬프트 의존 | 개인·팀 | $20(연)/$25(월)/사용자 | — | 미국 | 요약 |
| 51 | Claude | 범용 LLM | 문서 번역·질의 | 예 | 프롬프트 의존 | 프롬프트 의존 | 개인·팀 | Pro $20, Team $25(월)/$20(연) | — | 미국 | 직접 |
| 52 | Microsoft 365 Copilot Business | 범용 LLM | Office 내 AI | 예(2024~) | 미확인 | 미확인 | M365 기업 | $18(프로모션)/$21(연)/$25.20(월) | — | 미국 | 직접 |
| 53 | HUMAIN Chat | 범용 LLM | 아랍어 챗 | 예 | 미확인 | 미확인 | 사우디 사용자 | 미확인 | (HUMAIN) | 사우디 한정 | 직접 |
| 54 | 사람 번역(사우디 공인·국내 번역사·크몽 등) | 대체 | 번역·공증 | 예 | 사람 판단 | 번역자 주석 | 전부 | 사우디 장당 중앙값 62.5리얄(약 2.4만 원), 국내 장당 약 8.6만 원 | 사우디 번역업 상업등기 7,964건(+20%) | 사우디·한국 | 기존 |

### Inferences
- **직접 경쟁 0곳은 "공개적으로 그렇게 파는 곳이 없다"는 뜻일 뿐이다.** 기능을 구성하는 부품은 모두 시장에 있다. 이름 변형 데이터(CJKI), 이름 변환 API(Rosette RNT), 위험 표시 UI(QE 업체), 프롬프트로 모호성을 짚는 LLM이다. 진입 장벽은 기술보다 측정과 신뢰(근거·보류 규칙의 일관성)에 있다.
- **붐비는 범주:** 걸프 법률 AI(21곳)는 아랍어를 읽는 사람을 위한 도구다. 이름 스크리닝(8곳 이상)은 은행 준법팀을 위한 도구다. 번역 QE(9곳)는 번역관리시스템 기본 기능이 되어 간다. 세 범주 모두 "아랍어를 못 읽는 문서 책임자"를 주 구매자로 삼지 않는다.
- **빈 범주:** 비아랍어 독자용 이름 독법 검수, 확정 대신 보류를 출력하는 번역 도구, 한국 업체의 아랍어 법률 문서 서비스. 빈 이유가 수요 부재일 가능성을 배제할 근거는 없다. Straker Verify 부진, Nimdzi가 기록한 "refuse to pay for the human oversight"(기존)가 반대 신호다.
- **가격 위치(계산):** 장당 4,900원은 기계 번역·QE(117~1,440원/장)보다 3~42배 비싸다. 사람 번역(사우디 약 2.4만 원, 국내 약 8.6만 원)보다는 싸다. LLM 좌석(월 약 2.6만~3.7만 원)과는 월 6~8장에서 같아진다. 장당 1.6만~1.7만 원이면 사우디 공인 번역가의 약 2/3 수준이다. "번역보다 싼 검수"라는 논리가 약해진다.
- **가장 그럴듯한 경쟁 진입자(가설):** ① Arabic.AI+HUMAIN의 계약 "check" 에이전트에 이름 검증이 붙는 경우 ② 베링랩이 아랍어를 추가하는 경우(국내) ③ 범용 LLM이 "불확실한 고유명사 표시"를 기본 동작으로 넣는 경우. 세 경우 모두 이번 자료에 진입 신호는 없다.

### Gaps
- LexisNexis Bridger, Lilt, Lokalise, Pairaphrase, Amazon·Microsoft 번역, Gemini/Google Docs, 엘박스·로앤컴퍼니·트위그팜·한컴은 이번 집계에서 확인하지 못했다. 이들을 넣으면 인접·대체 개수는 늘어난다.
- 집계는 검색 30회로 찾은 이름 기준이다. 지역 법률 AI 목록은 이해당사자(HAQQ) 한 곳의 목록에 크게 의존한다.
- "같은 일을 하는 제품"이 비공개 사내 도구나 번역사 내부 QA로 존재하는지는 공개 자료로 확인할 수 없다.
- 경쟁자 고객의 실제 구매 이유(이름 오류를 얼마나 문제로 보는지)는 인터뷰 없이 알 수 없다.
