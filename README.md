# Tashkeel Check

아랍어 문서 검수 도구: 번역에서 독법과 표기가 갈리는 곳을 드러낸다

*A review aid for people who are responsible for Arabic documents but cannot read Arabic. It surfaces the spots where an Arabic → English translation had to choose between readings, especially names and short fields, and refuses to settle them without evidence.*

> **현재 상태 (2026-10-21): 단계 1 실험 장치를 구현했고, 조건 비교 실험은 보류·준비 중입니다.** 실제 모델로는 개발용 문서 3개로 동작 점검만 했고(마지막 점검은 네 조건 모두 형식 통과), 측정 결과는 없습니다. 점검에서 드러난 채점 정의 문제는 실험 전에 고쳤습니다. 분석기 실측(EXP-001)은 끝났습니다. 실제 걸프 이름 단위 3,023개 가운데 분석기 후보에 실제 영문 표기가 든 비율이 50.2%로, 사전에 정한 기준(50%)을 겨우 넘었습니다(가문명 42%, 이름 70%). 에이전트 조건 비교(EXP-002)는 쉬운 합성 문서에서 반복 1회(120/360회) 만에 지시만 준 조건(C1)도 만점이 나와 보류했습니다. 그래서 동명이인·형식이 다른 근거·함정 근거·긴 문서가 섞인 어려운 합성 문서(synthetic-hard)와, 이름 정확도 99%(말없이 틀리지 않음과 기대 처분 일치 둘 다)를 기준으로 한 EXP-003을 준비했습니다. 생성기·채점·판정 코드와 개발용 문서 20개까지 만들었고, 평가 문서와 실제 모델 실행은 아직입니다. 아래 질문들은 답을 가정하지 않은 실험 질문입니다. 사업 쪽 대상은 걸프(사우디·UAE)에서 아랍어 문서를 영어로 읽어야 하는 사람으로 정했고, 제품에 사람 검수는 넣지 않습니다. 1순위 고객은 걸프 법인 고객의 서류를 확인하는 KYC·컴플라이언스 팀이고, 판매 형태는 API입니다. 지금의 단일 에이전트는 중간 단계이고, 멀티 에이전트 구조는 단계 3에서 같은 지표로 비교한 뒤 정합니다. 과제 2 요건에 따라 웹 화면·API·MCP를 단계 1.5로 구현했습니다(2026-10-21, 가짜 모델과 Postgres·MCP로 기능·예외 테스트 완료, 실제 모델 실행은 EXP-002 뒤). 같은 날 14단계 개발 가이드를 참고해 **서류 묶음 검수**(단계 2 첫 구현)를 더했습니다: 같은 대상 ID가 붙은 다른 서류의 영문 표기만 근거로 쓰고, 정확히 일치할 때만 확정하며, 나머지는 사유와 함께 확인 대기로 돌립니다([ADR-018](docs/adr/ADR-018.md)). 기록은 `docs/과제2-테스트-기록.md`입니다.

## 무엇을 하는가

번역기가 아닙니다. 아랍어는 단모음을 생략해서 같은 철자에 여러 독법이 생깁니다. 문맥으로 풀리지 않는 곳, 특히 인명·회사명과 표의 셀 같은 짧은 필드에서 번역이 어느 독법을 골랐는지 드러내고, 근거가 없으면 확정하지 않고 보류합니다.

| 아랍어 | 가능한 표기 |
| --- | --- |
| مسلم | Muslim, Musallam |
| حمد | Hamad, Hamd |
| رشيد | Rashid, Rashed |

서류의 이름은 여권이나 신분증 표기와 맞아야 합니다. 이 표기는 아랍어 실력으로 정해지지 않고 외부 근거가 있어야 확정됩니다.

이 도구가 약속하는 것은 "정확한 번역"이 아니라 "모호한 구간을 얼마나 잡아내는가"입니다.

## 왜 필요한가

번역하는 LLM은 모호한 단어를 만나면 표시하지 않고 하나로 정해 넘길 수 있습니다. 이 프로젝트는 이것을 "모호성 은폐"라고 부릅니다(specification gaming의 한 형태이며 의도적 조작이 아닙니다). 읽는 사람은 아랍어를 모르니 그런 선택이 있었다는 사실조차 알 수 없습니다. 이것이 실제로 얼마나 일어나는지가 단계 1에서 잴 첫 질문입니다.

## 단계 1에서 하는 것

기능은 적게, 측정은 많이 넣은 단일 에이전트 실험 장치를 만듭니다.

| 질문 | 데이터 |
| --- | --- |
| 형태소 분석기가 실제 걸프 인명에서 독법 후보를 얼마나 내는가 | Wikidata 인명(실제 데이터, CC0) |
| 에이전트가 모호한 곳을 정말 말없이 찍는가 | 업무 규칙 기반 합성 문서 |
| "모호하면 표시하라"는 지시만으로 해결되는가 | 〃 |
| 형태소 분석기를 주면 더 잡는가 | 〃 |

구성: LangGraph 그래프(입력 → 분석기 → 에이전트 → 검증 → 대조 → 출력), LangChain 모델·툴 인터페이스, LangSmith 추적. 형태소 분석은 CAMeL Tools를 씁니다. 처분 누락 확인과 지표 계산은 LLM이 아니라 코드가 합니다.

## 실행

Python 3.11과 [uv](https://docs.astral.sh/uv/)가 필요합니다.

```bash
uv sync
```

```bash
uv run camel_data -i morphology-db-msa-r13
```

API 키 없이 연습 모드(가짜 모델)로 문서 하나를 네 조건 모두 돌려 봅니다.

```bash
uv run tashkeel run --doc data/synthetic/dev/dev_001.json --condition all --fake
```

실제 모델로 돌리려면 `.env.example`을 `.env`로 복사해 `OPENAI_API_KEY`를 넣고 `--fake`를 뺍니다. LangSmith 키가 있으면 추적이 켜지고, 없으면 추적만 꺼집니다. 결과는 `results/debug/<문서>/<조건>/`에 `segments.json`, `proper_nouns.csv`, `metrics.json`, `run_meta.json`으로 남습니다.

EXP-002(조건 비교, 360회)는 비용이 들어 `--yes`가 있어야 돌고, 끊어 가며 돌릴 수 있습니다. `--max-runs`·`--token-budget`에 닿거나 실행 폴더에 `STOP` 파일을 만들면 돌던 실행만 마치고 멈춥니다. 멈춘 실행은 `--resume`으로 이어서 합니다. `exp002-status`는 진행과 토큰만 보여 주고, 결과 지표는 다 끝난 뒤 `summary.json`에만 나옵니다([ADR-016](docs/adr/ADR-016.md)).

```bash
uv run tashkeel exp002 --split eval --workers 4 --max-runs 8 --yes
uv run tashkeel exp002-status
uv run tashkeel exp002 --resume --workers 4 --yes
```

EXP-003(어려운 합성 문서, 99% 기준)은 같은 실행 장치를 씁니다. 개발용 문서의 구간별 정답은 `inspect-gold`로 볼 수 있습니다. 평가 문서는 한 번만 만들고, 이미 있으면 다시 만들지 않습니다([ADR-017](docs/adr/ADR-017.md)).

```bash
uv run tashkeel inspect-gold --split dev --case C2 --n 2
uv run tashkeel exp003 --split dev --fake --repeats 1 --workers 4   # 연습 모드, 비용 없음
uv run tashkeel exp003-errors                                       # 실행 뒤 사람 확인용 errors.csv
```

### 서비스(단계 1.5): API·폼 화면·Postgres·MCP

`.env`에 `LLM_BACKEND`(기본 `openai`, 키 없이 보려면 `fake`), `DATABASE_URL`(없으면 DB 없이 돈다), `USE_MCP_TOOLS`(기본 `false`)를 넣고 `run.sh`로 띄웁니다. `run.sh`는 키·포트를 검사하고 `alembic upgrade head`를 돌린 뒤 `tashkeel serve`를 띄워 `/health`를 기다립니다.

```bash
createdb tashkeel        # 로컬 Postgres. 또는 docker compose up db
LLM_BACKEND=fake USE_MCP_TOOLS=true DATABASE_URL=postgresql+psycopg:///tashkeel ./run.sh
```

화면 `http://127.0.0.1:8000`(샘플 문서 또는 아랍어 붙여넣기 → 조건 → 6단계 진행 → 번역·확인 대기 목록·지표), API 문서 `/docs`, 상태 `/health`. 결과는 `results/web/<작업>/` 네 파일과 DB(`documents`·`jobs`·`runs`·`name_items`) 양쪽에 남습니다. MCP 서버는 `uv run python -m tashkeel_check.mcp.server`로 stdio에서 혼자 띄울 수도 있습니다(툴 `analyze_tokens`, 리소스 `document://synthetic/{split}/{doc_id}`, 프롬프트 `review_instructions`). `docker compose up --build`는 앱 + Postgres(pgvector) 구성이고 아직 빌드해 보지 않았습니다[미확인].

### 완제품 패키지: Docker Compose + API 키 (ADR-019)

```bash
cp .env.example .env   # POSTGRES_PASSWORD, OPENAI_API_KEY(또는 LLM_BACKEND=fake), AUTH, MULTI_AGENT
docker compose up -d --build
docker compose run --rm app tashkeel customers add --name demo   # api_key: tk_… 를 한 번만 보여 준다
curl -s -H "X-API-Key: tk_…" -F files=@묶음.json localhost:8000/v1/bundles   # 묶음의 customer_id는 비우거나 키의 고객과 같아야 한다
LLM_BACKEND=fake ./scripts/smoke.sh                               # 기동 → 키 발급 → 업로드 → 대기 목록 → 사용량 → PASS
```

모든 `/v1/*`는 API 키(`X-API-Key` 또는 `Authorization: Bearer`)를 받고, 묶음·작업·사전·사용량은 키의 고객에 묶입니다(`GET /v1/usage`). 화면에서는 서류 파일을 올려 초안을 만들고(`POST /v1/bundles/draft`), 같은 당사자를 가리키는 칸에 대상을 지정한 뒤 검수합니다. 서버는 같은 대상을 **제안**만 하고 자동으로 연결하지 않습니다. `MULTI_AGENT=true`면 조건 `M1`(번역자 → 격리 검증자 → 규칙 중재자)을 받습니다. 절차는 [docs/deploy.md](docs/deploy.md)에 있습니다.

### 서류 묶음 검수(단계 2): 같은 대상의 다른 서류와 대조

여러 서류를 한 묶음으로 보내면, 서류의 영문 표기를 **같은 대상 ID(`entity_id`)가 붙은 다른 서류**의 영문 칸과 대조합니다. 대상은 사람·회사·기관·그 밖의 명명된 당사자 모두이고 규칙은 같습니다. 아랍어 표기가 같다는 이유로 다른 대상을 연결하지 않고, 대소문자·공백만 무시한 정확 일치일 때만 확정하며, 그 밖에는 사유(근거 없음, 서류 간 표기 충돌, 번역 표기 불일치, 비교 대상 없음, 검증 실패, 대상 ID 없음 …)와 함께 확인 대기로 돌립니다. 라벨 칸(`الاسم:`, `اسم الشركة:` …)이 있으면 LLM 없이 돌고, 라벨 칸이 없는 문장은 LLM(C1~C3)이 고유명사를 뽑아 같은 판정을 탑니다.

```bash
uv run tashkeel make-bundles          # 평가 사례 9개 × 대상 종류 3개 + KYC(등기·여권·정관) 사례 8개 합성 묶음 → data/synthetic/bundles/
curl -s -F files=@data/bundles/sample_bundle.json localhost:8000/v1/bundles   # 파일 업로드로 묶음 만들고 바로 검수
curl -s -X POST localhost:8000/v1/bundles/review -H 'content-type: application/json' \
  -d @data/bundles/sample_bundle.json | python3 -m json.tool
curl -s localhost:8000/v1/bundles/bundle_sample_001/pending
```

화면의 "서류 묶음" 탭에서 샘플 묶음이나 JSON을 넣어 전체 결과·확인 대기 목록·항목별 원문·번역·근거를 보고, 담당자가 확인한 표기를 사전에 등록해 항목을 닫을 수 있습니다(`POST /v1/dictionary`. 검수 결과를 자동으로 사전에 넣지 않습니다). 사전은 고객 + 대상 ID + 정규화 아랍어 표기가 키이고 다른 고객의 사전은 보지 않습니다. 저장은 Postgres 표 `bundles`·`review_items`·`name_dictionary`(`DATABASE_URL`이 없으면 메모리)입니다. MCP 서버에는 `search_bundle` 툴이 더해졌습니다. 파일 업로드(`POST /v1/bundles`)와 묶음 단위 진행 스트림(SSE)도 있습니다. 여권은 `Surname`·`Given Names` 칸을 하나로 합치고 MRZ 첫 줄도 해독해 근거로 쓰되, 같은 여권에 인쇄 칸이 있으면 MRZ는 쓰지 않습니다. 합성 KYC 묶음(상업등기 + 여권 + 정관, 사례 8개)이 `make-bundles`에 포함됩니다.

```bash
uv run pytest -m "not live"
```

`db` 마커 테스트는 `DATABASE_URL`이 닿을 때만 돌고, `live` 마커 테스트는 실제 OpenAI를 부릅니다. `.env`에 키가 있으면 `uv run pytest`만으로도 비용이 듭니다.

개발할 때는 CI와 같은 검사를 돌립니다. `tests/golden/`은 리팩토링 전후 결과가 같은지 보는 기준값이라 고치지 않습니다([ADR-013](docs/adr/ADR-013.md)).

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pre-commit install   # 선택: 커밋할 때 자동 검사
```

## 하지 않는 것 (단계 1)

스캔본 문자 인식, 사람 검토 화면(확인 대기 항목을 닫으며 표기를 등록하는 것만 있음), 멀티 에이전트 비교 실험(틀 `M1`은 있으나 실제 모델로 돌리지 않음), 한글 표기, 번역 문장 품질 평가, 고객당 여러 사용자·권한, 클라우드 배포 설정. 파일 업로드는 묶음 JSON 또는 텍스트 서류(`.json`·`.txt`·`.md`)만 받고 스캔본은 받지 않습니다. 벡터 검색(RAG)은 같은 대상의 구간만 색인하는 후보 힌트이고 근거로 쓰지 않습니다. 묶음에 대상 ID가 없는 고유명사는 근거를 찾지 않고 대기로 둡니다. 서류 종류별 우선순위는 없습니다(서류끼리 다르면 대기).

## 과제 2 안내 파일과의 대응 [확인, 2026-10-21 구현]

과제 2는 제공 프로젝트(`all_total_vue_student`: FastAPI + Vue 채팅 UI + LangGraph + MCP + SQLite)의 구조를 재활용해 새 서비스를 만들라고 합니다. 이 레포는 기존 구조를 유지하고 제공 프로젝트에서는 패턴만 가져옵니다. 챗봇 대신 문서 붙여넣기 폼, SQLite 대신 Postgres, LLM 층은 기존 LangChain 방식입니다([ADR-012](docs/adr/ADR-012.md)).

| 제공 프로젝트 파일 | 이 레포에서의 위치 | 상태 |
| --- | --- | --- |
| `web_chat.html` | `src/tashkeel_check/web/static/index.html` (Vue 3 CDN 폼 화면, `EventSource` 진행 표시) | 구현 |
| `server.py` | `src/tashkeel_check/web/app.py`(FastAPI, lifespan, `/health`, SSE), `web/jobs.py`(스레드 실행·이벤트) | 구현 |
| `agent/graph.py` | `src/tashkeel_check/graph.py` | 있음(변경 없음) |
| `agent/openai_llm.py`, `fake_llm.py` | `src/tashkeel_check/runner.py`의 `make_model`, `fake.py` | 있음(변경 없음) |
| `agent/ollama_llm.py` | 쓰지 않음 | — |
| `agent/session_store.py` (SQLite) | `src/tashkeel_check/web/db.py`, `web/models.py`, `alembic/` (Postgres 4테이블) | 구현 |
| `mcp_server.py`, `agent/mcp_client.py`, `agent/retry.py` | `src/tashkeel_check/mcp/server.py`(FastMCP stdio), `client.py`(한 번 연결·lock·`with_retry`), `tools.py`(C2 툴 교체) | 구현 |
| `data/` | `data/synthetic/`, `data/wikidata/` | 있음 |
| `run.sh` | `run.sh` (uv 기준, 키·포트 검사, alembic, `/health` 대기), `Dockerfile`, `docker-compose.yml` | 구현(compose 빌드는 미확인) |

기능별 테스트 16건과 예외 테스트 7종(빈 입력, 아랍어 없음, 조건 오류, 형식 오류 재시도, 키 없음 기동 거부, DB 불통, MCP 서버 다운)의 입력·예상·실제 결과와 화면 캡처는 [docs/과제2-테스트-기록.md](docs/과제2-테스트-기록.md)에 있습니다. 전체 동작 흐름: 화면/API → `POST /v1/reviews`(입력 검증) → 작업 스레드에서 LangGraph 그래프(`load → analyze → agent → validate → reconcile → export`) → 노드마다 SSE 이벤트 → 결과 파일 + DB → `GET /v1/jobs/{id}/result`.

## 알려진 한계

- 에이전트 실험은 합성 문서로 합니다. 결과를 실제 서류의 오류율이나 포착률로 일반화하지 않습니다.
- Wikidata 인명은 공개 인물 위주라 일반 고객 서류의 이름 분포와 다를 수 있습니다.
- 단계 1(단일 문서)에서 고유명사의 근거로 인정하는 것은 같은 문서 안의 영문 표기뿐입니다. 묶음 검수(단계 2)에서는 같은 대상 ID가 붙은 다른 서류의 영문 칸을 더 봅니다. 대상 ID는 입력 데이터가 줘야 하고, 이름이 같다는 사실로 대신하지 않습니다.
- 아랍어 사람 검수를 하지 않으므로 실제 고객 서류의 포착률은 재지 않습니다. 실제 문서 측정은 공식 영문본이 함께 공개된 문서로만 계획합니다.
- 어려운 합성 문서(synthetic-hard)의 99%는 그 유형 구성(어려운 경우 약 2/3, 문서 유형 넷)에서 잰 값입니다. 템플릿 아랍어와 단어 함정 문장은 사람이 검수하지 않았고, 판단이 갈릴 수 있는 정답은 따로 표시해 뺀 값도 함께 냅니다.
- 현재 모델(`gpt-6.1-sol`)은 temperature를 0으로 고정할 수 없습니다(기본값 1만 허용). 같은 입력에도 결과가 실행마다 달라질 수 있어, 실험은 반복 실행 간 일치율을 함께 보고합니다.

## 라이선스 참고

CAMeL Tools의 기본 형태소 DB(calima-msa-r13)는 GPL v2입니다. 이 프로젝트는 내부 측정에만 쓰며, 배포 형태로 넘어가기 전에 법률 검토가 필요합니다.

## 문서

- [PROJECT_PLAN.md](PROJECT_PLAN.md): 현재 상태, 다음 작업, 문서 지도
- [docs/README.md](docs/README.md): 문서 지도. 정의·범위·구조·데이터·측정·로드맵·ADR·변경 이력이 `docs/` 아래에 나뉘어 있다
- [아키텍처](docs/architecture.md): 그래프, 조건 C0~C3, 스키마, 툴, 스택, 코드 대조
- [로드맵](docs/roadmap.md): 주요 기능, 기술 스택·시스템 구성, 마일스톤, 체크리스트
- [사업성 검토](docs/business/feasibility.md): 시장성, 기술성, 경제성 검토
