# Tashkeel Check

번호: (기재) · 성함: (기재)

아랍어 서류를 영어로 읽어야 하는 사람을 위한 검수 도구다. 아랍어는 단모음을 적지 않아 같은 철자의 이름이 여러 가지로 읽힌다(مسلم → Muslim 또는 Musallam). 번역 LLM은 이런 자리를 표시 없이 하나로 정해 버릴 수 있고, 아랍어를 모르는 읽는 사람은 그런 선택이 있었다는 사실조차 모른다. 이 도구는 문서를 넣으면 고유명사마다 읽기 후보를 문서 안 근거와 함께 보여 주고, 근거가 없으면 확정하지 않고 보류한다. 사람이 후보를 골라 확정하면 회사 사전에 저장되어 다음 서류의 같은 이름은 처음부터 확정으로 나온다.

## 1. 진행 사항

### 선택한 과제: 과제 2

제공 프로젝트(`all_total_vue_student`: FastAPI + Vue 채팅 UI + LangGraph + MCP + SQLite)의 구조를 재활용해 새 서비스를 만드는 과제다. 챗봇 대신 문서 검수 서비스를 만들었고, 제공 프로젝트에서는 서버·화면·MCP·재시도 패턴을 가져오고 저장소는 SQLite 대신 Postgres를 썼다([ADR-012](docs/adr/ADR-012.md)). 파일 대응표는 [부록 B](#부록-b-제공-프로젝트와의-대응)에 있다.

### 과제 주제

걸프(사우디·UAE)에 진출한 외국 중소기업이 아랍어 서류를 내부 검토용으로 읽을 때, 고유명사의 읽기가 갈리는 자리를 드러내고 근거 없이 확정하지 않는 서비스. 사람이 확정한 표기만 회사 사전에 쌓아 다음 서류에서 재사용한다([ADR-021](docs/adr/ADR-021.md)).

### 주요 Task

| 순서 | Task | 결과 |
| --- | --- | --- |
| 1 | 측정 장치: LangGraph 그래프(입력 → 분석기 → 에이전트 → 검증 → 대조 → 출력)와 조건 C0~C3, 합성 시험지 생성기, 자동 채점 | 골든 160건으로 동작 고정 |
| 2 | EXP-001: 형태소 분석기(CAMeL Tools)가 실제 걸프 인명 3,023개에서 후보를 내는 비율 | 50.2%(기준 50%를 겨우 넘음) |
| 3 | EXP-002: 쉬운 합성 문서에서 조건 비교 | 반복 1회에서 C1~C3 모두 만점이라 보류 |
| 4 | EXP-003: 동명이인·함정 근거·긴 문서가 섞인 어려운 합성 문서 70개, 99% 기준 | 판정 `stop`. 지시문만 준 C1이 99.93%, 분석기 조건과 차이 없음 |
| 5 | 서비스화(단계 1.5): FastAPI API·SSE 진행 표시·Vue 화면·Postgres·MCP 서버와 클라이언트 | 기능 16건·예외 7종 기록 |
| 6 | 서류 묶음 검수(단계 2): 같은 대상 ID가 붙은 다른 서류의 영문 칸만 근거로 쓰고 정확히 일치할 때만 확정 | 합성 묶음 사례 17개로 테스트 |
| 7 | 완제품 패키지: API 키 인증·고객 분리·사용량, 멀티 에이전트 틀 M1, Docker Compose | 스모크 PASS |
| 8 | 방향 전환(ADR-021): 파일 업로드(.txt/.md/.pdf/이미지) → 이름 후보 → 클릭 확정 → 회사 사전 | 실제 모델로 확정 → 재사용 확인 |

Task 4의 결과가 Task 8의 이유다. 분석기를 주지 않아도 지시문만으로 99%를 넘었으므로, 제품의 가치를 "읽기 정확도"가 아니라 "근거 찾기·검증·기록·재사용"에 두는 쪽으로 좁혔다. 분석기는 측정 지표용으로만 남았다.

## 2. 사용한 기술 요소

| 기술 요소 | 어디에 쓰였나 | 상태 |
| --- | --- | --- |
| LangGraph · LangChain | `graph.py`의 6노드 그래프. 구조화 출력(`AgentOutput`)이 형식에 안 맞으면 agent 노드를 1회 재시도하고, 처분 누락과 지표 계산은 LLM이 아니라 코드가 한다 | 구현·측정 |
| Multi-Agent | `multi_agent.py`의 M1: 번역자 → 격리된 검증자(번역자 출력을 못 봄) → 규칙 중재자. `MULTI_AGENT=true`일 때 조건 `M1` | 틀만 구현, 가짜 모델로 테스트. 실제 모델 비교는 안 함 |
| MCP | `mcp/server.py`(FastMCP, stdio): 툴 `analyze_tokens`·`search_bundle`, 리소스 `document://synthetic/...`, 프롬프트 `review_instructions`. `mcp/client.py`는 연결 1개를 lock으로 공유하고 `with_retry`로 재시도한다. `USE_MCP_TOOLS=true`면 C2의 분석 툴 호출이 MCP로 간다 | 구현, 서버 다운 시 503 처리까지 테스트 |
| RAG | `rag/bundle.py`의 `BundleIndex`: 같은 대상 ID의 구간만 색인해 후보 힌트로 쓴다. 근거로는 쓰지 않는다 | 구현(메모리 색인, pgvector 이전은 안 함) |
| 의존성 주입 | `Settings` → `build_runtime()` → `Runtime(model, analyzer, dictionary, ocr)`. 모델은 `make_model(fake=...)`로 진짜·가짜를 바꾸고, OCR(`OcrBackend`)과 사전(`DictionaryLookup`)은 `Protocol`이라 테스트에서는 가짜를 넣는다 | 구현 |
| LangSmith | `runner.py`의 `@traceable`. `LANGSMITH_API_KEY`가 있으면 켜지고 없으면 추적만 꺼진다 | 연결은 되어 있으나 현재 `.env`의 키가 401로 거부되어 최근 실행의 추적은 없다 |
| 모듈화 | `graph`(흐름) / `prompts`·`schemas`(LLM 입출력) / `analyzer`·`tools`(분석기) / `reconcile`·`scoring_v2`(채점) / `bundle/`(묶음 규칙) / `ocr/`(입력) / `dictionary_apply`(사전 덧씌움) / `web/`(API·작업·DB) / `mcp/` / `experiments/`. 위쪽이 아래쪽을 import하고 반대는 없다 | [architecture.md 4.11](docs/architecture.md) |
| 단위 테스트 | pytest 512개 통과(8 skip). 골든 스냅샷 160건은 리팩토링 전후 결과가 같은지 보는 기준값이라 고치지 않는다([ADR-013](docs/adr/ADR-013.md)). 마커 `db`(Postgres 있을 때)·`live`(실제 모델)·`camel`. ruff·mypy·pre-commit | CI와 같은 검사 통과 |
| 저장소·배포 | Postgres + Alembic 3단계(문서·작업·실행·이름 항목, 묶음·검수 항목·사전, 고객·사용량). API 키 인증. Docker Compose(앱 + Postgres) | 스모크 PASS, 이미지 10.1 GB |
| 입력 경로 | `ocr/extract.py`: .txt/.md 그대로, .pdf는 `pypdf` 텍스트 층 먼저, 아랍어가 없으면 OCR, 이미지는 OCR. 백엔드는 `none`과 무료 API `ocrspace` | 추출 로직은 테스트, OCR 실제 호출은 키가 없어 안 함 |

### 기존 기능의 개선 사항

- 지시문 p0 → p1. p0는 "모호하면 표시하라"는 지시였고, p1은 근거의 원칙(같은 문서 안의 영문 표기만, 글자 그대로 인용, 다른 사람의 표기는 근거가 아니다)을 적었다. 같은 입력에서 엄격 정확도 0.9266 → 0.9993 (3절).
- 서비스 기본값을 측정한 설정으로 맞췄다. 전에는 화면·API가 C3·p0로 돌았고, 측정은 C1·p1로 했다. 지금은 둘이 같다.
- 회사 사전이 묶음 검수 밖에서도 돈다. 전에는 대상 ID가 있는 묶음에서만 조회·등록이 됐다. 지금은 단일 문서 결과 위에 코드가 사전을 덧씌운다(`dictionary_apply.py`). 보류 + 적중이면 사전 확정, 문서 근거와 사전이 다르면 충돌로 표시하고 확정하지 않는다.
- 실험 실행 장치가 중간에 멈추고 재개된다(`plan.json`·`runs.jsonl`·`--resume`). API 오류는 완료로 치지 않는다. EXP-003 실행 중 langchain이 감싼 속도 제한 오류를 API 오류로 못 알아보던 버그를 고쳤다([TS-004](docs/troubleshooting.md)).

### 추가 구현

- `POST /v1/reviews/upload`: 파일 하나를 올리면 추출 → 구간 분할 → 검수를 한 번에 한다. `POST /v1/extract`는 추출만.
- 사전 API: `POST /v1/dictionary`(사람이 후보를 누를 때만 등록), `GET /v1/dictionary`, `DELETE /v1/dictionary/{id}`.
- 결과 응답에 `tokens`(토큰 위치)와 `dictionary`(덧씌움)를 더해 화면이 문자열 치환이 아니라 토큰 위치로 이름을 감싼다. 같은 이름이 두 번 나와도 정확하다.
- 화면을 두 페이지로 나눴다. `#/upload`는 누르면 로컬 파일 선택이 열리고, `#/result/{job_id}`는 원문·번역에 이름을 색으로 표시한다(주황 보류, 초록 문서 근거 확정, 파랑 사전 확정, 빨강 충돌). 이름을 누르면 후보가 토글로 열리고, 후보를 누르면 바로 저장된다.

### 화면 캡처

파일 넣는 페이지. 점선 상자를 누르면 로컬 파일 선택 창이 열린다.

![파일 넣는 페이지](docs/images/screen-upload.jpg)

결과 페이지에서 주황(보류) 이름 نوال을 누른 상태. LLM 후보 Nawal·Noual과 직접 입력 칸이 열렸다.

![후보 토글](docs/images/screen-result-candidates.jpg)

단계 1.5 화면(검수 결과와 구간별 원문·번역)과 묶음 검수 화면은 `docs/images/screen-dev005-c2-*.jpg`, `screen-bundle_*.jpg`에 있다.

### 최종 실행 화면

Nawal을 확정한 뒤 같은 문서를 다시 넣은 결과. 모델 출력은 여전히 보류인데 사전이 덧씌워져 처음부터 파랑(사전 확정)으로 나오고, 번역문의 `[Nawal/Noual]`이 `Nawal`로 바뀌었다.

![재사용](docs/images/screen-result.jpg)

## 3. 선택 사항: 같은 입력에서 개선 전후 비교

### 지시문 p0 → p1 (EXP-003, 합성 문서 synthetic-hard eval 70개, 이름 부분 1,457개)

모델은 `gpt-6.1-sol`, 처리 등급 flex, 동시 16개, 반복 1회. 5조건 × 70문서 = 350회, 합계 3.39M 토큰, 약 21분, 약 $10[추정]. 엄격 정확도는 철자까지 맞아야 하고, 안전 정확도는 "말없이 틀리지 않음"만 본다. 문서당 비용은 기본 단가(입력 $2·출력 $10/100만 토큰)로 계산한 추정값이다.

| 조건 | 엄격 | 안전 | 문서당 시간 | 문서당 토큰 | 문서당 비용[추정] | 형식 실패 재시도 |
| --- | --- | --- | --- | --- | --- | --- |
| C0 지시 없는 번역 | 0.5546 | 0.5546 | 7초 | 765 | $0.004 | 2 |
| C1p0 옛 지시문 p0 (개선 전) | 0.9266 | 0.9300 | 69초 | 7,247 | $0.060 | 0 |
| C1 지시문 p1 (개선 후) | 0.9993 | 1.0000 | 62초 | 6,635 | $0.053 | 0 |
| C2 p1 + 분석 툴 | 0.9979 | 1.0000 | 59초 | 15,000 | $0.073 | 0 |
| C3 p1 + 분석 블록 | 0.9993 | 1.0000 | 86초 | 18,782 | $0.103 | 0 |

![EXP-003 비교](docs/images/exp003-compare.jpg)

- p0 → p1 차이: 엄격 +0.073(문서 단위 부트스트랩 95% 구간 0.049~0.097). p0의 오류 107건은 다른 사람의 표기를 근거로 쓴 것 49건, 그 사람 표기로는 부족한데 확정한 것 43건, 회사명·이메일 같은 함정 10건, 보류 5건이다. p1의 오류는 1건이고, `ASA'AD`와 MRZ의 `ASAAD`를 다른 철자로 보고 보류한 것이다.
- 분석기를 준 C2·C3는 C1과 차이가 없다(C1 − C3 = 0). 토큰은 2~3배 든다.
- C0는 절반 가까이 말없이 찍었다(silent_pick 626건). C0의 재시도 2회는 flex 용량 부족 429 때문이고 형식 실패가 아니다.
- 한계: 합성 문서 결과이고, 시험지·정답 규칙·지시문을 같은 작업자가 설계했다. 자동 판정 오류의 사람 확인(`errors.csv`)은 아직이다. 자세한 내용은 [EXP-003](docs/experiments/EXP-003.md).

### 회사 사전 적용 전후 (같은 문서 dev_005, 실제 모델, 조건 C1·p1)

| | 1회째(사전 비어 있음) | 2회째(نوال → Nawal 확정 뒤) |
| --- | --- | --- |
| 이름 항목 | 8개: 보류 7, 문서 근거 확정 1 | 8개: 보류 6, 사전 확정 1, 문서 근거 확정 1 |
| 번역문 | `[Nawal/Noual] [Muammar/Ma'mar] …` | `Ms. Nawal [Muammar/Ma'mar] …` |
| 시간 · 토큰 | 76초 · 5.2k | 새 LLM 호출(사전은 LLM 입력에 들어가지 않고 코드가 결과 위에 덧씌운다) |
| 캡처 | `screen-result-candidates.jpg` | `screen-result.jpg` |

## 4. 느낀 점 및 향후 개선 사항

### 느낀 점

- 분석기가 도움이 될 거라는 가정으로 시작했는데, 재 보니 지시문이 거의 전부였다. 쉬운 시험지(EXP-002)에서 천장에 닿아 어려운 시험지를 다시 만들고 99% 기준을 세웠는데, 거기서도 지시문만으로 넘었다. 기능을 먼저 만들었으면 쓸모없는 부품 위에 제품을 올렸을 것이다. 측정을 먼저 한 것이 비용을 아꼈다.
- 99%라는 숫자는 시험지를 만든 사람이 지시문도 쓴 결과라서 그대로 믿기 어렵다. 실제 서류로 재기 전까지는 "합성 문서 기준"이라고 붙여 두는 것 말고 방법이 없었다.
- 실험 장치에 들인 시간(재개, 토큰 예산, 사전 등록한 판정 코드)은 처음엔 과하다고 느꼈는데, 실행 중 속도 제한 오류가 "완료"로 기록되는 버그를 잡을 수 있었던 건 그 장치 덕분이었다.
- 골든 스냅샷을 고치지 않는다는 규칙 때문에 기본값을 바꿀 때 테스트가 깨졌다. 실험 경로와 제품 경로를 설정으로 분리해 두니 둘 다 보존할 수 있었다.
- LLM 출력에서 같은 이름의 두 등장이 한 항목으로 묶여 나오는 것처럼, 화면에 올려 보기 전엔 몰랐던 형태가 있었다. API 테스트만으로는 안 보였다.

### 향후 개선 사항

1. 자기 회사 표기 감시: 자기 회사를 거래처 0번으로 등록하고, 서류의 회사명·등기번호·세금번호가 등록 표기와 다르면 경고한다. 근거 규칙의 출처를 찾은 뒤에 수치를 쓴다.
2. OCR 실제 호출 1회(키가 생기면, 연결 확인만)와 무료 등급 제한 확인. 무료 API는 파일을 제3자 서버로 보내므로 민감 서류용 로컬 백엔드(Tesseract 등)는 요구가 생기면 끼운다.
3. Postgres에 사전을 두고 실행하는 `db` 테스트와 `docker compose up --build` 재확인.
4. 합성 문서 유형을 중소기업 서류(거래처 계약, 정부 통지, 임대차, 인보이스, 근로계약)로 다시 만드는 생성기 v3.
5. EXP-003 `errors.csv`의 사람 확인과, 공개 이중언어 문서(법령 공식 영역본, 상장사 공시)로 실제 서류 측정.
6. 사전 키를 거래처 단위로 나눌지 결정. 지금은 고객 전체라 같은 철자의 다른 사람이면 잘못 확정할 수 있고, 문서 근거와 다를 때만 충돌로 잡는다.

## 알려진 한계

- 에이전트 실험은 합성 문서로 했다. 실제 서류의 오류율이나 포착률로 일반화하지 않는다.
- 단일 문서에서 근거로 인정하는 것은 같은 문서 안의 영문 표기와 회사 사전뿐이다. 묶음 검수는 같은 대상 ID의 다른 서류를 더 본다.
- 문자 인식 성능은 재지 않았고, 인식 오류와 독법 오류를 구분해 보고하지 못한다.
- 현재 모델은 temperature를 0으로 고정할 수 없어 같은 입력에도 실행마다 결과가 다를 수 있다.
- CAMeL Tools의 형태소 DB(calima-msa-r13)는 GPL v2다. 측정에만 쓰고, 배포 전 법률 검토가 필요하다.

## 부록 A. 실행 방법

Python 3.11과 [uv](https://docs.astral.sh/uv/)가 필요하다.

```bash
uv sync
uv run camel_data -i morphology-db-msa-r13
cp .env.example .env     # OPENAI_API_KEY. 없으면 LLM_BACKEND=fake
```

서비스(파일 넣기 → 후보 → 확정 → 회사 사전):

```bash
LLM_BACKEND=openai AUTH=disabled uv run tashkeel serve --port 8000
# 브라우저 http://127.0.0.1:8000/#/upload  (API 문서 /docs, 상태 /health)
```

```bash
curl -s -F file=@계약서.txt localhost:8000/v1/reviews/upload          # 202 job_id
curl -s localhost:8000/v1/jobs/<job_id>/result | jq '.dictionary'
curl -s -X POST localhost:8000/v1/dictionary -H 'content-type: application/json' \
  -d '{"job_id": "<job_id>", "token_ids": [11, 86], "english_name": "Nawal"}'
curl -s localhost:8000/v1/dictionary
```

가짜 모델(`LLM_BACKEND=fake`)은 비용이 없지만 분석기가 모르는 토큰만 보류로 내서 샘플 문서에서는 이름 항목이 거의 없다. 스캔·이미지는 `OCR_BACKEND=ocrspace OCR_API_KEY=...`가 있어야 읽힌다. Postgres를 쓰려면 `DATABASE_URL`을, MCP 경유는 `USE_MCP_TOOLS=true`를 준다. `run.sh`는 키·포트 검사와 `alembic upgrade head`까지 해 준다.

실험과 CLI:

```bash
uv run tashkeel run --doc data/synthetic/dev/dev_001.json --condition all --fake   # 네 조건 연습 실행
uv run tashkeel exp003 --split dev --fake --repeats 1 --workers 4                  # 연습, 비용 없음
uv run tashkeel exp003-errors                                                       # 사람 확인용 errors.csv
uv run tashkeel make-bundles                                                        # 합성 묶음 생성
```

Docker Compose와 API 키 발급은 [docs/deploy.md](docs/deploy.md), 묶음 검수 API는 [docs/roadmap.md](docs/roadmap.md) 2.3절에 있다.

테스트와 검사:

```bash
uv run pytest -m "not live"      # db 마커는 DATABASE_URL이 닿을 때만, live는 실제 모델 호출
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

## 부록 B. 제공 프로젝트와의 대응

| 제공 프로젝트 파일 | 이 레포 | 상태 |
| --- | --- | --- |
| `web_chat.html` | `src/tashkeel_check/web/static/index.html` (Vue 3 CDN, `#/upload`·`#/result`, SSE 진행 표시) | 구현 |
| `server.py` | `web/app.py`(FastAPI, lifespan, `/health`, SSE), `web/jobs.py`(스레드 실행·이벤트) | 구현 |
| `agent/graph.py` | `graph.py` | 있음 |
| `agent/openai_llm.py`, `fake_llm.py` | `runner.py`의 `make_model`, `fake.py` | 있음 |
| `agent/session_store.py` (SQLite) | `web/db.py`, `web/models.py`, `alembic/` (Postgres) | 구현 |
| `mcp_server.py`, `agent/mcp_client.py`, `agent/retry.py` | `mcp/server.py`, `mcp/client.py`(연결 1개·lock·`with_retry`), `mcp/tools.py` | 구현 |
| `run.sh` | `run.sh`, `Dockerfile`, `docker-compose.yml` | 구현 |

기능별·예외 테스트의 입력·예상·실제는 [docs/과제2-테스트-기록.md](docs/과제2-테스트-기록.md)에 있다.

## 문서

- [PROJECT_PLAN.md](PROJECT_PLAN.md): 현재 상태, 다음 작업, 사용자가 정할 것
- [docs/README.md](docs/README.md): 문서 지도(정의·범위·구조·데이터·측정·로드맵·ADR·변경 이력)
- [docs/architecture.md](docs/architecture.md): 그래프, 조건, 스키마, 툴, 모듈 구조
- [docs/experiments/](docs/experiments/README.md): EXP-001~003 기록
- [docs/business/feasibility.md](docs/business/feasibility.md): 사업성 검토
