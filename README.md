# Tashkeel Check

아랍어 문서 검수 도구: 번역에서 독법과 표기가 갈리는 곳을 드러낸다

*A review aid for people who are responsible for Arabic documents but cannot read Arabic. It surfaces the spots where an Arabic → English translation had to choose between readings, especially names and short fields, and refuses to settle them without evidence.*

> **현재 상태 (2026-10-20): 단계 1 실험 장치를 구현했고, 실험은 아직 돌리지 않았습니다.** 실제 모델로는 개발용 문서 2개로 동작 점검만 했고, 측정 결과는 없습니다. 점검에서 드러난 채점 정의 문제는 실험 전에 고쳤습니다. 분석기 실측(EXP-001)은 개발용 표본으로 영문 표기 비교 규칙을 고쳐 고정했고, 본 측정은 아직입니다. 아래 질문들은 답을 가정하지 않은 실험 질문입니다. 사업 쪽 대상은 걸프(사우디·UAE)에서 아랍어 문서를 영어로 읽어야 하는 사람으로 정했고, 제품에 사람 검수는 넣지 않습니다. 1순위 고객은 걸프 법인 고객의 서류를 확인하는 KYC·컴플라이언스 팀이고, 판매 형태는 API입니다. 지금의 단일 에이전트는 중간 단계이고, 멀티 에이전트 구조는 단계 3에서 같은 지표로 비교한 뒤 정합니다. 과제 2 요건에 따라 웹 화면·API·MCP를 계획(단계 1.5)에 추가했고, 아직 구현 전입니다.

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

```bash
uv run pytest -m "not live"
```

`live` 마커 테스트는 실제 OpenAI를 부릅니다. `.env`에 키가 있으면 `uv run pytest`만으로도 비용이 듭니다.

개발할 때는 CI와 같은 검사를 돌립니다. `tests/golden/`은 리팩토링 전후 결과가 같은지 보는 기준값이라 고치지 않습니다(`PROJECT_PLAN.md` ADR-013).

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pre-commit install   # 선택: 커밋할 때 자동 검사
```

## 하지 않는 것 (단계 1)

스캔본 문자 인식, 고객별 이름 사전, 사람 검토 화면, 멀티 에이전트, 한글 표기, 번역 문장 품질 평가. 서류 묶음 검색(RAG·벡터 DB)은 단계 2용 틀만 있고 꺼져 있습니다. 웹 화면과 API는 단계 1.5로 계획만 있고 아직 없습니다.

## 과제 2 안내 파일과의 대응 [계획, 미구현]

과제 2는 제공 프로젝트(`all_total_vue_student`: FastAPI + Vue 채팅 UI + LangGraph + MCP + SQLite)의 구조를 재활용해 새 서비스를 만들라고 합니다. 이 레포는 기존 구조를 유지하고 제공 프로젝트에서는 패턴만 가져옵니다. 챗봇 대신 문서 붙여넣기 폼, SQLite 대신 Postgres, LLM 층은 기존 LangChain 방식입니다(`PROJECT_PLAN.md` ADR-012).

| 제공 프로젝트 파일 | 이 레포에서의 위치 | 상태 |
| --- | --- | --- |
| `web_chat.html` | `src/tashkeel_check/web/static/index.html` (Vue 3 CDN 폼 화면) | 계획 |
| `server.py` | `src/tashkeel_check/web/app.py`, `web/jobs.py` (FastAPI, SSE 진행) | 계획 |
| `agent/graph.py` | `src/tashkeel_check/graph.py` | 있음(변경 없음) |
| `agent/openai_llm.py`, `fake_llm.py` | `src/tashkeel_check/runner.py`의 `make_model`, `fake.py` | 있음(변경 없음) |
| `agent/ollama_llm.py` | 쓰지 않음 | — |
| `agent/session_store.py` (SQLite) | `src/tashkeel_check/web/db.py`, `web/models.py` (Postgres) | 계획 |
| `mcp_server.py`, `agent/mcp_client.py` | `src/tashkeel_check/mcp/` (툴 `analyze_tokens`, 리소스 합성 문서, 프롬프트 조건 지시문) | 계획 |
| `data/` | `data/synthetic/`, `data/wikidata/` | 있음 |
| `run.sh` | `run.sh` (uv 기준, Postgres 확인 포함) | 계획 |

실행 방법, 실행 화면, 기능별·예외 테스트 결과는 구현 뒤에 이 문서와 `docs/과제2-테스트-기록.md`에 넣습니다.

## 알려진 한계

- 에이전트 실험은 합성 문서로 합니다. 결과를 실제 서류의 오류율이나 포착률로 일반화하지 않습니다.
- Wikidata 인명은 공개 인물 위주라 일반 고객 서류의 이름 분포와 다를 수 있습니다.
- 단계 1에서 고유명사의 근거로 인정하는 것은 같은 문서 안의 영문 표기뿐입니다.
- 아랍어 사람 검수를 하지 않으므로 실제 고객 서류의 포착률은 재지 않습니다. 실제 문서 측정은 공식 영문본이 함께 공개된 문서로만 계획합니다.
- 현재 모델(`gpt-6.1-sol`)은 temperature를 0으로 고정할 수 없습니다(기본값 1만 허용). 같은 입력에도 결과가 실행마다 달라질 수 있어, 실험은 반복 실행 간 일치율을 함께 보고합니다.

## 라이선스 참고

CAMeL Tools의 기본 형태소 DB(calima-msa-r13)는 GPL v2입니다. 이 프로젝트는 내부 측정에만 쓰며, 배포 형태로 넘어가기 전에 법률 검토가 필요합니다.

## 문서

- [PROJECT_PLAN.md](PROJECT_PLAN.md): 계획, 측정 설계, ADR, 진행 기록
- [개발 계획](docs/개발-계획.md): 주요 기능, 기술 스택·시스템 구성, 마일스톤
- [사업성 검토](사업성%20검토%20아랍어%20문서%20검증%20도구.md): 시장성, 기술성, 경제성 검토
