# 시스템 구조

- 기준: TTS 전환 계획(2026-10-23, [ADR-023](adr/ADR-023.md)). **코드는 아직 서류 검수 제출본(2026-10-22) 그대로다.** 이 문서는 "지금 코드가 무엇이고 그중 무엇을 어떻게 쓰는가"와 "새로 만들 것 [제안]"을 구분해 적는다. 서류 검수 구조(그래프 6노드, 조건 C0~C3, M2, 보관함, 옛 절 번호 4.1~4.11)는 [보관본](archive/document-review/architecture.md)에 있다.
- 마지막 업데이트: 2026-10-23
- 문서 지도는 [docs/README.md](README.md).

**요약.** 제품은 두 경로다. **오프라인 경로**는 이름 목록에서 독법 후보를 만들고(분석기·디아크리타이저·LLM·라틴 표기 역음역), 근거를 검사하고(라틴 표기 일치·녹음 정렬·사람 확정), 사람이 확정한 것만 고객 발음 사전에 넣는다. LLM·agent·근거 검사는 모두 여기 산다. **실시간 경로**는 발화 텍스트를 받아 사전을 조회하고, 없으면 결정적 디아크리타이저의 기본 독법에 낮은 확신을 붙여 엔진 형식으로 치환한다. LLM·난수가 없고 목표는 문장당 50ms 이하다 [제안]. 서류 검수 때 60~84초 걸리던 그래프는 실시간에 들어오지 않는다.

## 4.1 설계 원칙

옛 음성 계획(2026-10-05, `git show f3d70cf:PROJECT_PLAN.md` 4.1절)의 원칙과 서류 검수에서 확인한 것을 합쳤다.

| 원칙 | 구현 | 확인 방법 |
| --- | --- | --- |
| 자음 골격 불변 | 출력에서 디아크리틱스를 지운 문자열이 입력과 같을 때만 쓴다. 다르면 폐기하고 오류로 센다(LLM 디아크리타이저 환각 방어, Toyin et al. 2026 [문헌○]) | 골격 변경 건수 0(자동 테스트) |
| 닫힌 후보 집합 | 최종 독법은 후보 목록 중 하나다. 후보마다 출처(사전·분석기·CATT·LLM·역음역)를 남긴다 | 후보 밖 출력 0 |
| 제안과 판정의 분리 | 모델은 후보와 점수만 낸다. 판정은 공개된 규칙과 보정된 임계값이 한다 | 판정 함수 단위 테스트 |
| 근거 없이 확정하지 않음 | 사전 등록은 사람 확정·녹음 정렬 통과·라틴 표기 일치 중 하나가 있을 때만. 디아크리타이저·LLM 출력은 기본 독법이지 확정이 아니다 | 근거 없는 등록 0 |
| 실시간에서 모르면 기본 독법 + 확신 표시 + 로그 | 발화를 막지 않는다. 저확신은 사후 확정 큐로 | 확신 등급 누락 0 |
| 결정적 재현 | 실시간 경로에 LLM·난수 없음. 사전·디아크리타이저·엔진 어댑터 버전을 기록 | 같은 입력 재실행 일치 테스트 |
| 음성·텍스트 외부 전송 최소화 | 실시간 경로는 로컬. 녹음은 역내 저장, 파생 독법만 보관을 기본으로, 동의 기록 | 호출 로그, 설정 기본값 |
| 엔진은 교체 가능, 지원 범위는 측정값 | 엔진·모델·로케일별 "디아크리틱스 존중 / phoneme / 사전" 매트릭스를 EXP-006으로 채우고, 미지원이면 폴백 | 매트릭스 표와 실험 기록 |

## 4.2 두 경로

```
오프라인(배치, LLM·agent·근거 검사가 사는 곳)          실시간(발화마다, LLM→TTS 사이, 목표 ≤ 50ms)
───────────────────────────────────────────          ────────────────────────────────────────────
CRM 이름 목록 · 등록 서류(라틴 표기) · 본인 녹음         음성 에이전트의 LLM 출력(문장 단위 버퍼)
  → 후보 생성                                            → 토큰화(text.py) → 고유명사 탐지
      고객 사전 / CAMeL diac(격어미·caphi 보존)                 (사전 키 조회 + 규칙·경량 NER)
      / CATT / LLM 디아크리타이저(자음 골격 검사)            → 사전 적중: 확정 독법 (high)
      / 라틴 표기 역음역 필터                                → 미적중: 결정적 디아크리타이저 1위 + 마진
  → 근거 검사                                                   마진 충분 (medium) / 미달 (low)
      라틴 표기 일치 · 녹음 격자 정렬 마진 · 사람 확정        → 엔진 어댑터로 치환
  → 두 역할 일치 게이트(기존 arbitrate, 비교자 교체)            Azure IPA / Polly IPA·X-SAMPA / Google
  → 확정 큐(합성해 들려주고 고르기 · 직접 입력 · 녹음)           customPronunciations / ElevenLabs alias·v4 IPA
  → 고객 발음 사전                                              / 디아크리틱스 텍스트
      (customer_id, entity_id, arabic_key)                → 발화 로그(독법·확신·엔진·버전·지연)
      + pronunciation · phonemes · source · overrides       → 저확신은 사후 확정 큐
```

- **확신 등급 [제안]:** high = 고객 사전 적중(근거 있는 확정). medium = 분석기 독법이 하나뿐이거나 라틴 표기와 일치하는 후보가 하나뿐일 때의 기본 독법. low = 디아크리타이저 1위만 있고 2위와의 마진이 임계 미만일 때. 임계는 1단계 라벨로 보정한다([evaluation.md 6.7절](evaluation.md)).
- **동명이인:** 통화 맥락의 고객 ID를 `entity_id`로 받아 사전 키에 넣는다. 서류 검수 때 고객 전체 `"*"` 키가 같은 철자의 다른 사람을 잘못 확정할 수 있던 문제를 처음부터 피한다. ID가 없으면 `"*"` 폴백 + low.
- **스트리밍 제약:** Azure 텍스트 스트리밍 모드는 SSML을 받지 않고, Google 스트리밍 요청도 SSML 미지원, ElevenLabs WebSocket은 사전 매칭이 청크 안에서만 된다 [문헌○]. 그래서 실시간 경로는 이름이 든 문장 경계까지 버퍼링한 뒤 문장 단위로 엔진에 보낸다. LiveKit `tts_node`, Pipecat `text_filters`가 끼울 자리다.

## 4.3 지금 코드에서 가져가는 것, 바꾸는 것, 새로 만드는 것

2026-10-23 코드 점검 결과다. 경로는 `src/tashkeel_check/` 기준.

| 구분 | 그대로 쓴다 | 바꿔야 한다 | 새로 만든다 [제안] |
| --- | --- | --- | --- |
| 텍스트 처리 | `text.py` 토큰·구간 ID(`s01`, 전역 토큰 번호, offset). `normalize_key`(디아크리틱스·tatweel 제거, alef·ة·ى 통일) → 사전 조회 키로 적합. 문서 구조에 묶이지 않아 한 문장도 된다 | 토큰 정규식이 구두점을 자르지 않음(발화 텍스트엔 영향 적음) | 디아크리틱스·SSML을 offset으로 끼워 넣는 치환기 |
| 분석기 | `analyzer.py`가 CAMeL `diac`를 보관하고 독법 수를 센다 | 입력 디아크리틱스를 지우고 분석(`analyzer.py:150`), 격어미를 버림(TTS에는 필요), `caphi` 발음 필드를 읽지 않음, DB를 `builtin_db()` 무명 로드 | 격어미·`caphi` 보존 옵션. 실제 걸프 인명의 36.9%는 분석 0개(EXP-001)라 보조 후보원 |
| 로마자 | `romanize.py` Arabic→Latin, `strict_key`, `match_spelling`, MRZ 파서 | 정보 손실(ص→s, ع→') | **Latin→모음 아랍어 역음역 없음.** `experiments/exp001.py:77-88`(CAMeL diac 후보를 로마자화해 영문 표기와 맞는 것만 거름)을 후보 필터로 확장 |
| 사전 | `name_dictionary` 표(`web/models.py:135-152`) 키 `(customer_id, entity_id, arabic_key)`, `upsert_dictionary_entry`, 등록·목록·취소 API, Alembic 0001~0004 | `english_name NOT NULL`, `dictionary_apply._overlay`가 `strict_form(english)` 비교, `archive/search.py:181`이 english만 반환 | 컬럼 `pronunciation`(디아크리틱스)·`phonemes`(IPA)·`source`·`engine_overrides`(JSON)·`previous_value`(Alembic 0005). 조회 루프(`apply_dictionary`)는 그대로 |
| API | `POST /v1/bundles/review`(동기, LLM 없음, 사전 인라인 적용)가 `/v1/pronounce`의 템플릿. `POST /v1/extract`도 동기. API 키·고객·사용량(`web/auth.py`·`customers.py`·`usage.py`) | 작업 큐(`JobManager`, worker 1)·SSE·그래프는 60~84초 → 실시간에 못 씀 | `POST /v1/pronounce`, `POST /v1/names/import`, `GET/POST /v1/names/queue`(확정 큐), `GET /v1/engines`(지원 매트릭스) |
| 그래프·agent | load→analyze→agent→validate(1회 재시도)→reconcile 골격, 토큰 ID로 지목, 인용이 구간에 있는지 검사(`reconcile.py:59`), 두 역할 일치 게이트(`multi_agent.arbitrate`) | 스키마 `romanized` 필수·`Evidence.quote` 라틴 필수·구간마다 번역 필수(`graph.py:151-169`), `verify_evidence`가 영문 철자 비교, `arbitrate`가 `strict_form` 비교, 프롬프트 전부 "영어로 번역" | 오프라인 후보 생성 agent(출력 `reading` 필드는 `schemas.py:10-13`에 이미 있음 + 근거 종류), 비교자를 디아크리틱스 정규형으로 교체 |
| 회사 기록 MCP | `ScopeRegistry` 작업별 범위 토큰(`mcp/records.py:52-77`), 인프로세스 FastMCP, 토큰 ID 묶음 입력 | 결과가 `english`·`latin_candidates`, `build_passages`가 라틴 문자 없는 구절을 버림 | 녹음·디아크리틱스 기록을 돌려주는 툴 |
| 실험 장치 | `experiments/harness.py`의 `Spec` 계약, `plan.json`·`runs.jsonl`·`STOP`·재개·예산, Clopper–Pearson·부트스트랩 | 작업 단위가 `runner.run_document`→`ReviewResult`에 고정, 입력 `docs_dir/*.json`, `openai` 오류 판별 | `scoring_v2`는 전부 옛 과제 전용 → 이름 단위 발음 오류율·DER·PER·후보 포함률 채점기 신규 |
| 의존성 | Python 3.11, FastAPI, SQLAlchemy·Alembic·psycopg, camel-tools 1.6.0(torch·transformers 동반), fastmcp | — | 디아크리타이저(CATT `catt-tashkeel` Apache-2.0, libtashkeel MIT, CAMeL GLF disambiguator), 엔진 SDK(azure-cognitiveservices-speech, boto3 Polly, google-cloud-texttospeech, elevenlabs), 오디오 I/O(soundfile), 선택으로 음소 인식·강제 정렬. 음성 의존성은 현재 0 |
| 보관·보류 | 서류 검수 경로(그래프 C0~C3·M1·M2, `archive*`, 업로드 화면, OCR, 묶음 검수)는 코드·테스트·골든 유지 | — | — |

## 4.4 새 모듈 [제안]

| 모듈 | 하는 일 | 재사용 |
| --- | --- | --- |
| `pronounce/detect.py` | 발화 텍스트에서 고유명사 후보 구간을 찾는다: 사전 키 조회(정규화 아랍어 1~4단어 창), 호칭·역할 규칙(السيد·الشيخ·شركة·بنك 뒤), 선택으로 경량 NER | `text.py` |
| `pronounce/candidates.py` | 이름 하나의 독법 후보: 사전 → CAMeL diac → CATT → LLM(자음 골격 검사) → 라틴 역음역 필터. 출처·점수 붙임 | `analyzer.py`, `romanize.py`, `exp001` 필터 |
| `pronounce/evidence.py` | 근거 검사: 라틴 표기 일치(`match_spelling`·`strict_key`), 녹음 정렬 마진(격자 제약 CTC, 선택), 사람 확정 기록 | `romanize.py`, `reconcile.verify_evidence` 패턴 |
| `pronounce/diacritizer.py` | 결정적 디아크리타이저 어댑터(CATT-EO ONNX / libtashkeel / CAMeL GLF), 이름 구간만, 1·2위 마진 반환, 자음 골격 검사 | — |
| `pronounce/engines/*.py` | 엔진 어댑터: 디아크리틱스 아랍어·IPA → Azure SSML(IPA, ar-SA PLS), Polly SSML(IPA/X-SAMPA, ar-AE 음소표), Google `customPronunciations`, ElevenLabs alias·v4 인라인 IPA, 디아크리틱스 텍스트. 지원 매트릭스 설정 | — |
| `pronounce/g2p.py` | 디아크리틱스 아랍어 → IPA(Halabi phonetiser·SawtArabi espeak-ng 수정 규칙 참고), 엔진별 phone set 매핑 | — |
| `pronounce/service.py` | `/v1/pronounce` 흐름: detect → lookup → diacritize → engine → log. 확신 등급 | `web/app.py` 동기 엔드포인트 패턴 |
| `pronounce/queue.py` | 사후 확정 큐: 저확신 발화 저장, 후보 합성 클립, 확정 반영 | `name_dictionary` |
| `experiments/exp006.py`, `scoring_tts.py` | 엔진 × 입력 형식 조건 실행, 합성 파일 저장, 청취 평가표 생성, ASR 왕복·강제 정렬 채점 | `harness.py` |

## 4.5 API 초안 [제안]

| 메서드·경로 | 입력 | 출력 | 경로 |
| --- | --- | --- | --- |
| `POST /v1/pronounce` | `{text, customer_id, entity_ids?, engine, voice, dialect?}` | `{engine_text (SSML 또는 텍스트), names: [{span, arabic, reading, phonemes, confidence, source}], latency_ms, versions}` | 실시간, 동기, LLM 없음 |
| `POST /v1/names/import` | CSV·JSON 이름 목록(아랍어, 라틴 표기?, entity_id?, 역할?, 녹음 참조?) | 작업 ID, 후보 생성 결과 | 오프라인 |
| `GET /v1/names/queue` / `POST /v1/names/{id}/confirm` | — / `{reading, source: human|recording|latin, previous?}` | 큐 항목(후보·합성 클립 URL·근거) / 사전 항목 | 오프라인 |
| `GET/POST/DELETE /v1/dictionary` | 기존 API에 `pronunciation`·`phonemes`·`source` 추가 | 사전 항목 | 공통 |
| `GET /v1/engines` | — | 엔진·모델·로케일별 지원 매트릭스(실험으로 채운 값과 날짜) | 공통 |
| `GET /v1/usage`, `/health` | 기존 | 기존 + 디아크리타이저·사전 버전 | 공통 |

## 4.6 DB 변경 [제안]

- `name_dictionary`에 `pronunciation TEXT`, `phonemes TEXT`, `source TEXT`(`human`·`recording`·`latin`·`import`), `engine_overrides JSONB`, `previous_value JSONB`, `english_name`을 NULL 허용으로(Alembic 0005).
- 새 표 `utterance_log`(고객, 텍스트 해시, 이름별 독법·확신·출처, 엔진·음성·버전, 지연, 시각), `pronounce_queue`(저확신 이름, 후보, 합성 클립 참조, 상태, 확정 결과), `recordings`(참조·동의 기록·역내 저장 위치·파생 독법. 원본 보관 여부는 설정).
- 고객 격리는 기존 `customer_id` 조건에 더해 Postgres RLS를 검토한다(`tenant_id` + `FORCE ROW LEVEL SECURITY` + `SET LOCAL app.tenant`, OWASP LLM08 권고 [문헌○]).

## 4.7 엔진 지원 매트릭스 (문서 기준, 2026-10-23. EXP-006으로 채운다)

| 엔진 | 걸프 로케일·음성 | 디아크리틱스 입력 존중 | `<phoneme>` | 저장 사전 | 스트리밍 제약 | 출처 |
| --- | --- | --- | --- | --- | --- | --- |
| Azure Speech | ar-SA Zariyah·Hamed, ar-AE Fatima·Hamdan(표준 neural, HD 아랍어 없음) | [미확인] | IPA(SAPI는 아랍어 없음), 모르는 phone은 HTTP 400 | PLS ≤100KB, 로케일당 1개, 15분 캐시. **ar-SA Yes, ar-AE No** | 텍스트 스트리밍 모드 SSML 불가 | MS Learn [문헌○] |
| Amazon Polly | ar-AE Hala·Zayd(neural, 아랍어·영어 이중언어), arb Zeina(standard) | [미확인] | IPA·X-SAMPA, neural·standard·long-form(generative 부분). **ar-AE 음소표 공개** | PLS, 계정당 100개·각 40,000자·호출당 5개, 크기가 지연에 영향 | — | AWS 문서 [문헌○] |
| Google Cloud TTS | ar-XA만(걸프 로케일 없음), Chirp 3 HD | [미확인] | `<phoneme>` 지원 로케일 21개에 아랍어 없음. Chirp 3 HD `customPronunciations`(IPA·X-SAMPA, 여러 단어 구문)에 ar-XA 포함 [미확인] | 없음(요청 단위) | 스트리밍 요청 SSML 불가 | Google 문서 [문헌○] |
| ElevenLabs | Multilingual v2·Flash v2.5·v3·v4 아랍어 포함 | [미확인] | `eleven_flash_v2`만 태그, v3/v4는 SSML 없음, v4는 본문 `/IPA/`(음성·문장에 따라 다름). 다른 언어 IPA는 v4 필요. 문서 간 불일치 | PLS 사전(phoneme은 v4·flash_v2·v3, alias는 전부). WebSocket은 청크 안에서만 매칭 | 위와 같음 | ElevenLabs 문서 [문헌○] |
| OpenAI | 아랍어 포함, "영어 최적화". gpt-4o-mini-tts는 deprecated 표시(2026-10-23 확인) | [미확인] | 없음 | 없음 | — | OpenAI 문서 [문헌○] |
| 오픈 모델(Habibi, Chatterbox 등) | Habibi 12개 이상 방언 | Habibi는 디아크리틱스 없이 합성 → 존중 여부 [미확인] | 없음 | 없음 | — | arXiv 2601.13802 [문헌○] |

## 4.8 저장소 구조와 기술 스택

- 저장소 구조, 모듈 계층, 실제 API·DB 표(서류 검수 제출본)는 [보관본 4.8절](archive/document-review/architecture.md)에 있다. 코드가 바뀌지 않았으므로 그 표가 지금 코드다.
- 기술 스택(유지): Python 3.11, uv, FastAPI, SQLAlchemy·Alembic·Postgres, LangChain·LangGraph(오프라인 경로만), FastMCP, camel-tools 1.6.0(측정·오프라인), pytest·ruff·mypy, Docker Compose.
- 추가 후보 [제안]: `catt-tashkeel`(Apache-2.0, ONNX export), libtashkeel(MIT, Rust·Python·WASM, 확신 0.95 미만이면 격어미 sukoon 폴백), CAMeL BERT disambiguator GLF 모델(걸프 방언, GPU 기본), 엔진 SDK 4종, `soundfile`, 선택으로 wav2vec2-phoneme·Montreal Forced Aligner(녹음 정렬·PER 채점).
- 실행 환경: 실시간 경로는 CPU 추론을 전제로 한다(ONNX). GPU는 오프라인 후보 생성·녹음 정렬에만.

## 4.9 코드 대조

- 2026-10-23 현재 코드와 문서의 관계: **코드는 서류 검수 제출본이고 이 문서는 TTS 계획이다.** 4.3절 표가 둘의 대응이다. 새 모듈(4.4절)·API(4.5절)·DB(4.6절)는 하나도 구현되지 않았다.
- 코드가 바뀌면 이 절을 "구현된 것 / 계획과 다른 것"으로 갱신하고 [changelog.md](changelog.md)에 적는다.
