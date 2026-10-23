# Tashkeel Check

아랍어 음성 에이전트가 이름을 제대로 읽게 하는 앞단 층. **2026-10-23 방향 전환, 계획 단계.**

아랍어는 단모음을 적지 않아서 같은 철자의 이름이 여러 가지로 읽힌다. مسلم은 Muslim일 수도 Musallam일 수도 있다. TTS 엔진은 내부에서 발음을 추측해 하나로 읽고, 그 선택을 표시하지 않는다. 디아크리타이저와 LLM은 바로 이 고유명사에서 가장 자주 틀리고(GPT-4o가 영어 표기를 받고도 73%, NYUAD 고유명사 벤치), 운영자도 듣는 사람도 틀렸다는 사실을 모른다.

이 도구는 음성 에이전트가 말할 텍스트에서 고유명사(사람·회사·지명)마다 올바른 독법을 근거와 함께 정해 TTS 엔진에 넘긴다. 근거(고객 발음 사전, 본인 녹음, 등록 서류의 라틴 표기, 사람 확정)가 있으면 그 독법을 쓰고, 없으면 기본 독법을 내보내되 낮은 확신으로 표시해 사후 확정 큐에 넣는다. 사람이 확정한 발음은 고객 발음 사전에 쌓여 다음 발화부터 바로 쓰인다. 대상은 사우디·UAE에서 아랍어 음성 봇·IVR을 운영하는 은행·통신사·정부 서비스와 이들에게 음성 에이전트를 공급하는 쪽이다.

TTS 엔진이 아니다. 엔진은 기존 것(Azure·Amazon Polly·Google·ElevenLabs·오픈 모델)을 쓰고, 이 도구는 그 앞에서 "어느 이름이 확정이고 어느 이름이 추측인지"를 정해 넘긴다.

## 상태

- **코드:** 아직 이전 제품(아랍어 서류의 이름을 영문 표기 후보와 근거로 보여 주는 검수 서비스, 2026-10-22 제출본) 그대로다. TTS 앞단 층의 코드는 없다.
- **문서:** TTS 기준으로 다시 썼다([ADR-023](docs/adr/ADR-023.md)). 이전 제품 문서는 [docs/archive/document-review/](docs/archive/document-review/)에 있다.
- **측정값:** 없다. 첫 실험 [EXP-006](docs/experiments/EXP-006.md)(엔진 베이스라인)은 사전 등록 초안만 있고 실행하지 않았다.

## 사용 흐름 (계획)

**오프라인:** 고객이 이름 목록(CRM, 등록 서류, 선택으로 본인 녹음)을 올린다. 이름마다 독법 후보를 만들고(형태소 분석기·디아크리타이저·LLM·라틴 표기 역음역), 근거를 검사하고(라틴 표기 일치, 녹음 정렬, 사람 확정), 확정 큐에서 후보를 합성해 들려주고 고르면 고객 발음 사전에 들어간다.

**실시간:** 음성 에이전트의 LLM이 낸 문장이 TTS로 가기 전에 `POST /v1/pronounce`를 거친다. 사전에 있는 이름은 확정 독법(high), 없는 이름은 결정적 디아크리타이저의 기본 독법에 확신 등급(medium/low)을 붙여 엔진 형식(디아크리틱스 텍스트, IPA/X-SAMPA phoneme, 사전 항목)으로 치환한다. LLM 호출은 없고 목표는 문장당 50ms 이하다 [제안]. 저확신 발화는 사후 확정 큐로 간다.

## 왜 앞단 층인가

- 디아크리타이저·LLM의 오류는 고유명사에 집중한다(Sadeed 2025, CamelProp 2025). 신경망 TTS는 저자원 고유명사를 체계적으로 틀린다(SonoEdit 2026).
- 최신 오픈 엔진은 디아크리틱스 없이 합성하는 쪽으로 간다(Habibi 2026). 이름 발음 제어는 엔진 밖에서 해야 할 필요가 커진다.
- 발음 제어 수단(SSML phoneme·사전)은 엔진·모델·로케일마다 지원이 다르고 조용히 무시되기도 한다. 어느 입력을 어느 엔진이 받는지 실험으로 채우는 것이 제품의 일부다.
- 이전 제품에서 확인한 원칙이 그대로 쓰인다: 모델이 "모름"을 판단하게 두지 않고 코드가 근거 유무로 정한다. 인용·일치는 코드가 검사한다. 사전은 사람만 쓴다.

조사 근거는 [docs/research/tts-literature.md](docs/research/tts-literature.md)에 있다.

## 지금 코드로 할 수 있는 것

이전 제품(서류 검수 서비스)이 그대로 돈다. Python 3.11과 [uv](https://docs.astral.sh/uv/)가 필요하다.

```bash
uv sync
uv run camel_data -i morphology-db-msa-r13
cp .env.example .env     # OPENAI_API_KEY. 없으면 LLM_BACKEND=fake
LLM_BACKEND=openai AUTH=disabled uv run tashkeel serve --port 8000
# http://127.0.0.1:8000/#/upload
```

```bash
uv run pytest -m "not live"      # 559개
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

서류 검수 서비스의 사용 흐름·API·시스템 구성·실험 결과는 [보관 문서](docs/archive/document-review/)와 [배포 절차](docs/deploy.md), [테스트 기록](docs/과제2-테스트-기록.md)에 있다. 그 코드 중 TTS 앞단 층이 가져가는 것(토큰·구간 ID, 정규화 키, 형태소 분석기 독법 후보, 사전 저장소·API, 범위 토큰 MCP, 실험 장치)과 바꾸는 것은 [docs/architecture.md](docs/architecture.md) 4.3절에 있다.

## 알려진 한계

- 계획 단계다. TTS 앞단 층의 코드·측정값이 없다.
- 이름 벤치는 공개 인물(Wikipedia·Wikidata) 위주다. 고객 이름 분포로 일반화하지 않는다.
- 자체 라벨(걸프 인명 디아크리틱스)에는 아랍어 원어민 라벨러 2인이 필요하다. 팀 안에 없다.
- 결정적 디아크리타이저가 이름 구간에서 수십 ms 안에 드는지는 어느 논문도 보고하지 않았다. 직접 재야 한다.
- 라틴 표기(Musallam)에서 모음을 역추론하는 것은 상한이 있다. e/o·장모음·shadda·인두음 정보가 라틴 표기에 없다.
- 걸프 방언 독법과 표준 아랍어 독법 중 고객이 어느 쪽을 원하는지 모른다. 설정으로 두고 잰다.
- 본인 녹음은 개인(생체) 데이터다. 역내 저장과 동의가 필요하고, 수집이 어려우면 근거를 라틴 표기·사람 확정으로 줄인다.
- 사람 간 디아크리틱스 불일치(WER 1.6~5.6%)보다 높은 정확도는 약속하지 않는다.
- CAMeL Tools의 형태소 DB(calima-msa-r13)는 GPL v2다. 측정·오프라인에만 쓰고 실시간 경로의 디아크리타이저는 Apache-2.0·MIT 것을 우선한다.

## 향후 계획

[PROJECT_PLAN.md](PROJECT_PLAN.md)와 [docs/roadmap.md](docs/roadmap.md) 2절과 같은 순서다.

1. EXP-006 엔진 베이스라인의 판정 기준·예산·엔진 목록 확정과 실행. 결과로 엔진 지원 매트릭스를 채운다.
2. 디아크리타이저 3종(CATT-EO ONNX·libtashkeel·CAMeL GLF)의 이름 단위 정확도·지연 점검.
3. 사전 스키마 확장과 독법 후보 생성.
4. 엔진 어댑터 2개와 G2P 첫 판.
5. 확정 큐와 피드백 기록.
6. 실시간 API와 지연 측정.
7. 사업성 검토 재계산(이전 검토는 서류 검수 기준).
8. 서류 검수 코드 유지 여부 결정.

## 관련 문서

- [PROJECT_PLAN.md](PROJECT_PLAN.md): 현재 상태, 다음 작업, 정할 것
- [docs/README.md](docs/README.md): 문서 지도
- [docs/adr/ADR-023.md](docs/adr/ADR-023.md): 전환 결정
- [docs/research/](docs/research/tts-literature.md): 조사 기록
- [docs/experiments/](docs/experiments/README.md): 실험 요약과 EXP-006 사전 등록
- [docs/archive/document-review/](docs/archive/document-review/): 이전 제품(서류 검수) 문서
