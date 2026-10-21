# 문서 지도

- 마지막 업데이트: 2026-10-21
- 현재 상태와 다음 작업은 루트 [PROJECT_PLAN.md](../PROJECT_PLAN.md)에 있다. 작업 규칙은 [AGENTS.md](../AGENTS.md).

## 무엇이 어디에 있는가

| 문서 | 내용 | 이것이 바뀌면 고친다 |
| --- | --- | --- |
| [problem-and-goals.md](problem-and-goals.md) | 정의, 문제의 세 층, 대상 고객, 서비스 목표 G1~G7, 질문 Q0~Q3, 기능·비기능 요구사항 | 제품이 약속하는 것, 목표값, 요구사항 |
| [scope.md](scope.md) | 단계 1 / 1.5 / 2 / 3의 위치, 단계 1에 넣는 것·뺀 것, 사용자가 확정한 것과 확인한 것 | 범위, 합격선·중단 기준, 모델·규모 결정 |
| [architecture.md](architecture.md) | 설계 원칙, 그래프, 산출물, 조건 C0~C3, 출력 스키마·강등 규칙, 툴, 스택, 저장소 구조, 코드 대조 | 노드·조건·스키마·툴·모듈 구조 |
| [data.md](data.md) | Wikidata 걸프 인명(스냅숏·이름 풀·정렬 규칙), 합성 문서(규칙·근거 배치·정답·분할), 어려운 합성 문서 synthetic-hard(5.3절: 정답 규칙·유형 A1~D5), 합성 묶음(5.4절: 사례 9 × 종류 3) | 데이터 출처·생성 규칙·버전 |
| [evaluation.md](evaluation.md) | EXP-001 지표 M1~M6, EXP-002 지표·판정, 실행마다 기록할 것, EXP-003 99% 기준(6.4절: 엄격 철자·근거 검사 v2·채점 v2), 묶음 검수 지표(6.5절) | 지표 정의, 판정 규칙, 기록 항목 |
| [roadmap.md](roadmap.md) | 기능 F1~F14, 제품 스택·시스템 구성·API 초안·데이터 모델, 마일스톤 M0~M6, 테스트 전략, 단계별 체크리스트, 위험 | 기능·일정·제품 설계, 체크리스트 |
| [changelog.md](changelog.md) | 계획 변경 이력 표와 날짜별 완료 기록 | 모든 계획·범위·구조 변경(이유와 영향을 함께) |
| [adr/](adr/README.md) | 기술 결정 기록 ADR-001~018, 한 결정 한 파일 | 중요한 기술 결정. 뒤집으면 새 ADR을 추가해 연결 |
| [troubleshooting.md](troubleshooting.md) | TS-001~003 | 재현 가능한 오류와 해결 과정 |
| [experiments/](experiments/README.md) | 실험 목록, 템플릿, EXP-001·EXP-002(보류)·EXP-003(사전 등록) 기록 | 모델·프롬프트·규칙·도구 정책이 바뀐 비교 실험 |
| [과제2-테스트-기록.md](과제2-테스트-기록.md) | 단계 1.5 서비스의 실행 방법, 기능별 테스트 16건, 예외 테스트 7종, 단계 2 묶음 검수 기능 19건·예외 9종(5절), 화면 캡처(`images/`) | API·화면·DB·MCP 동작이 바뀌면 다시 실행해 갱신 |
| [business/feasibility.md](business/feasibility.md) | 사업성 검토(시장성·기술성·경제성) | 사업 판단, 가격·고객 수 가정 |
| [business/market/](business/market/) | 시장 조사 기록, 출처 목록, 재계산 스크립트 | 조사 추가·출처 갱신 |
| [../data/synthetic/README.md](../data/synthetic/README.md) | 합성 문서 파일 형식 | 생성기 출력 형식 |
| [../data/synthetic-hard/README.md](../data/synthetic-hard/README.md) | 어려운 합성 문서 파일 형식(gold 형식 2) | synthetic-hard 생성기 출력 형식 |

## 절 번호 안내

`PROJECT_PLAN.md`는 2026-10-20에 위 문서들로 분할했다. 분할 전 절 번호(예: "4.5절", "6.2절")는 각 문서 안에서 그대로 유지하므로, 다른 문서·코드 주석·실험 기록이 인용하는 번호는 아래 표로 찾는다.

| 분할 전 절 | 지금 위치 |
| --- | --- |
| 1절 | problem-and-goals.md |
| 2절, 3절 | scope.md |
| 4절 | architecture.md (4.9 툴 상세, 4.10 실행 환경, 4.11 코드 대조는 분할 때 더함) |
| 5절 | data.md |
| 6절 | evaluation.md |
| 7절, 14절 | 이 문서 |
| 8절 | roadmap.md 4절 |
| 9절 | 완료 기록은 changelog.md, 다음 작업·사용자가 정할 것은 PROJECT_PLAN.md, 위험 목록은 roadmap.md 5절, 실행 환경은 architecture.md 4.10 |
| 10절 | changelog.md |
| 11절 | adr/ |
| 12절 | troubleshooting.md |
| 13절 | experiments/README.md |

## 근거 표기

### 근거 표기

| 표시 | 뜻 |
| --- | --- |
| [확인] | 이 프로젝트에서 직접 실행하거나 조회한 결과 |
| [문헌○] | 조사로 확인한 외부 자료. 인용 전에 원문을 다시 확인한다 |
| [제안] | 아직 확정·검증하지 않은 설계안이나 수치 |
| [가설] | 실험으로 확인할 추정 |
| [미확인] | 아직 모르는 값 |

## 산출물과 문서 규칙 (구 7절)

| 산출물 | 내용 |
| --- | --- |
| `docs/problem-and-goals.md` | 문제 정의, 서비스 목표 G1~G7, 질문 Q0~Q3, 기능·비기능 요구사항(요구사항마다 충족하는 노드나 툴을 연결) |
| `docs/architecture.md` | 설계 원칙, mermaid 그래프, 조건 C0~C3, 스키마·강등 규칙, 툴, 스택, 저장소 구조, 코드 대조 |
| `docs/architecture.md` 4.9절 | 툴마다 이름, 입력·출력 스키마, 호출 시점, 실패 시 동작. 일반 함수의 정규화·일치 규칙 |
| `docs/roadmap.md` | 단계 1~3을 제품 관점으로 묶은 주요 기능 선정(F1~F14, 선정 기준·우선순위), 기술 스택·시스템 구성(구성도, API 초안, 데이터 경계), 마일스톤 M0~M6과 테스트 전략 |
| `docs/experiments/EXP-001.md`, `EXP-002.md`, `EXP-003.md` | `docs/experiments/README.md` 템플릿 형식의 실험 기록 |
| `docs/business/market/` | 시장 조사 기록(가격·고객 수, 긍정 근거), 출처 목록(`sources.csv`), 사업성 검토 경제성 재계산 스크립트(`recalc_economics.py`, 긍정 근거 시나리오 `recalc_upside.py`, 수요·공급 계산 `recalc_demand_supply.py`, ADR-008 이후 현재 구조의 추정 `recalc_gulf.py`). 수요·공급·경쟁 보고서는 `reports/`, 그 조사 노트 다섯 갈래는 `research_notes/`에 있다. 사업성 검토(`docs/business/feasibility.md`)의 가정을 출처 있는 값으로 바꾸는 근거 |
| 코드·데이터·테스트 | 명령 한 줄로 EXP-001, 명령 한 줄로 합성 문서 1개 실행(JSON·CSV 출력) |

문서는 과제 보고서에 들어가므로 각각 한두 쪽으로 짧게, 결론부터 쓴다. 구현하다 설계가 바뀌면 문서도 같이 고친다.

문서 표현 규칙:

- "번역기 정확도가 떨어진다"는 일반 주장은 쓰지 않는다.
- "reward hacking" 대신 "모호성 은폐(specification gaming의 한 형태)"라고 쓴다.
- 제품이 약속하는 것은 "모호 구간을 얼마나 잡아내는가"다.
- 확인한 사실과 가정을 구분하고, 출처 없는 수치는 만들지 않는다.
- 합성 문서 결과를 실제 서류의 오류율이나 포착률로 쓰지 않는다.

테스트:

- analyze, reconcile, romanize, match_spelling은 LLM 없이 도는 단위 테스트를 둔다.
- 그래프 전체는 가짜 모델(스크립트된 tool call)로 결정적 테스트를 둔다. 강등 규칙, 미처리 집계, 인용 검증, 토큰 ID 검증을 확인한다.
- 실제 LLM이 필요한 테스트는 pytest 마커(`live`)로 분리한다. 번역 문장이 아니라 처분 종류, 근거 유무, 미처리 수 같은 구조만 확인한다.

## 문서 관리 원칙 (구 14절)

- `PROJECT_PLAN.md`를 현재 상태·다음 작업의 기준으로 유지한다. 본문은 이 디렉터리의 문서에 둔다.
- 루트 `README.md`는 외부용 소개다. 정의, 범위, 진행 단계, 알려진 한계가 바뀌면 `PROJECT_PLAN.md`·해당 문서와 함께 갱신한다.
- 작업 시작 시 `PROJECT_PLAN.md`를 읽고, 종료 시 실제 결과에 맞게 갱신한다.
- ADR은 `adr/`에 한 결정 한 파일, 트러블슈팅은 `troubleshooting.md`, 실험은 `experiments/`에 둔다. 2026-10-20에 단일 `PROJECT_PLAN.md`(1,118줄)를 이 구조로 분할했다(`changelog.md`).
- 대용량 데이터와 실험 산출물은 문서에 직접 넣지 않고 저장 위치와 재현 방법을 기록한다.
