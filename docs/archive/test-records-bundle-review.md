# 묶음 검수 테스트 기록 (보류 기능)

- 보관 사유: 서류 묶음 검수(ADR-018)는 ADR-021로 추가 개발을 멈춘 기능이라 제출본 테스트 기록에서 뺐다. 코드와 자동 테스트(`tests/test_bundle_*.py`)는 그대로 있고 통과한다.
- 원래 위치: [`docs/과제2-테스트-기록.md`](../과제2-테스트-기록.md) 5절(2026-10-21 기록). 2026-10-22에 옮겼고, 내용은 고치지 않았다(캡처 파일 이름을 링크로 바꾼 것만). 본문의 F-12·F-15는 원래 문서 2절의 항목이다.

## 5. 묶음 검수 (단계 2, 2026-10-21, 14단계 가이드 1~12·14단계, ADR-018)

실행은 가짜 모델 + 로컬 Postgres(`alembic upgrade head`로 0002 적용) + `tashkeel serve --port 8011`. 화면 캡처는 Chrome 확장이 연결되지 않아 headless Chrome(`--screenshot`)으로 딥링크(`#bundle?sample=…&run=1`)를 열어 찍었다.

### 5.1 기능별 (가이드 단계 → 입력 → 예상 → 실제)

| # | 가이드 | 입력 | 예상 | 실제 | 결과 |
| --- | --- | --- | --- | --- | --- |
| B-1 | 1 문서 읽기 | `data/bundles/sample_bundle.json` / 없는 경로 / `{not json` | 아랍어 그대로 읽힘 / `BundleNotFound` / `InvalidBundle`(JSON 오류 메시지) | 그대로. 두 예외는 서로 다른 클래스이고 둘 다 `InputError` | 통과 |
| B-2 | 2 스키마 | `status: "maybe"`, `evidence: "none"`, 모르는 키, 빈 `documents`, 중복 `document_id` | 검증 오류 | `ValidationError` / `InvalidBundle("묶음 구조 오류: … duplicate document_id")` | 통과 |
| B-3 | 3 이름 추출 | `الاسم: مسلم` / 칸 3개(개인·기관·회사) / 라벨 없음 / `الاسم: مسلم \| Name: Musallam` | 1건 / 3건 순서대로(종류 person·organization·organization) / 빈 목록 / 아랍어 칸만 1건, 영문 칸은 근거 출처 | 그대로. `رقم الهوية:`처럼 모르는 라벨은 무시 | 통과 |
| B-4 | 4 근거 검색 | 계약서(e1) + 신분증(e1, Name: Musallam) + 신분증(e2, 같은 아랍어, Name: Muslim) | e1 근거 1건(id1/Musallam)만. e2는 아랍어가 같아도 제외 | 그대로. ID 없는 항목·같은 서류는 근거 없음 | 통과 |
| B-5 | 5 인용 검증 | 올바른 근거 / 없는 서류 / 다른 구간 / 원문에 없는 인용 / 인용에 없는 영문 | 통과 / `document_not_found` / `segment_not_found` / `quote_not_in_segment` / `name_not_in_quote` | 그대로. 대소문자·공백은 무시, 철자는 무시하지 않음 | 통과 |
| B-6 | 6 판정 | 샘플 묶음(개인 Muslim vs 신분증 Musallam, 회사 Gulf Trading Company = 등기) | 개인 대기 "번역 표기 불일치", 회사 확정 "근거 일치" | `person pending translation_mismatch evidence='Musallam' (id_001/s01)`, `organization confirmed evidence_match` | 통과 |
| B-7 | 6 판정 규칙 6종 | 근거 없음 / 충돌(Musallam·Musalam) / 불일치 / 번역 없음 / 검증 실패만 / 일치(`  musallam `) | 대기·대기·대기·대기·대기·확정(원래 표기 보존) | 그대로. `Mohamed` vs `Mohammed`는 대기 + 제안 `Mohammed` | 통과 |
| B-8 | 7 사전 | 고객 c2 항목 / 같은 고객·다른 대상 e9 / 같은 고객·같은 대상 e1 / `customer_id` 없는 묶음 | 적중 안 함 / 안 함 / `dictionary_match` / 사전 안 봄 | 그대로 | 통과 |
| B-9 | 7 저장(Postgres) | 같은 묶음 2번 `POST /v1/bundles/review`, 대기 항목 닫기, 서버 재기동 | 덮어쓰기, `/v1/dictionary` 201, 재기동 뒤 `/items` 2건 그대로, 근거 없는 다음 묶음은 `dictionary_match` | 그대로(`db` 마커 테스트). 표 `bundles 1, review_items 2, name_dictionary 1` | 통과 |
| B-10 | 8 API | `POST /v1/bundles/review` 샘플 → `/items` → `/pending` → `/v1/bundles` | 200 `counts {confirmed 1, pending 1}`, items 2, pending 1(`reason_label "번역 표기 불일치"`), 최근 목록 | 그대로 | 통과 |
| B-11 | 9 LLM 연결 | 라벨 칸 없는 계약서(`حضر <이름> بصفته طرفاً أول.`) + 신분증, 가짜 모델이 이름 토큰을 `proper_noun` 보류로 냄, C1 | 서류별 작업 2개 → 합류 항목 1건 `no_translation` + 제안 = 신분증 표기, 대상 ID·종류 붙음, 저장소에도 반영 | 그대로(개인·회사·기타 3종류). 가짜 모델이 `adopt`로 표기를 내면 근거와 비교해 `evidence_match` / `translation_mismatch` | 통과 |
| B-12 | 9 라벨 우선 | 샘플 묶음(라벨 칸 있음)에 LLM C2 | LLM 항목은 라벨 칸 구간에서 쓰지 않음 → 결과는 라벨 경로와 같음 | `counts {1, 1}`, `:llm` 항목 없음 | 통과 |
| B-13 | 10 형태소 | — | 기존 C2 툴·MCP 그대로 | 변경 없음(F-12·F-15) | 통과 |
| B-14 | 11 범위 색인 | `BundleIndex.from_documents(docs, entity_id="e1")` | e1 구간만 색인, 결과에 `document_id`·`segment_id`, e2 표기는 안 나옴 | 그대로 | 통과 |
| B-15 | 12 MCP | `search_bundle(documents=샘플, entity_id=person_001, arabic_name=مسلم)` / `entity_id=nope` / 리소스 `document://synthetic/bundles/dev[/dev_person_match]` / 없는 묶음 | 근거 `[(id_001, Musallam, valid)]` / `error "unknown entity id"` / 목록·묶음(gold 없음) / 오류 | 그대로. 툴 목록 `analyze_tokens, search_bundle` | 통과 |
| B-16 | 14 화면 | 서류 묶음 탭, 샘플 `dev_person_conflict` 실행 | 전체 결과 → 대기 목록 → 항목 비교(원문 RTL·번역·근거 2건 검증 통과) → 닫기 입력란 | 캡처 [screen-bundle_conflict.jpg](../images/screen-bundle_conflict.jpg) | 통과 |
| B-17 | 14 화면 | 샘플 `dev_organization_match` | 확정 1 대기 0, 회사 항목이 개인과 같은 표 형식 | 캡처 [screen-bundle_org_match.jpg](../images/screen-bundle_org_match.jpg) | 통과 |
| B-18 | 14 화면 LLM | 샘플 `dev_person_model_error` + LLM C2(가짜 모델) | 서류별 진행 표시 → done | 캡처 [screen-bundle_llm.jpg](../images/screen-bundle_llm.jpg). 가짜 모델(연습 응답)은 분석기가 아는 이름을 항목으로 내지 않아 합류 항목 0건. 합류 자체는 B-11의 스크립트 응답으로 확인 | 통과 |
| B-20 | 4·5 여권 칸·MRZ | `Surname: AL QAHTANI \| Given Names: FATMA AHMED` / MRZ `P<SAUAL<QAHTANI<<FATMA<AHMED<<…` / 인쇄 칸 + MRZ가 같은 여권에 / 하이픈·39자 초과 이름 | 영문 표기 `FATMA AHMED AL QAHTANI` 하나 / 해독값 같음 / 인쇄 칸만 근거 / 해독값이 달라 대기 | 그대로(`test_bundle_mrz.py` 6건) | 통과 |
| B-21 | 14 KYC 묶음 | `tashkeel make-bundles` → 등기 + 여권 2 + 정관 사례 8개 × dev·eval | 정답과 일치, 같은 이름의 다른 주주는 연결 안 함, MRZ만 있는 여권은 MRZ 구간이 근거 | 그대로(`test_bundle_eval_kyc.py` 21건). dev `mrz_only`의 관리자 이름은 39자를 넘어 잘리므로 정답대로 대기 | 통과 |
| B-22 | 8 파일 업로드 | `POST /v1/bundles` multipart: 샘플 묶음 JSON / `contract.txt`(2줄) + `id.txt`(`Name: Musallam`) + `customer_id` | 201 확정 1 대기 1, 서류 3개 / 201 서류 2개(줄마다 구간), 항목 1건 `no_entity_id` | 그대로 | 통과 |
| B-23 | 8 묶음 SSE | `POST …/reviews?condition=C1` 뒤 `GET …/reviews/{id}/events` / 끝난 뒤 다시 | `start`(서류 3개 작업) → `document`(queued·node·done) → `done`(counts) / 재생 뒤 바로 `done` | 그대로 | 통과 |
| B-24 | 14 화면 | 샘플 `dev_kyc_passport_mismatch` 실행, 파일 업로드 입력란 | 확정 2(회사·관리자) 대기 1(소유자, 여권·정관 근거 2건 통과, 제안 = 여권 표기) | 캡처 [screen-bundle_kyc.jpg](../images/screen-bundle_kyc.jpg). 업로드 버튼은 파일을 고르기 전에는 비활성. 진행 표시는 SSE `document` 이벤트로 갱신(끊기면 폴링) | 통과 |
| B-19 | 14 평가 사례 | `tashkeel make-bundles` → 사례 9 × 종류 3(60파일) | 종류와 무관하게 정답과 일치 | `test_bundle_eval.py` 27건 + 종류 무관성 1건 통과. `model_error`는 B-11·E-10으로 | 통과 |

### 5.2 예외 (가이드 사례)

| # | 예외 | 재현 | 예상 | 실제 | 결과 |
| --- | --- | --- | --- | --- | --- |
| E-8 | 묶음 구조 오류 | `POST /v1/bundles/review {"bundle_id":"x","documents":[]}` / 본문이 JSON이 아님 | 400 `kind input` "묶음 구조 오류" / 422 | 그대로 | 통과 |
| E-9 | 없는 묶음 | `GET /v1/bundles/nope/items`, `/pending`, `/v1/bundles/samples/nope`, `POST /v1/bundles/nope/reviews`, `/v1/dictionary` 없는 항목 | 404 | 그대로 | 통과 |
| E-10 | LLM 호출 실패 | 가짜 모델이 `openai.APIConnectionError`를 던짐, 묶음 LLM 검수 C1 | 이름 미검출이 아니라 실행 오류: 서류마다 `model_error` 항목, `errors`에 서류 2개 | `detail "attempt N: APIConnectionError: …"`, `errors {contract_001, evidence_001}` (3종류) | 통과 |
| E-11 | 동명이인·같은 이름의 다른 회사 | `namesake` 사례(같은 아랍어, 다른 대상 ID) | 연결하지 않음, 근거 0건, 제안 없음 | 그대로(3종류) | 통과 |
| E-12 | 다른 고객 문서에만 근거 | `other_customer` 사례(고객 b 묶음에서 확정, 그 표기를 고객 b 사전에 등록) | 고객 a 묶음은 `no_evidence` | 그대로 | 통과 |
| E-13 | 원문에 없는 인용 | `bad_quote` 사례의 `claimed_evidence` | `quote_not_in_segment`, 그 근거만 있으면 `validation_failed` | 그대로 | 통과 |
| E-14 | 추출 실패 | `الاسم: ` (빈 값), `الاسم: 12345` | `extraction_error empty_value / value_not_arabic`, 판정 `extraction_failed` | 그대로 | 통과 |
| E-15 | DB 불통 | `DATABASE_URL`이 닿지 않는 값으로 기동 뒤 `POST /v1/bundles/review` | 503 `kind config` | 그대로 | 통과 |
| E-17 | 업로드 파일 오류 | `.pdf` / UTF-8 아닌 `.txt` / `{not` JSON / 묶음 JSON + 서류 파일 함께 / `entities=[1]` / `{"segments": "x"}` / 파일 없음 | 400(형식) / 400(UTF-8) / 400(JSON 오류 줄 번호) / 400 / 400 / 400(구조 오류) / 422 | 그대로 | 통과 |
| E-16 | 사전 등록 불가 | `customer_id` 없는 묶음 / 대상 ID 없는 항목으로 `POST /v1/dictionary` | 400 | 400 "customer_id가 없는 묶음은 사전에 등록할 수 없습니다" | 통과 |

### 5.3 하지 않은 것

- 실제 모델로 묶음 LLM 경로 실행(EXP-002 보류 중, 사용자 결정으로 이번에 안 함).
- 벡터 검색의 pgvector 이전, 서류 종류별 우선순위, 인증, 업로드 서류에 대상 ID를 붙이는 입력, 멀티 에이전트(가이드 13단계). 파일 업로드·묶음 SSE·KYC 묶음은 같은 날 뒤에 더했다(B-20~B-24, E-17).
- Chrome 확장 캡처(연결 안 됨). headless Chrome으로 대체했고 클릭 흐름(항목 선택·등록 버튼)은 캡처하지 않았다.
