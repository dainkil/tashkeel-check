# 조사 기록 — 아랍어 TTS 이름 발음 앞단 층 (2026-10-23)

- 이 문서: TTS 전환([ADR-023](../adr/ADR-023.md))의 근거가 된 문헌·문서·제품 조사다. 2026-10-23에 웹 검색으로 모았다. 표시: [문헌○] = URL을 열어 확인, [미확인] = 2차 요약·초록·모델 카드만 본 것. 인용 전에 원문을 다시 확인한다.
- 조사 질문: (A) TTS에서 이름 발음은 어떻게 다루고 어떻게 재는가, (B) 아랍어 TTS·디아크리타이저·G2P·데이터의 현재, (C) 실시간 음성 에이전트에서 발음 제어가 끼일 자리와 제약, (D) 옛 음성 계획(2026-10-05)의 문헌, (E) 서류 검수 품질 조사에서 이어지는 것.
- 서류 검수 제품 품질 조사(같은 날 오전)는 [document-review-quality.md](document-review-quality.md)에 있다.

## 결론 (조사가 지지하는 것)

1. 이름은 디아크리타이저·LLM·TTS 모두의 약점이다. GPT-4o는 영어 표기를 받고도 고유명사 디아크리틱스 73%(CamelProp). 신경망 TTS는 저자원 고유명사를 체계적으로 틀린다(SonoEdit).
2. 엔진은 "디아크리틱스 불필요" 방향으로 간다(Habibi, Musleh·Darwish). 이름 발음 제어는 엔진 밖(앞단)에서 해야 할 필요가 커진다.
3. 발음 제어 수단(SSML phoneme·사전·customPronunciations)은 엔진·모델·로케일마다 다르고 조용히 무시되기도 한다. 지원 범위는 문서가 아니라 실험으로 채워야 한다.
4. 실시간에서는 이름 결정 단계가 LLM→TTS 사이에 보이지 않아야 한다(수십 ms). LLM은 오프라인으로, 실시간은 사전 조회 + 결정적 디아크리타이저.
5. 발음 정확도는 사람 청취로 재야 한다. MOS 예측기·오디오 LLM 심판은 발음 오류를 안정적으로 못 잡고, ASR 왕복은 오경보가 크다.
6. 녹음은 개인(생체) 데이터다. 파생 독법만 저장, 역내, 동의 기록.

## (A) 이름 발음 방법론·평가·시장

| 항목 | 출처 | 핵심 | 이 제품에서 | 확인 |
| --- | --- | --- | --- | --- |
| SonoEdit | Singh et al. (smallest.ai), arXiv 2601.17086, 2026 | 신경망 TTS가 저자원 고유명사를 체계적으로 틀림. 300개 고유명사 세트, Target-WER·PER 채점 | 문제 정의, 이름 단위 채점 프로토콜 | 문헌○ |
| OLaPh | Wirth, arXiv 2509.20086, 2025 | 모든 G2P가 이름·외래어·약어·동형이의어에서 약함. 사전 우선 + 모델 폴백 | 구조(사전 → 폴백) | 문헌○ |
| LLM G2P 벤치 | Qharabagh et al., arXiv 2409.08554 (2024); Fast, Not Fancy, arXiv 2505.12973 (2025) | LLM G2P 가능하나 지연·재현성이 중요한 곳은 결정적 G2P + 오프라인 데이터 | 실시간 경로에 LLM 없음 | 문헌○ |
| PhonologyBench | Suvarna et al. (UCLA), arXiv 2404.02456, 2024 | LLM은 동형이의어 G2P에서 약함 | LLM 출력은 후보, 근거 아님 | 문헌○ |
| CamelProp 고유명사 디아크리틱스 벤치 | Bondok, Nassar, Khalifa, Micallef, Habash (NYUAD), arXiv 2505.02656, WikiNLP 2025 | 3,000개 이름, GPT-4o few-shot(아랍어+영어) 73.0%, zero-shot 46.5%, 아랍어만 55.9%. shadda·fatha 과잉 | EXP-006 데이터, 후보 포함률 측정 | 문헌○ |
| Habibi | arXiv 2601.13802, 2026 | 방언 통합 아랍어 TTS, 디아크리틱스 없이 합성. ArVoice가 MSA 100시간 미만 | 엔진 방향, 오픈 엔진 후보 | 문헌○ |
| 음소 인식(녹음→IPA) | ZIPA; wav2vec2-xlsr-53-espeak; Magoshi et al. Interspeech 2025; Allosaurus | 범용 음소 인식기. 이름 단위 평가 없음 | 녹음 근거 경로의 부품 후보 | 문헌○(이름 평가 없음) |
| 업계 이름 발음 기능 | Google Assistant(2021), Siri, LinkedIn(2020), Teams(2024-11), Amazon 특허 | 녹음→발음 저장(Google은 녹음 보관 안 함), 말하면 후보 중 선택(Siri), 확신 비슷하면 사용자에게 물음(특허) | 확정 큐 UX | 문헌○(Alexa 출시 여부 미확인) |
| Polly 사전·phoneme | AWS 문서 | PLS 1.0, IPA·X-SAMPA, 로케일 일치, 호출당 `LexiconNames` 5개, 계정당 100개·40,000자 | 엔진 어댑터 | 문헌○ |
| Azure 사전·phoneme | MS Learn | PLS ≤100KB, 로케일당 1개, 15분 캐시, IPA·x-microsoft-sapi, HD 음성 SSML 일부, phoneme 무음 사례 | 엔진 어댑터 | 문헌○ |
| ElevenLabs phoneme | ElevenLabs 문서 | phoneme 태그는 `eleven_flash_v2`(Turbo v2) 등 일부 모델만, 다른 모델은 조용히 무시, v3/v4 SSML 없음, v4 인라인 `/IPA/`. 문서 간 불일치 | 실험 필수, alias 폴백 | 문헌○ |
| Google phoneme | Google 문서 | Chirp 3 HD만 `<phoneme>`·`<sub>`, Journey·구 Chirp SSML 없음 | 엔진 어댑터 | 문헌○ |
| 콜센터 관행 | Genesys 커뮤니티, 3CX 요청 | 표준 콜 플로에서 SSML·사전이 안 닿음, 마침표·철자 변형 우회 | 플러그인 위치 | 문헌○ |
| EmergentTTS-Eval | Manku et al. (Boson AI), arXiv 2505.23009, NeurIPS 2025 D&B | 오디오 LLM 심판, "외래어"·"복잡 발음" 범주 | 심판 설계 참고(주 지표는 아님) | 문헌○ |
| Beyond Naturalness | arXiv 2608.09930, 2026 | MOS 예측기·오디오 LLM 심판이 발음 오류를 안정적으로 못 잡음 | 사람 청취가 주 지표 | 문헌○ |
| SP-MCQA | arXiv 2510.26190, 2025 | WER 포화, 핵심 정보(이름·숫자) 정확도는 객관식으로 | 청취 평가표 설계 | 문헌○ |
| ASR 왕복 | Taylor·Richmond Interspeech 2021; Deepgram PER 글 2026-09(벤더) | 왕복이 비원어민 청취자보다 안정적이나 오경보 21~34%, 강제 정렬이 더 안정 | 왕복은 선별용 | 문헌○(벤더 수치) |
| MOS 비판 | Chiang·Huang·Lee Interspeech 2023 등 | 같은 시스템이 설정에 따라 순위가 바뀜 | MOS 안 씀 | 문헌○ |
| Arabic TTS Arena | Navid(Watad), 2026-03, HF 감사 글 2026-08 | 15개 모델 Bradley-Terry, 방언별 성능 차이, Audar-TTS-V1-Pro 강세 | 엔진 후보 참고(자연성만) | 문헌○ |
| SawtArabi | Lodagala et al. (HUMAIN·SDAIA·KTH·QCRI), Interspeech 2025 | 4시간 벤치, espeak-ng 아랍어 수정(ة·همزة الوصل·شدة), 모음 있음 MOS 3.95 vs 없음 2.53 | G2P 규칙 참고 | 문헌○ |
| 시장·규제 | stc Bahrain Bayan(2026 Q4), du TelecomGPT-Arabic, Maqsam, ElevenLabs 사우디 채용; SDAIA 딥페이크 가이드라인 SDAIA-P119(2025-05) | 걸프 음성 에이전트 수요, 복제 음성 동의·워터마크 | 고객·규제 | 문헌○(회사 주장 포함) |
| 이름 오발음 비용 | NameCoach 설문 2021(n=1,060, 벤더), Kaiser Doctors' Names Project, MIT SMR 2024 | 신뢰·회피 행동. 통제 연구 없음 | 사업 근거(일화 수준) | 문헌○ |
| 이름 발음 제품 | NameCoach, Namedrop($12/년 개인), NameShouts | 영어 중심, 녹음 저장·재생 | 경쟁·공백 | 문헌○(가격 일부 미확인) |

## (B) 아랍어 TTS·디아크리타이저·G2P·데이터

| 항목 | 출처 | 핵심 | 이 제품에서 | 확인 |
| --- | --- | --- | --- | --- |
| More Data, Fewer Diacritics | Musleh, Zhang, Darwish, arXiv 2603.01622, 2026 | 4,000시간이면 디아크리틱스 없이도 격차 상당히 메움, 있는 쪽이 여전히 나음 | 엔진 방향 | 문헌○ |
| ArTST, Fanar TTS, Chatterbox Multilingual, Spark-TTS 아랍어, Audar-TTS-V1, MiniMax-Speech | 각 저장소·논문 | ArTST는 ClArTTS 학습, Fanar는 Farasa로 디아크리틱스 후 합성, Spark는 완전 디아크리틱스 입력 전제, MiniMax 아랍어 WER 1.665(벤더) | 오픈 엔진 후보 | 문헌○ / Audar·Spark 미확인 |
| Azure 아랍어 발음 개선 | Microsoft 블로그 2024-12-24 | 디아크리틱스 모델로 단어 발음 오류 78% 감소, 아랍 문자 영어 단어 개선 | 엔진 내장 디아크리타이저도 개선 중 | 문헌○ |
| 엔진 로케일 | Azure ar-SA·ar-AE 등 16개, Polly ar-AE Hala·Zayd, Google ar-XA만, OpenAI "영어 최적화"·gpt-4o-mini-tts deprecated 표시 | 걸프 로케일은 Azure·Polly | EXP-006 엔진 목록 | 문헌○(2026-10-23) |
| Azure phoneme 알파벳 | MS Learn | ipa·sapi·ups·x-sampa, SAPI는 아랍어 없음, ar-EG/ar-SA IPA 표, 모르는 phone HTTP 400. 커스텀 사전 phoneme 대상 ar-SA Yes / **ar-AE No** | 어댑터, 매트릭스 | 문헌○ |
| Google customPronunciations | Google 릴리스 노트 2025-05 | Chirp 3 HD, 요청 단위, IPA·X-SAMPA, 여러 단어 구문, ar-XA 포함 추정. 스트리밍 SSML 불가 | 어댑터 | 문헌○(ar-XA 포함은 미확인) |
| Polly ar-AE 음소표 | AWS 문서 | Hala용 IPA/X-SAMPA 표(인두음화 모음 포함), `<phoneme>` neural·standard·long-form | 어댑터 | 문헌○ |
| CATT | Alasmary, Zaafarani, Ghannam (Abjad AI), arXiv 2407.03236, ArabicNLP 2024 | 상대 DER 30~35% 개선, GPT-4-turbo보다 9.4% 나음, Apache-2.0, ONNX export, EO 권장 | 결정적 디아크리타이저 1순위 후보 | 문헌○ |
| Sadeed | Misraj, arXiv 2504.21635, 2025 | 1.5B, WikiNews DER 5.25, 오류가 외래어·고유명사에 집중, 재정렬 필요 | 오프라인 후보원(핫패스 불가) | 문헌○ |
| Are LLMs Good Text Diacritizers? | Toyin, Magdy, Aldarmaki (MBZUAI), arXiv 2506.11602, LREC 2026 | MultiDiac CER: ChatGPT-4o 2.0, DeepSeek-R1 2.6, Claude 3.5 5.8, CATT 10.3, Jais-13B 61.9. 소형 LLM 환각 WER 35~75% | LLM은 오프라인 후보원 + 자음 골격 검사 | 문헌○ |
| Uncertainty-driven Partial Diacritization | Alblooshi, Shelmanov, Aldarmaki, UncertaiNLP 2025 | 불확실성으로 50%까지 표시 생략해도 DER 유지 | 확신 신호 | 문헌○ |
| libtashkeel | mush42, GitHub | Rust/ONNX/WASM, MIT, 확신 0.95 미만이면 격어미 sukoon 폴백 | 디아크리타이저 후보, 폴백 템플릿 | 문헌○ |
| CAMeL BERT disambiguator | camel-tools 문서 | MSA·EGY·GLF 모델, 순위 분석 | 유일한 걸프 방언 디아크리타이저 | 문헌○ |
| DialG2P | Hawasly, Mubarak, Abdelali, Ali (QCRI), ArabicNLP 2025 | 방언(이집트) G2P 비교 | G2P 참고 | 문헌○ |
| 데이터 | Arabic Speech Corpus(Halabi, CC BY-NC-SA), ClArTTS, ArVoice(CC BY 4.0), SawtArabi, Ramsa(에미라티 41h), SADA, Saudi ASWAT, Common Voice ar 23.0 | 디아크리틱스 전사가 있는 TTS급은 ArVoice·ClArTTS·ASC | 녹음 정렬·G2P 검증 참고 | 문헌○ |
| KSAA-2026 공유 과제 | KSAA·PNU·MBZUAI, OSACT7@LREC 2026 | 음성+텍스트→디아크리틱스 텍스트, 최고 베이스라인 WER 10.89(격어미 제외), CATT-Whisper 2위 DER 7.04 | 녹음 근거 경로의 과제 정의 | 문헌○ |
| 역음역(라틴→모음 아랍어) | Al Almaoui et al. MT Summit 2025 (arXiv 2502.20973); A Tale of Two Scripts (Habash et al., EACL 2026, arXiv 2507.04746); Shazal·Usman·Habash 2020; ArabiziKit | 직접 평가 없음. Arabizi→아랍어는 본질적으로 모호(주석자 일치 0.171 [미확인]) | 라틴 표기는 근거 하나, 확정은 사람 | 문헌○ / ArabiziKit 미확인 |
| PCGN 걸프 지명 자료, ICAO 9303 MRZ | UK PCGN Factfiles; ICAO TAG-MRTD 문서 | ق→g/j 변이, MRZ 표는 가역적이나 VIZ 표기는 국가 관행 | 방언 독법 설정 | 문헌○ |

## (C) 실시간 파이프라인·지연·콜센터·녹음·확신

| 항목 | 출처 | 핵심 | 이 제품에서 | 확인 |
| --- | --- | --- | --- | --- |
| 지연 예산 | Soniox 위키; smallest.ai 블로그 2026-10-05; Dograh 2026-08 | 첫 음성까지 약 800ms 목표, TTS 첫 음성 100~200ms, 전처리 단계 예산 없음. ElevenLabs Flash v2.5 TTFB ~75ms(벤더) | 이름 결정 ≤ 50ms 목표 | 문헌○ |
| Azure 지연 문서 | MS Learn 2026-02 | 텍스트 스트리밍 입력 모드는 SSML 미지원 | 문장 단위 SSML 요청 | 문헌○ |
| ElevenLabs WebSocket | ElevenLabs 문서; LiveKit 커뮤니티 2026-01 | `enable_ssml_parsing` 기본 꺼짐, 사전은 첫 메시지·청크 안에서만, LiveKit 플러그인 WS 사전 불가 | 어댑터 제약 | 문헌○ |
| LiveKit `tts_node`, Pipecat `text_filters`, Vapi 정규화기 | 각 문서 | TTS 앞 노드에 발음 규칙을 끼우는 자리. Vapi는 이름을 정확 일치 치환만 | 플러그인 위치 | 문헌○ |
| 디아크리타이저 배포성 | CATT 저장소; libtashkeel; Sadeed; Mishkal; Shakkala; NeMo TN `ar` | CATT ONNX·EO 권장(ms 수치 없음, 3자 카드 ~31ms [미확인]); Sadeed 핫패스 불가; 논문 어디에도 문장당 지연 없음 | EXP-007 직접 벤치 | 문헌○ |
| Polly 사전 한도 | AWS 문서 | 계정 100개·40,000자·호출당 5개, 크기가 지연에 영향 | 호출 단위 인라인 phoneme | 문헌○ |
| Azure 로케일별 사전 지원 | MS Learn 언어 지원표 | ar-SA·EG·KW·QA·BH·OM Yes, ar-AE No | 매트릭스 | 문헌○ |
| Google customPronunciations | Google 문서 | 요청 단위, 여러 단어, ar-XA 포함(미지원 목록에 없음) | 어댑터 | 문헌○(ar-XA 미확인) |
| 콜센터 벤더 이름 녹음 기능 | Amazon Connect·Genesys·NICE·Five9 | 찾지 못함 | 공백 | 미확인 |
| 녹음→발음 | KSAA-2026; wav2vec2-xlsr-53-espeak; Allosaurus; Whisper 디아크리틱스 파인튜닝 | 과제 정의 있음, 이름 단위 정확도 없음, Whisper 파인튜닝 미검증 | 1단계 선택 부품 | 문헌○ / Whisper 미확인 |
| PDPL·UAE 데이터 보호 | DLA Piper 요약 | 사우디 생체 데이터 민감, 역외 이전 안전장치; UAE 45/2021 "voice" 식별자, 시행규칙 미공표(2025-01 기준) | 파생 독법만 저장, 역내, 동의 | 문헌○ |
| 확신·폴백 | libtashkeel 임계 0.95; CAMeL 순위 마진; Azure HTTP 400; Polly 조용한 폴백 | 전용 논문 없음 | 정책 설계 | 문헌○ |
| 걸프 vs MSA 음성 | Polly Hala·Zayd ar-AE 이중언어; Azure ar-* 16개(HD 아랍어 없음); Google ar-XA만 | 방언 이름 독법 선호 연구 없음 | 설정·측정 | 문헌○ / 연구 공백 |

## (D) 옛 음성 계획(2026-10-05)에서 다시 쓰는 문헌

`git show f3d70cf:PROJECT_PLAN.md` 5절 참고 문헌에서. 당시 표시 ◎(원문 대조)·○(조사 보고).

| 문헌 | 이번에 쓰는 내용 |
| --- | --- |
| Marew, Keleg, Aldarmaki, *Constrained CTC Decoding for Efficient Diacritic Restoration*, arXiv 2607.18946, 2026 | 격자 제약 디코딩: 자음 골격 고정, 모음 자리만 선택. 녹음 근거 경로(격자 정렬 마진) |
| Shatnawi, Alqahtani, Aldarmaki, *Automatic Restoration of Diacritics for Speech Data Sets*, NAACL 2024 | 텍스트 vs 음성 결합 디아크리틱스. ClArTTS DER Farasa 19.17, Mishkal 21.79, 최고 텍스트 4.87~4.93, 음성 결합 2.70 |
| Toyin et al., *ArVoice*, 2025; Kulkarni et al., *ClArTTS*, 2023 | 데이터 |
| Al Wazrah et al., *KSAA-2026 Shared Task*, OSACT 2026 | 음성+무모음 전사→모음 전사 과제. 학습 없는 Fine-Tashkeel DER 10.56이 음성 결합 기준 13.50보다 나음 |
| Lodagala et al., *SawtArabi*, Interspeech 2025 | 모음 있음 MOS 3.95 vs 없음 2.53 |
| Bouamor et al., 2015 | 사람 간 디아크리틱스 불일치 WER 1.56~5.58% → 정확도 상한 |
| Laptev·Ginsburg, SLT 2022 | CTC 과신. 점수는 순위로만 |
| Angelopoulos et al., *Learn then Test* 2021; *Conformal Risk Control* ICLR 2024; Geifman·El-Yaniv NeurIPS 2017 | 임계 보정, 선택적 판정 |
| Koenecke et al., *Careless Whisper*, FAccT 2024 | ASR 환각. 왕복은 선별용 |
| Xiong et al., ICLR 2024 | LLM 확신도의 한계 |
| 설계 원칙(옛 4.1절) | 자음 골격 불변, 닫힌 후보 집합, 제안과 판정 분리, 음성 근거 없이 수정 없음, 임계는 보정 절차로, 모르면 넘김, 결정적 재현, 음성 외부 전송 없음 |

## (E) 서류 검수 품질 조사에서 이어지는 것

[document-review-quality.md](document-review-quality.md)의 항목 중 TTS에도 적용되는 것: AbstentionBench(보류는 코드가 결정), Conformal Abstention(자동 결정 중 오류 ≤ α), Lu et al. 2025(교차 모델 계열 검증), Atil et al. 2024(결정적 설정도 비결정, TARa@N), Anthropic 2026 evals 가이드(실패 사례 회귀 스위트, pass^k), Hamel Husain·Shreya Shankar Evals FAQ(오류 분석 먼저, 이진 라벨), Tavakoli·Zamani 2025(사람 라우팅), Confidence-Driven Inference(일부 라벨로 유효 추정), 사우디 PDPL 역외 이전·역내 추론 옵션, Postgres RLS, OWASP LLM08.

## 조사에서 찾지 못한 것 (공백)

- LLM이 아랍어 이름의 n-best 독법 후보를 얼마나 잘 내는지 평가한 논문
- 걸프 인명 발음 변이(방언) 데이터셋·선호 연구
- 아랍어 디아크리타이저의 고유명사 정확도·문장당 지연 보고
- 혼합 아랍어/라틴 문서 OCR 벤치(서류 검수용)
- 콜센터 벤더의 "고객 이름 녹음 → TTS" 기능
- Jais 2·Falcon-H1 Arabic 기술 보고서, Mistral OCR 3 아랍어 수치
