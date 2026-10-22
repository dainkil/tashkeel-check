# 문서 지도

- 마지막 업데이트: 2026-10-22 (제출본 기준 정리)
- 현재 상태와 남은 일은 루트 [PROJECT_PLAN.md](../PROJECT_PLAN.md), 제품 소개와 실행 방법은 [README.md](../README.md), 작업 규칙은 [AGENTS.md](../AGENTS.md)에 있다.
- 아래 문서는 모두 제출본(현재 코드)을 기준으로 쓴다. 지난 계획·진행 경과는 [archive/](archive/README.md)와 [changelog.md](changelog.md)에 있다.

## 지금 기준 문서

| 문서 | 내용 | 이것이 바뀌면 고친다 |
| --- | --- | --- |
| [problem-and-goals.md](problem-and-goals.md) | 해결하려는 문제, 고객, 서비스 목표 G1~G7과 상태, 질문 Q0~Q3과 답, 요구사항 | 제품이 약속하는 것, 목표, 요구사항 |
| [scope.md](scope.md) | 제출본에 들어간 것 / 코드만 있고 보류한 것 / 범위 밖, 사용자가 확정한 것, 아직 정하지 않은 것 | 범위, 사용자 결정 |
| [architecture.md](architecture.md) | 설계 원칙, 그래프와 조건 M2, 산출물 형식, 스키마·강등 규칙, 툴, 저장소 구조·API·DB 표·기술 스택·명령, 코드 대조 | 노드·조건·스키마·툴·모듈·API·DB |
| [data.md](data.md) | 데이터별 용도와 버전, Wikidata 걸프 인명, 합성 문서, 어려운 합성 문서(synthetic-hard), 합성 묶음 | 데이터 출처·생성 규칙·버전 |
| [evaluation.md](evaluation.md) | 지금 유효한 기준, 지표 정의(EXP-001~003, 묶음 검수, M2 [제안]), 실행마다 기록할 것 | 지표 정의, 판정 규칙, 기록 항목 |
| [roadmap.md](roadmap.md) | 기능 F1~F20(F18 없음)과 상태, 제출 뒤 다음 작업, 위험 | 기능 상태, 다음 작업 |
| [deploy.md](deploy.md) | Docker Compose 패키지 운영 절차(설정, 첫 고객 키, 스모크, 업그레이드·백업) | 배포 절차 |
| [과제2-테스트-기록.md](과제2-테스트-기록.md) | 제출본의 실행 방법, 기능별 테스트, 예외 테스트, 실제 모델 작동 확인, 화면 캡처 | API·화면·DB·MCP 동작이 바뀌면 다시 실행해 갱신 |
| [experiments/](experiments/README.md) | 프로젝트 중 한 측정의 핵심 요약(M0, EXP-001~003, EXP-005 [제안])과 실험별 상세 기록 | 비교 실험을 하거나 결과를 고칠 때 |
| [adr/](adr/README.md) | 기술 결정 ADR-001~022(배경 · 결정 · 결정 이유 · 고려한 대안 · 최종 결정) | 중요한 결정. 뒤집으면 새 ADR을 추가해 연결 |
| [troubleshooting.md](troubleshooting.md) | 재현 가능한 오류와 해결 과정 TS-001~005 | 오류를 찾거나 고칠 때 |
| [changelog.md](changelog.md) | 계획·범위·구조 변경 이력(날짜, 내용, 이유, 영향) | 모든 계획·범위·구조 변경 |
| [../data/synthetic/README.md](../data/synthetic/README.md), [../data/synthetic-hard/README.md](../data/synthetic-hard/README.md) | 합성 문서 파일 형식 | 생성기 출력 형식 |

## 보관 문서

[archive/](archive/README.md)에 둔다. 지금 제품을 설명하지는 않지만 결정의 근거나 과정을 찾아볼 때 쓴다.

| 문서 | 내용 |
| --- | --- |
| [archive/business/](archive/business/feasibility.md) | 사업성 검토와 시장 조사(KYC·셀프서브 기준, ADR-008·009 시점) |
| [archive/progress-log.md](archive/progress-log.md) | 단계별 완료 기록(2026-10-13 ~ 10-21) |
| [archive/README.md](archive/README.md) | 보관 목록, 정리 때 지운 것과 찾는 방법 |

## 절 번호

문서 안의 절 번호(예: architecture 4.5절, data 5.3절, evaluation 6.4절)는 2026-10-20에 단일 계획 문서를 나눌 때의 번호를 그대로 쓴다. 코드 주석·ADR·실험 기록이 이 번호를 인용하므로 남은 절의 번호는 바꾸지 않는다. 문서별 번호대는 problem-and-goals 1, scope 2·3, architecture 4, data 5, evaluation 6이다.

## 근거 표기

| 표시 | 뜻 |
| --- | --- |
| [확인] | 이 프로젝트에서 직접 실행하거나 조회한 결과 |
| [문헌○] | 조사로 확인한 외부 자료. 인용 전에 원문을 다시 확인한다 |
| [제안] | 아직 확정·검증하지 않은 설계안이나 수치 |
| [가설] | 실험으로 확인할 추정 |
| [추정] | 계산이나 외삽으로 낸 값 |
| [미확인] | 아직 모르는 값 |

## 문서 규칙

- 지금 기준 문서는 현재 코드와 제출본을 현재형으로 쓴다. 날짜별 경과는 changelog·ADR·archive에 둔다.
- 짧게, 결론부터 쓴다. 확인한 사실과 가정을 구분하고, 출처 없는 수치는 만들지 않는다.
- 합성 문서 결과를 실제 서류의 오류율이나 포착률로 쓰지 않는다. 측정하지 않은 설정(지금은 M2)의 성능을 쓰지 않는다.
- 고유명사는 사람·회사·기관 등 명명된 대상 전체를 가리킨다. 사람 이름만인 것처럼 쓰지 않는다.
- "번역기 정확도가 떨어진다"는 일반 주장은 쓰지 않는다. "reward hacking" 대신 "모호성 은폐(specification gaming의 한 형태)"라고 쓴다.
- 대용량 데이터와 실험 산출물은 문서에 넣지 않고 저장 위치와 재현 방법을 적는다.
- 새 문서를 만들면 이 지도에 한 줄을 더한다. 문서를 보관하면 [archive/README.md](archive/README.md)에 사유와 원래 위치를 적는다.

## 테스트 원칙

- analyze, reconcile, romanize, match_spelling, 덧씌움(사전·보관함)은 LLM 없이 도는 단위 테스트를 둔다.
- 그래프 전체(C0~C3, M1, M2)는 가짜 모델로 결정적 테스트를 둔다.
- 골든 스냅숏 160건과 LLM 입력 해시는 동작 보존의 기준이라 리팩토링으로 다시 만들지 않는다([ADR-013](adr/ADR-013.md)).
- 실제 LLM이 필요한 테스트는 `live` 마커, Postgres가 필요한 테스트는 `db` 마커로 분리한다.
