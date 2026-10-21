# 단계 1.5 서비스 이미지. CAMeL 형태소 DB(calima-msa-r13, GPL v2)는 빌드 때 받는다(ADR-005: SaaS 내부 사용 한정).
FROM python:3.11-slim

ENV UV_PROJECT_ENVIRONMENT=/app/.venv PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:${PATH}"
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --locked --no-dev
RUN camel_data -i morphology-db-msa-r13

COPY data ./data
COPY alembic ./alembic
COPY alembic.ini ./
COPY run.sh ./

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && tashkeel serve --host 0.0.0.0 --port 8000"]
