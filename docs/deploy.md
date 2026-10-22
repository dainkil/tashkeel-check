# 배포: Docker Compose 패키지

앱 1개와 Postgres 1개를 `docker compose`로 띄운다(ADR-019). 앱 컨테이너는 기동할 때 `alembic upgrade head`(0001~0004, 표 11개)를 돌리고 `tashkeel serve`를 띄운다. 클라우드 배포 설정·TLS·리버스 프록시는 포함하지 않는다. 앞단에 두는 것은 운영하는 쪽의 몫이다.

compose 없이 한 대에서 띄우는 방법(`uv run tashkeel serve`, `./run.sh`)은 [README](../README.md)의 "설치 및 실행"에 있다.

## 1. 준비

1. Docker Desktop(또는 Docker Engine + Compose v2).
2. `.env.example`을 `.env`로 복사하고 다음을 채운다. `.env`는 커밋하지 않는다.

| 키 | 필수 | 뜻 |
| --- | --- | --- |
| `POSTGRES_PASSWORD` | 필수 | compose의 Postgres 비밀번호. 앱의 `DATABASE_URL`은 compose가 이 값으로 만든다 |
| `OPENAI_API_KEY` | `LLM_BACKEND=openai`일 때 필수 | 실제 모델(`MODEL`, 기본 `openai:gpt-6.1-sol`)과 보관함 임베딩에 쓴다 |
| `LLM_BACKEND` | 선택 | compose 기본은 `openai`. `fake`면 키 없이 가짜 모델로 화면·API를 점검한다(M2에서는 번역하지 않고, 회사 기록에서 찾은 이름만 보류로 낸다) |
| `AUTH` | 선택 | compose 기본은 `required`(항상 API 키). `auto`는 활성 고객이 없을 때만 열리고, `disabled`는 항상 열린다 |
| `REVIEW_CONDITION` | 선택 | 서비스 기본 조건. 기본 `M2`(두 agent + 회사 기록 툴 MCP + 코드 중재자, ADR-022, **정확도 미측정**). `C1`이면 EXP-003에서 잰 설정(LLM 한 번)으로 돈다. 요청마다 `condition`으로 고를 수도 있다 |
| `PROMPT_VERSION` | 선택 | 기본 `p1`(EXP-003에서 99% 기준을 넘긴 지시문). `p0`는 EXP-002의 옛 지시문 |
| `EMBEDDING_MODEL` | 선택 | 회사 문서 보관함 구절의 순서를 정하는 임베딩(기본 `text-embedding-3-small`, `LLM_BACKEND=openai`일 때). **보관함 글이 OpenAI로 간다**(LLM 호출과 같은 경계). 가짜 모델이면 연습용 n-gram이다 |
| `OCR_BACKEND` | 선택 | 기본 `none`(텍스트 층 없는 PDF·이미지는 400). `ocrspace`는 무료 OCR API이고 `OCR_API_KEY`가 필요하다(없으면 기동 거부). **파일을 제3자 서버로 보내므로 "자체 배포 안에서 처리"라는 전제와 어긋난다.** 민감 서류는 텍스트로 넣거나 로컬 백엔드로 갈아끼운다(`ocr/base.py`의 `OcrBackend`가 교체 지점) |
| `OCR_MAX_BYTES` · `UPLOAD_MAX_BYTES` | 선택 | OCR로 보낼 파일 상한(기본 1 MB, 무료 등급 제한은 공식 문서로 확인하지 않았다)과 업로드 상한(기본 5 MB) |
| `MULTI_AGENT` | 선택 | `true`면 조건 `M1`(번역자 → 격리 검증자 → 규칙 중재자)도 받는다. 기본 `false`(보류 기능) |
| `MODEL`, `PRICE_*` 등 | 선택 | `.env.example` 참고 |

인증을 끈 서버(`AUTH=disabled`, 또는 `auto`에서 고객이 없을 때)는 회사 사전과 보관함을 고객 `local` 하나에 묶는다(한 회사 자체 배포용, ADR-021).

## 2. 띄우기와 첫 고객 키

```bash
docker compose up -d --build          # 이미지 빌드(CAMeL 형태소 DB를 받는다) → db → app(기동 때 alembic upgrade head)
curl -s localhost:8000/health         # {"status":"ok", "db": true, "auth": "required", "default_condition": "M2", "records_mcp": true, "archive": {"store": "db", ...}, ...}
docker compose run --rm app tashkeel customers add --name demo
```

`customers add`는 `api_key: tk_…`를 **한 번만** 출력한다. 저장은 sha256 해시뿐이라 잃어버리면 새 키를 만들어야 한다(`customers revoke <customer_id>` 뒤 `add`).

호출은 `X-API-Key: tk_…` 헤더로 한다(또는 `Authorization: Bearer tk_…`, SSE는 `?api_key=`). 화면(`http://localhost:8000/#/upload`)은 상단 입력칸에 키를 넣고 저장하면 브라우저에 보관한다.

서류 하나를 검수하고 결과를 확정하는 흐름:

```bash
curl -s -H "X-API-Key: $KEY" -F file=@계약서.txt localhost:8000/v1/reviews/upload    # 202, job_id
curl -s -H "X-API-Key: $KEY" localhost:8000/v1/jobs/<job_id>/result | jq '.dictionary, .archive'
curl -s -H "X-API-Key: $KEY" -X POST localhost:8000/v1/dictionary -H 'content-type: application/json' \
  -d '{"job_id": "<job_id>", "token_ids": [11], "english_name": "Nawal"}'          # 보관함 제안은 "archive_hit_id"로
curl -s -H "X-API-Key: $KEY" localhost:8000/v1/archive                             # 보관함 목록, DELETE /v1/archive/{document_id}
curl -s -H "X-API-Key: $KEY" "localhost:8000/v1/usage?from=2026-10-01"
```

## 3. 스모크

```bash
LLM_BACKEND=fake ./scripts/smoke.sh   # 빌드·기동 → /health → 키 발급 → 키 없이 401 → 샘플 묶음 업로드(라벨 경로, LLM 없음) → 대기 1건 → 사용량 → PASS. 끝나면 compose down
KEEP=1 ./scripts/smoke.sh             # 내리지 않고 둔다
```

스모크는 인증·DB·마이그레이션·사용량이 컨테이너 안에서 도는지 본다. 샘플로 묶음 검수 경로(보류 기능, ADR-021)를 쓰므로 서류 업로드 → M2 검수 흐름은 확인하지 않는다. 실행 결과는 [테스트 기록](과제2-테스트-기록.md) 6절에 있다(6.1 P-11 PASS, 이미지 10.1 GB).

## 4. 운영

- **업그레이드:** `git pull` → `docker compose up -d --build`. 마이그레이션은 기동 때 자동이다(`alembic upgrade head`).
- **백업:** `docker compose exec db pg_dump -U tashkeel tashkeel > backup.sql`. 고객·API 키 해시·작업·결과·회사 사전·문서 보관함(`archive_documents`·`archive_passages`)은 모두 `pgdata` 볼륨의 DB에 있고, 결과 파일은 `results` 볼륨에 있다.
- **고객 관리:** `docker compose run --rm app tashkeel customers list|revoke <id>`.
- **보관함에서 서류 빼기:** 화면의 업로드 페이지 "회사 문서 보관함" 또는 `DELETE /v1/archive/{document_id}`. 그 서류를 출처로 한 제안은 내려가고, 이미 확정한 사전 항목은 남는다.
- **DB 포트:** 호스트에 열지 않는다. 직접 보려면 `docker compose exec db psql -U tashkeel tashkeel`.
- **로그:** `docker compose logs -f app`.

## 5. 포함하지 않는 것

TLS·도메인·리버스 프록시, 클라우드 배포 설정, 백업 자동화, 사용자·권한 모델(고객당 키 하나), 접근 로그에서 `?api_key=`를 가리는 설정, 외부 MCP 클라이언트용 `/mcp`(ADR-022에서 미룸), 이미지 용량 줄이기. DB 이미지는 pgvector용이지만 확장은 쓰지 않는다. 보관함 임베딩은 실수 배열로 저장하고 유사도는 Python에서 계산한다(ADR-022).
