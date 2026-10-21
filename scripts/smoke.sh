#!/usr/bin/env bash
# 완제품 패키지 스모크(ADR-019): compose 기동 → /health → 고객 키 발급 → 샘플 묶음 업로드 → 대기 목록 → 사용량 → PASS.
# 사용: ./scripts/smoke.sh            (.env에 POSTGRES_PASSWORD, LLM_BACKEND=fake 또는 OPENAI_API_KEY)
#       KEEP=1 ./scripts/smoke.sh     (끝나고 compose를 내리지 않는다)
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${WEB_PORT:-8000}"
BASE="http://127.0.0.1:$PORT"

docker compose up -d --build
trap '[[ -n "${KEEP:-}" ]] || docker compose down' EXIT

for _ in $(seq 1 60); do
  curl -fsS --max-time 2 "$BASE/health" >/dev/null 2>&1 && break
  sleep 2
done
curl -fsS "$BASE/health" | python3 -c 'import json,sys; h=json.load(sys.stdin); print("health:", h["status"], "db", h["db"], "auth", h["auth"], "backend", h["backend"])'

OUT="$(docker compose run --rm -T app tashkeel customers add --name smoke)"
KEY="$(printf '%s\n' "$OUT" | sed -n 's/^api_key: //p')"
[[ -n "$KEY" ]] || { echo "키 발급 실패:"; echo "$OUT"; exit 1; }
echo "customer key issued (prefix ${KEY:0:9}…)"

code="$(curl -s -o /dev/null -w '%{http_code}' "$BASE/v1/bundles")"
[[ "$code" == "401" ]] || { echo "키 없이 401이어야 하는데 $code"; exit 1; }
echo "no key → 401 OK"

# 샘플 묶음의 customer_id(customer_demo)는 키의 고객과 다르므로 떼고 올린다(다르면 400, ADR-019)
TMP="$(mktemp -t sample_bundle).json"
python3 -c 'import json,sys; b=json.load(open(sys.argv[1], encoding="utf-8")); b.pop("customer_id", None); json.dump(b, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)' data/bundles/sample_bundle.json "$TMP"
curl -fsS -H "X-API-Key: $KEY" -F "files=@$TMP;filename=sample_bundle.json" "$BASE/v1/bundles" \
  | python3 -c 'import json,sys; b=json.load(sys.stdin); print("upload:", b["bundle_id"], b["counts"])'
rm -f "$TMP"
PENDING="$(curl -fsS -H "X-API-Key: $KEY" "$BASE/v1/bundles/bundle_sample_001/pending" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')"
[[ "$PENDING" == "1" ]] || { echo "대기 항목이 1건이어야 하는데 $PENDING"; exit 1; }
echo "pending: $PENDING OK"
curl -fsS -H "X-API-Key: $KEY" "$BASE/v1/usage" | python3 -c 'import json,sys; u=json.load(sys.stdin); print("usage:", u["totals"])'
echo "PASS"
