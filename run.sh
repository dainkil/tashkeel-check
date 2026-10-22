#!/usr/bin/env bash
# 단계 1.5 서비스 실행(Mac, uv 기준): 키·DB 검사 → 마이그레이션 → tashkeel serve → /health 대기.
# 사용: ./run.sh            (.env의 LLM_BACKEND·REVIEW_CONDITION·DATABASE_URL·USE_MCP_TOOLS·WEB_PORT를 읽는다)
#       REVIEW_CONDITION=C1 ./run.sh  (기본 M2 대신 EXP-003에서 잰 설정 C1로)
#       LLM_BACKEND=fake ./run.sh   (API 키 없이 가짜 모델로 화면을 본다)
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv가 없습니다. README의 설치 절차(brew install uv, uv sync)를 먼저 하세요."; exit 1
fi
if [[ -f .env ]]; then
  set -a; # shellcheck disable=SC1091
  source .env; set +a
fi

MODE="${LLM_BACKEND:-openai}"
case "$MODE" in
  fake|openai) ;;
  *) echo "지원하지 않는 LLM_BACKEND: $MODE (openai / fake)"; exit 1 ;;
esac
case "${REVIEW_CONDITION:-M2}" in
  M2|C1) ;;
  *) echo "지원하지 않는 REVIEW_CONDITION: ${REVIEW_CONDITION} (M2 / C1)"; exit 1 ;;
esac
if [[ "$MODE" == "openai" && -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY가 없습니다. .env에 키를 넣거나 LLM_BACKEND=fake로 실행하세요."; exit 1
fi

HOST="${WEB_HOST:-127.0.0.1}"
PORT="${WEB_PORT:-8000}"
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "포트 $PORT를 이미 사용 중입니다. 기존 서버를 먼저 종료하세요."; exit 1
fi

if [[ -n "${DATABASE_URL:-}" ]]; then
  echo "DB 마이그레이션: alembic upgrade head"
  uv run alembic upgrade head
else
  echo "DATABASE_URL이 없어 DB 없이(메모리·results/ 파일만) 실행합니다."
fi

uv run tashkeel serve --host "$HOST" --port "$PORT" &
API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

for _ in $(seq 1 120); do
  if ! kill -0 "$API_PID" 2>/dev/null; then echo "서버가 기동 중에 종료됐습니다. 위 오류를 확인하세요."; exit 3; fi
  if curl -fsS --max-time 2 "http://$HOST:$PORT/health" >/dev/null 2>&1; then break; fi
  sleep 0.5
done
if ! curl -fsS --max-time 2 "http://$HOST:$PORT/health" >/dev/null 2>&1; then
  echo "서버가 /health에 응답하지 않습니다."; exit 1
fi
echo "실행 모드: $MODE · 화면 http://$HOST:$PORT · API 문서 http://$HOST:$PORT/docs · 종료: Control + C"
wait "$API_PID"
