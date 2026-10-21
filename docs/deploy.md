# 배포: Docker Compose 패키지 (완제품, ADR-019)

앱 1개 + Postgres 1개를 `docker compose`로 띄운다. 클라우드 배포 설정·TLS·리버스 프록시는 포함하지 않는다(앞단에 두는 것은 운영하는 쪽 몫이다).

## 1. 준비

1. Docker Desktop(또는 Docker Engine + Compose v2).
2. `.env.example`을 `.env`로 복사하고 다음을 채운다.

| 키 | 필수 | 뜻 |
| --- | --- | --- |
| `POSTGRES_PASSWORD` | 필수 | compose의 Postgres 비밀번호. 앱의 `DATABASE_URL`은 compose가 이 값으로 만든다 |
| `OPENAI_API_KEY` | `LLM_BACKEND=openai`일 때 필수 | 실제 모델. 없이 띄우려면 `LLM_BACKEND=fake`(가짜 모델, 화면·API 점검용) |
| `AUTH` | 선택 | compose 기본은 `required`(항상 API 키). `auto`는 활성 고객이 없을 때만 열림 |
| `MULTI_AGENT` | 선택 | `true`면 조건 `M1`(번역자 → 격리 검증자 → 규칙 중재자)을 받는다. 기본 `false` |
| `MODEL`, `PRICE_*` 등 | 선택 | `.env.example` 참고 |

`.env`는 커밋하지 않는다.

## 2. 띄우기와 첫 고객 키

```bash
docker compose up -d --build          # 이미지 빌드(CAMeL 형태소 DB를 받는다) → db → app. alembic upgrade head는 app 기동 때 돈다
curl -s localhost:8000/health         # {"status":"ok", "db": true, "auth": "required", ...}
docker compose run --rm app tashkeel customers add --name demo
```

`customers add`는 `api_key: tk_…`를 **한 번만** 출력한다. 저장은 sha256 해시뿐이라 잃어버리면 새 키를 만들어야 한다(`customers revoke <customer_id>` 뒤 `add`).

호출은 `X-API-Key: tk_…` 헤더(또는 `Authorization: Bearer tk_…`, SSE는 `?api_key=`). 화면(`http://localhost:8000`)은 상단 입력칸에 키를 넣고 저장하면 브라우저에 보관한다.

묶음 JSON에 `customer_id`가 있으면 키의 고객과 같아야 한다(다르면 400). 샘플 묶음은 `customer_demo`라서 떼고 올린다.

```bash
python3 -c 'import json; b=json.load(open("data/bundles/sample_bundle.json")); b.pop("customer_id"); json.dump(b, open("/tmp/sample.json","w"), ensure_ascii=False)'
curl -s -H "X-API-Key: $KEY" -F "files=@/tmp/sample.json;filename=sample_bundle.json" localhost:8000/v1/bundles
curl -s -H "X-API-Key: $KEY" localhost:8000/v1/bundles/bundle_sample_001/pending
curl -s -H "X-API-Key: $KEY" "localhost:8000/v1/usage?from=2026-10-01"
```

## 3. 스모크

```bash
LLM_BACKEND=fake ./scripts/smoke.sh   # 기동 → /health → 키 발급 → 키 없이 401 → 샘플 묶음 업로드 → 대기 1건 → 사용량 → PASS. 끝나면 compose down
KEEP=1 ./scripts/smoke.sh             # 내리지 않고 둔다
```

실행 결과는 `docs/과제2-테스트-기록.md` 6절에 적는다(실제로 돌린 것만).

## 4. 운영

- **업그레이드:** `git pull` → `docker compose up -d --build`. 마이그레이션은 기동 때 자동이다(`alembic upgrade head`).
- **백업:** `docker compose exec db pg_dump -U tashkeel tashkeel > backup.sql`. 데이터는 `pgdata` 볼륨에, 결과 파일은 `results` 볼륨에 있다.
- **고객 관리:** `docker compose run --rm app tashkeel customers list|revoke <id>`.
- **DB 포트:** 호스트에 열지 않는다. 직접 보려면 `docker compose exec db psql -U tashkeel tashkeel`.
- **로그:** `docker compose logs -f app`.

## 5. 포함하지 않는 것

TLS·도메인·리버스 프록시, 클라우드 배포 설정, 백업 자동화, 벡터 검색의 pgvector 이전(`rag/bundle.py`는 메모리 Qdrant 힌트 그대로), 사용자·권한 모델(고객당 키 하나), 접근 로그에서 `?api_key=`를 가리는 설정.
