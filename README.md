# Tashkeel Check

아랍어 서류를 영어로 읽어야 하는 사람을 위한 검수 도구.

아랍어는 단모음을 적지 않아서 같은 철자의 이름이 여러 가지로 읽힌다. مسلم은 Muslim일 수도 Musallam일 수도 있다. 번역 LLM은 이런 자리를 표시 없이 하나로 정해 버릴 수 있고, 아랍어를 모르는 읽는 사람은 그런 선택이 있었다는 사실조차 모른다.

이 도구는 문서를 넣으면 고유명사마다 읽기 후보를 문서 안 근거와 함께 보여 주고, 근거가 없으면 확정하지 않고 보류한다. 사람이 후보를 골라 확정하면 회사 사전에 저장되고, 다음 서류의 같은 이름은 처음부터 확정으로 나온다. 대상은 걸프(사우디·UAE)에 진출한 외국 중소기업이 아랍어 서류를 내부 검토용으로 읽는 경우다.

## 사용 흐름

![파일 넣는 페이지](docs/images/screen-upload.jpg)

1. `#/upload`에서 점선 상자를 누르면 로컬 파일 선택 창이 열린다. `.txt`, `.md`, 텍스트 층이 있는 `.pdf`를 받고, 스캔·이미지는 OCR 백엔드를 켰을 때만 읽는다.
2. 추출 → 분석이 끝나면 결과 페이지로 넘어간다. 원문과 번역에 이름이 색으로 표시된다. 주황은 보류, 초록은 문서 근거로 확정, 파랑은 회사 사전으로 확정, 빨강은 사전과 문서 근거가 다른 경우다.
3. 이름을 누르면 그 자리에 후보가 열린다. 사전 표기, 문서 근거, LLM 후보, 직접 입력 순이다.

![후보 토글](docs/images/screen-result-candidates.jpg)

4. 후보를 누르면 바로 회사 사전에 저장되고 번역문의 `[Nawal/Noual]`이 `Nawal`로 바뀐다. 같은 문서를 다시 넣으면 모델 출력은 여전히 보류지만 사전이 덧씌워져 처음부터 파랑으로 나온다.

![재사용](docs/images/screen-result.jpg)

사전은 사람이 후보를 누를 때만 쌓인다. 검수 결과를 자동으로 사전에 넣지 않는다. 문서 근거와 사전이 다르면 확정하지 않고 충돌로 보여 준다.

## 설계 배경과 실험 결과

처음 가설은 "형태소 분석기(CAMeL Tools)를 LLM에 주면 모호한 이름을 더 잘 잡는다"였다. 그래서 기능보다 측정 장치를 먼저 만들었다. LangGraph 그래프(입력 → 분석기 → 에이전트 → 검증 → 대조 → 출력)에 조건 네 개를 두고, 업무 규칙으로 만든 합성 서류와 자동 채점으로 비교했다.

| 조건 | 내용 |
| --- | --- |
| C0 | 지시 없는 번역 |
| C1 | "근거 없이 확정하지 말라"는 지시문만 |
| C2 | C1 + 분석기를 툴로 호출 |
| C3 | C1 + 분석기 결과를 입력에 미리 넣음 |

결과는 가설과 달랐다. 동명이인, 다른 사람의 영문 표기, 회사명·이메일 같은 함정, 긴 문서를 섞은 어려운 시험지 70개(이름 부분 1,457개)에서 지시문만 준 C1이 99.93%를 냈고, 분석기를 준 C2·C3와 차이가 없었다([EXP-003](docs/experiments/EXP-003.md)).

| 조건 | 엄격 정확도 | 안전 정확도 | 문서당 시간 | 문서당 토큰 | 문서당 비용[추정] |
| --- | --- | --- | --- | --- | --- |
| C0 지시 없음 | 0.5546 | 0.5546 | 7초 | 765 | $0.004 |
| C1 옛 지시문 p0 | 0.9266 | 0.9300 | 69초 | 7,247 | $0.060 |
| C1 지시문 p1 | 0.9993 | 1.0000 | 62초 | 6,635 | $0.053 |
| C2 p1 + 분석 툴 | 0.9979 | 1.0000 | 59초 | 15,000 | $0.073 |
| C3 p1 + 분석 블록 | 0.9993 | 1.0000 | 86초 | 18,782 | $0.103 |

![EXP-003 비교](docs/images/exp003-compare.jpg)

엄격 정확도는 철자까지 맞아야 하고, 안전 정확도는 "말없이 틀리지 않음"만 본다. 모델은 `gpt-6.1-sol`, 반복 1회, 350회에 약 21분·약 $10이 들었다. 비용은 기본 단가(입력 $2·출력 $10/100만 토큰)로 계산한 추정값이다.

차이를 만든 것은 분석기가 아니라 지시문이었다. 옛 지시문 p0는 "모호하면 표시하라"였고, p1은 근거의 원칙(같은 문서 안의 영문 표기만, 글자 그대로 인용, 다른 사람의 표기는 근거가 아니다)을 적었다. p0의 오류 107건은 다른 사람의 표기를 근거로 쓴 것 49건, 그 사람 표기로는 부족한데 확정한 것 43건, 함정 10건, 보류 5건이다. p1의 오류는 1건으로, `ASA'AD`와 MRZ의 `ASAAD`를 다른 철자로 보고 보류한 것이다. 지시 없는 C0는 절반 가까이 말없이 찍었다(626건).

그래서 방향을 바꿨다([ADR-021](docs/adr/ADR-021.md)). 읽기 자체는 지시문으로 거의 해결되므로, 제품의 가치를 근거 찾기·검증·기록·재사용에 두고 회사 사전과 파일 업로드 화면을 만들었다. 분석기는 측정 지표용으로만 남겼다. 그 전에 만들었던 KYC용 서류 묶음 검수(같은 대상 ID의 다른 서류와 대조)와 멀티 에이전트 틀은 코드만 두고 보류했다.

이 99%는 합성 문서에서 잰 값이다. 시험지와 정답 규칙과 지시문을 같은 작업자가 설계했고, 자동 판정 오류의 사람 확인은 아직이다. 실제 서류로 일반화하지 않는다.

## 시스템 구성

| 부분 | 내용 |
| --- | --- |
| 그래프 | `graph.py`의 6노드. 구조화 출력이 형식에 안 맞으면 agent 노드를 1회 재시도한다. 처분 누락 확인과 지표 계산은 LLM이 아니라 코드가 한다 |
| 사전 덧씌움 | `dictionary_apply.py`. 결과를 고치지 않고 그 위에 덧씌움만 만든다. 보류 + 사전 적중이면 사전 확정, 문서 근거와 다르면 충돌. 키는 고객 + 정규화한 아랍어 |
| 입력 | `ocr/`. `.txt`·`.md` 그대로, `.pdf`는 `pypdf` 텍스트 층 먼저, 아랍어가 없으면 OCR. 백엔드는 `Protocol`이라 갈아끼울 수 있고 지금은 `none`과 무료 API `ocrspace`가 있다 |
| 서비스 | FastAPI(`web/app.py`), 작업 스레드와 SSE 진행 이벤트(`web/jobs.py`), Postgres + Alembic(`web/db.py`, 없으면 메모리), Vue 3 한 파일 화면 |
| MCP | `mcp/server.py`(FastMCP stdio): 툴 `analyze_tokens`·`search_bundle`, 리소스 `document://synthetic/...`, 프롬프트 `review_instructions`. 클라이언트는 연결 하나를 lock으로 공유하고 재시도한다. `USE_MCP_TOOLS=true`면 C2의 툴 호출이 MCP로 간다 |
| 의존성 주입 | `Settings` → `build_runtime()` → `Runtime(model, analyzer, dictionary, ocr)`. 모델은 `make_model(fake=...)`로 진짜·가짜를 바꾸고 테스트는 가짜를 넣는다 |
| 묶음 검수 | `bundle/`. 같은 대상 ID가 붙은 다른 서류의 영문 칸만 근거로 쓰고 정확히 일치할 때만 확정. 여권 MRZ 해독 포함. 보류 중 |
| 멀티 에이전트 | `multi_agent.py`의 M1: 번역자 → 격리된 검증자 → 규칙 중재자. 가짜 모델로만 테스트했다. 보류 중 |
| 실험 | `experiments/`. `plan.json`에 문서 해시·프롬프트 해시·설정을 고정하고 `runs.jsonl`로 재개한다. API 오류는 완료로 치지 않는다 |
| 추적 | `runner.py`의 LangSmith `@traceable`. 키가 있으면 켜지고 없으면 추적만 꺼진다 |
| 테스트 | pytest 512개. 골든 스냅샷 160건은 리팩토링 전후 결과가 같은지 보는 기준값이라 고치지 않는다([ADR-013](docs/adr/ADR-013.md)). ruff, mypy |

모듈 계층과 코드 대조는 [docs/architecture.md](docs/architecture.md)에 있다.

## 설치 및 실행

Python 3.11과 [uv](https://docs.astral.sh/uv/)가 필요하다.

```bash
uv sync
uv run camel_data -i morphology-db-msa-r13
cp .env.example .env     # OPENAI_API_KEY. 없으면 LLM_BACKEND=fake
```

```bash
LLM_BACKEND=openai AUTH=disabled uv run tashkeel serve --port 8000
# http://127.0.0.1:8000/#/upload   (API 문서 /docs, 상태 /health)
```

API로 쓰려면:

```bash
curl -s -F file=@계약서.txt localhost:8000/v1/reviews/upload          # 202 job_id
curl -s localhost:8000/v1/jobs/<job_id>/result | jq '.dictionary'
curl -s -X POST localhost:8000/v1/dictionary -H 'content-type: application/json' \
  -d '{"job_id": "<job_id>", "token_ids": [11, 86], "english_name": "Nawal"}'
curl -s localhost:8000/v1/dictionary                                    # DELETE /v1/dictionary/{id}로 취소
```

가짜 모델(`LLM_BACKEND=fake`)은 비용이 없지만 분석기가 모르는 토큰만 보류로 내서 샘플 문서에서는 이름 항목이 거의 없다. 실제 모델은 문서 하나에 60~100초, 약 $0.05가 든다. 스캔·이미지는 `OCR_BACKEND=ocrspace OCR_API_KEY=...`가 있어야 읽히고, 무료 API는 파일을 제3자 서버로 보낸다. Postgres를 쓰려면 `DATABASE_URL`을 준다. `run.sh`는 키·포트 검사와 `alembic upgrade head`까지 해 준다. Docker Compose와 API 키 발급은 [docs/deploy.md](docs/deploy.md)에 있다.

실험과 CLI:

```bash
uv run tashkeel run --doc data/synthetic/dev/dev_001.json --condition all --fake   # 네 조건 연습 실행
uv run tashkeel exp003 --split dev --fake --repeats 1 --workers 4                  # 연습, 비용 없음
uv run tashkeel exp003-errors                                                       # 사람 확인용 errors.csv
uv run tashkeel make-bundles                                                        # 합성 묶음 생성
```

```bash
uv run pytest -m "not live"      # db 마커는 DATABASE_URL이 닿을 때만, live는 실제 모델 호출
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

## 알려진 한계

- 에이전트 실험은 합성 문서로 했다. 실제 서류의 오류율이나 포착률로 일반화하지 않는다.
- 단일 문서에서 근거로 인정하는 것은 같은 문서 안의 영문 표기와 회사 사전뿐이다.
- 회사 사전은 고객 안에서 같은 아랍어 철자를 같은 이름으로 본다. 같은 철자의 다른 사람이면 잘못 확정할 수 있고, 문서 근거와 다를 때만 충돌로 잡는다.
- 문자 인식 성능은 재지 않았고, 인식 오류와 독법 오류를 구분해 보고하지 못한다.
- 현재 모델은 temperature를 0으로 고정할 수 없어 같은 입력에도 실행마다 결과가 다를 수 있다.
- CAMeL Tools의 형태소 DB(calima-msa-r13)는 GPL v2다. 측정에만 쓰고, 배포 전 법률 검토가 필요하다.

## 향후 계획

1. 자기 회사 표기 감시. 자기 회사를 거래처 0번으로 등록하고 서류의 회사명·등기번호·세금번호가 다르면 경고한다.
2. OCR 실제 호출 1회(키가 생기면)와 무료 등급 제한 확인. 민감 서류용 로컬 백엔드는 요구가 생기면.
3. Postgres에 사전을 둔 실행과 `docker compose up --build` 재확인.
4. 중소기업 서류(거래처 계약, 정부 통지, 임대차, 인보이스, 근로계약)로 합성 문서 생성기 v3.
5. EXP-003 `errors.csv`의 사람 확인과, 공개 이중언어 문서로 실제 서류 측정.
6. 사전 키를 거래처 단위로 나눌지 결정.

## 관련 문서

- [PROJECT_PLAN.md](PROJECT_PLAN.md): 현재 상태, 다음 작업, 정할 것
- [docs/README.md](docs/README.md): 문서 지도(정의·범위·구조·데이터·측정·로드맵·ADR·변경 이력)
- [docs/experiments/](docs/experiments/README.md): EXP-001~003 기록
- [docs/과제2-테스트-기록.md](docs/과제2-테스트-기록.md): 기능별·예외 테스트의 입력·예상·실제
- [docs/business/feasibility.md](docs/business/feasibility.md): 사업성 검토
