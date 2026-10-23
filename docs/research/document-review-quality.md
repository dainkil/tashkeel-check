# 조사 기록 — 서류 검수 제품을 실제 제품 수준으로 올리는 방향 (2026-10-23, 전환 전 진단)

- 이 문서: TTS 전환([ADR-023](../adr/ADR-023.md)) 직전에 한 조사다. 질문은 "서류 검수 제품(제출본 2026-10-22)을 실제 제품 수준으로 올리려면 무엇을 바꿔야 하는가"였다. 전환으로 실행하지 않게 됐지만, 진단과 문헌은 TTS 제품에도 이어진다([tts-literature.md (E)](tts-literature.md)). 표시 규칙은 [docs/README.md](../README.md)와 같다.
- 조사 방법: 코드 점검 1회(2026-10-23), 웹 검색 3갈래(아랍어 NLP·OCR·모델 / LLM 제품 품질 방법론 / 엔티티 매칭·RAG 보안·규제·시장).

## 진단: 제출본과 실제 제품 사이의 간극 (코드·문서에서 확인)

| # | 간극 | 근거 |
| --- | --- | --- |
| D1 | 기본값 M2가 미측정. 99.9%는 C1 값 | ADR-022, `config.py:55` |
| D2 | 측정이 전부 합성 문서. 시험지·정답 규칙·지시문을 같은 작업자가 설계. 반복 1회 | experiments 요약 "해석할 때 주의" |
| D3 | 동명이인 구분 신호가 코드에 없음. 사전 키 고객 전체 `"*"`, 보관함은 단어 일치 + 임베딩 순서 | `archive/search.py`, `bundle/dictionary.py:19` |
| D4 | TS-005: 두 agent 항목 단위 불일치. `arbitrate`가 `frozenset(token_ids)` 정확 일치로만 짝짓고 지시문이 단위를 정하지 않음 | `multi_agent.py:157`, `prompts.py` |
| D5 | 피드백 데이터가 끊김. `POST /v1/dictionary`가 선택 출처·`archive_hit_id`·이전 값을 저장하지 않음. 원시 agent 출력·역할별 지연 미저장 | `web/app.py:682-750`, `web/db.py` |
| D6 | 근거 검사 v2는 "같은 사람의 것인가"를 검사하지 않음 | `reconcile.py:44-66` |
| D7 | OCR 미측정·무료 제3자 API | `ocr/` |
| D8 | M2용 측정 장치 없음(실험 장치·골든·CLI가 C0~C3 고정) | `experiments/harness.py`, `cli.py:370` |
| D9 | 보관함 검색의 `LIMIT 200` 무순서, `ال` 미제거, 날짜가 업로드 시각 | `archive/search.py`, `web/db.py:432-437` |
| D10 | 데이터 외부 전송(OpenAI·OCR·LangSmith), PDPL 검토 없음 | roadmap 위험 표 |
| D11 | 공식 표기 규칙의 출처 부족 | problem-and-goals 1.1 |

**통계적 함의(계산):** 1,457개 중 오류 1건 → Wilson 95% 구간 약 [0.996, 0.9999]. 데이터가 지지하는 문구는 "≥ 99.6%". 오류율 ≤ 0.1%를 95% 신뢰로 보이려면 오류 0건 기준 약 3,000개 독립 항목이 필요하다(rule of three).

## 문헌 요약

### 엔티티 매칭·동명이인·근거 인용·보안·규제·시장

- LLM 엔티티 매칭: Peeters·Bizer EDBT 2025 (arXiv 2310.11244); Wang et al. ComEM COLING 2025(후보 N개 중 select가 pairwise보다 효율적). OpenSanctions Pairs (arXiv 2603.11051, 2026) [미확인 수치]; OpenSanctions 2025 글(설명 가능한 결정적 매칭 먼저).
- 아랍어 이름 구조: HRDAG NeurIPS 2019 HADR ws(이름 구성요소 특징); Hadith narrator ER (arXiv 2607.05424, 2026): kunya/ism 변이는 문자열 유사도 0 → 다중 신호. **동명이인은 철자가 아니라 ID·생년월일·국적·역할·거래처·날짜로 가른다.**
- 규제기관: OFAC FAQ 246(아랍어 음역 규칙 없음), ICAO 9303.
- RAG·인용 검증: BGE-M3 (arXiv 2402.03216); TREC RAG 2025; ALCE (EMNLP 2023); Wallat et al. *Correctness is not Faithfulness* (arXiv 2412.18004: 인용 최대 57% 사후 합리화); VERICITE (BioNLP 2026). → 인용을 코드가 글자 그대로 검사하는 설계가 문헌과 일치.
- 보안: *Design Patterns for Securing LLM Agents against Prompt Injections* (arXiv 2506.08837, 2025); CaMeL (arXiv 2503.18813); OWASP LLM Top 10 2025 LLM01·LLM08; Hidden-in-Plain-Text (2601.10923); Postgres RLS 패턴.
- 규제: 사우디 PDPL(2023-09 시행, 역외 이전 규정 2024-09 개정, 위험평가 가이드라인 2025-02); UAE 45/2021(시행규칙 진행 중), DIFC·ADGM 자체 규제. 역내 옵션: Bedrock UAE(me-central-1, 2025-09)·바레인, Core42 Compass, OpenAI UAE 저장 레지던시(2025-10), Anthropic `inference_geo`, HUMAIN ALLaM(제3자 API 미확인), Azure 사우디 2026-11 예정.
- 공식 표기 규칙: SAMA 계좌 개설 규칙(여권·이까마 그대로), 사우디 민사신분 시행규칙 2022, **사우디 상호법(M/83, 2025)**: 영문 상호는 아랍어 음역 동반, CR 쌍이 권위. UAE DMCC·ADGM·DIFC: 상호는 번역 않고 음역.
- 시장: Clauze.AI(리야드 2025, 역내·온프렘), Legalfly, Luminance; 이름 스크리닝 벤더에 독립 아랍어 벤치 없음. → "제품 품질" = 아랍어/영어 동등성 + 역내 처리 + 출처 있는 근거 + 낮은 오탐.

### 아랍어 NLP·OCR·모델

- SemEval-2025 Task 2 EA-MT(Conia et al.): GPT-4o COMET 91.7이지만 엔티티 정확도 45.3, Wikidata 검색 붙이면 88.5 → 근거 없으면 보류하는 설계의 직접 근거.
- CamelProp (arXiv 2505.02656): 이름 수준 실데이터 벤치, GPT-4o 73%. ANETAC (79,924쌍). Structure-Guided ER (ACL 2026 Industry).
- 디아크리틱스는 이름에 도움 안 됨: CATT, Sadeed(오류가 고유명사에 집중).
- OCR: KITAB-Bench (Findings ACL 2025: Gemini-2.0-Flash CER 0.13, GPT-4o 0.31, Surya 4.95), METATR (2026: Gemini 3 Pro 13.8%, Claude Opus 4.5 16.9%, Mistral OCR 19.4%, GPT-5.1 62.2%), Baseer (Misraj, WER 0.25로 Gemini-2.5-Pro·GPT-5보다 나음, 로컬 후보). OCR.space는 어떤 벤치에도 없음. 혼합 문자 벤치 공백.
- 아랍어 LLM: Jais 2, Falcon-H1 Arabic, ALLaM, Fanar 2.0, Hala(CC-BY-NC). 고유명사 벤치 없음.
- 공개 이중언어 문서: UN Parallel Corpus, AlignAR(CC BY 4.0, 사우디 법령), SAMA Rulebook, BOE 영문 법령, Tadawul·ADX·DFM 상장사 쌍. 목표 서류 유형의 정렬 코퍼스는 없음.

### LLM 제품 품질 방법론

- 평가: Anthropic *Demystifying evals for AI agents* (2026-01: capability vs regression, pass^k, 실패 20~50건); Hamel Husain·Shreya Shankar Evals FAQ(오류 분석 먼저, 이진, 심판 TPR/TNR); Evan Miller *Adding Error Bars to Evals* (arXiv 2411.00640, 클러스터 표준오차); *Judging the Judges* (arXiv 2406.12624); OpenAI Evals 플랫폼 2026-11-30 종료.
- 보류·보정: AbstentionBench (NeurIPS 2025, arXiv 2506.09038: 추론 파인튜닝은 보류를 24% 줄임); *Know Your Limits* (TACL 2025); Conformal Abstention (DeepMind, arXiv 2405.01563); Tao et al. (arXiv 2505.23854: 언어적 확신이 숫자보다 보정 좋음).
- 멀티에이전트: *Why Do Multi-Agent LLM Systems Fail?* (arXiv 2503.13657); *Stop Overvaluing MAD* (arXiv 2502.08788: 모델 이질성만 일관되게 도움); **Lu et al. *When Does Verification Pay Off?*** (arXiv 2512.02304: 교차 계열 검증이 최대 이득, 자기검증 최약); Stechly et al. ICLR 2025; *More Agents Is All You Need*; Soiffer et al. EMNLP 2025 Industry(캐스케이드 비용 40%·지연 60% 절감).
- 구조화 출력·비결정·캐시: *Let Me Speak Freely?* (EMNLP 2024); *The Format Tax* (arXiv 2604.03616); Atil et al. (arXiv 2408.04667, TARa@N); Thinking Machines *Defeating Nondeterminism* (2025-09); OpenAI Prompt Caching.
- 사람 수정에서 배우기: Tavakoli·Zamani (ICTIR 2025); Confidence-Driven Inference (NAACL 2025) [미확인]; Bertsch et al. (NAACL 2025: 파인튜닝은 수천 건 뒤).
- HITL·QA 표준: QE4PE (TACL 2025); Buçinca CHI 2021, Vasconcelos CSCW 2023(설명보다 검증 강제); ISO 17100·18587; MQM.

## 당시 제안했던 방향 (실행하지 않음, 기록용)

0단계(피드백 배관·수치 정정·TS-005) → 1단계(측정 체계: EXP-005 반복 3회·TARa@N, 합성 보관함 사례, CamelProp 이름 벤치, 회귀 스위트, 오류 분석 루틴) → 2단계(검증 agent를 다른 모델 계열로, 캐스케이드, conformal 보류 보정, 범주형 확신, 캐시 배치) → 3단계(식별자 추출로 동명이인 구분, 사전 키 식별자 단위, 보관함 select 문제, 하이브리드 검색) → 4단계(OCR 교체·벤치, 데이터 레지던시, RLS·주입 방어, MQM·ISO 18587 보고). 하지 말 것: 분석기 재도입, 디아크리틱스 전처리, 추론 모델 검증자, 지금 파인튜닝, 토론형 멀티에이전트, "99.9%" 표기.

이 방향은 사용자가 TTS 전환을 결정해 실행하지 않았다. 서류 검수를 다시 열 때의 출발점으로 남긴다.
