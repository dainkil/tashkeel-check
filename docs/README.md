# 문서 지도

- 마지막 업데이트: 2026-10-23 (TTS 전환, [ADR-023](adr/ADR-023.md))
- 현재 상태와 남은 일은 루트 [PROJECT_PLAN.md](../PROJECT_PLAN.md), 제품 소개는 [README.md](../README.md), 작업 규칙은 [AGENTS.md](../AGENTS.md)에 있다.
- 지금 기준 문서는 TTS 앞단 층 계획을 기준으로 쓴다. **코드는 아직 이전 제품(서류 검수, 2026-10-22 제출본)이다.** 이전 제품 문서는 [archive/document-review/](archive/document-review/)에, 경과는 [changelog.md](changelog.md)에 있다.

## 지금 기준 문서

| 문서 | 내용 | 이것이 바뀌면 고친다 |
| --- | --- | --- |
| [problem-and-goals.md](problem-and-goals.md) | 해결하려는 문제(언어·업무·도구 세 층), 고객, 서비스 목표 G1~G7(모두 미측정), 실험으로 답할 질문 Q1~Q5, 요구사항 FR·NFR [제안] | 제품이 약속하는 것, 목표, 요구사항 |
| [scope.md](scope.md) | 단계(서류 검수 완료·보관 → 전환 조사 → 0~3단계), 들어가는 것 / 코드만 있고 보류한 것(서류 검수 전체) / 범위 밖, 사용자가 확정한 것, 아직 정하지 않은 것 | 범위, 사용자 결정 |
| [architecture.md](architecture.md) | 설계 원칙 8개, 두 경로(오프라인·실시간), 지금 코드에서 가져가는 것·바꾸는 것·새로 만드는 것 표, 새 모듈·API·DB [제안], 엔진 지원 매트릭스(문서 기준) | 경로·모듈·API·DB·엔진 |
| [data.md](data.md) | Wikidata 걸프 인명(재사용), CamelProp, 자체 라벨 계획, 합성 발화 생성기 [제안], 음성 코퍼스 이용 조건, 고객 데이터 | 데이터 출처·라벨 규칙·버전 |
| [evaluation.md](evaluation.md) | 이름 단위 발음 오류율(사람 청취 객관식), ASR 왕복(선별), 강제 정렬 PER, 후보 포함률, 엔진 지원 판정, 확정 규칙 지표, 확신 보정, 지연, 반복 간 일치, 기록 항목, 판정 원칙 | 지표 정의, 판정 규칙 |
| [roadmap.md](roadmap.md) | 기능 T1~T14와 상태(기존 재사용 / 제안), 다음 작업, 위험 | 기능 상태, 다음 작업 |
| [deploy.md](deploy.md) | Docker Compose 패키지 운영 절차(이전 제품 기준, 코드가 그대로라 지금도 유효) | 배포 절차 |
| [과제2-테스트-기록.md](과제2-테스트-기록.md) | 이전 제품(서류 검수 서비스)의 실행 방법·기능별 테스트·화면 캡처. 코드가 그대로라 유효 | API·화면·DB·MCP 동작이 바뀌면 |
| [발표자료.pptx](발표자료.pptx), [발표자료.pdf](발표자료.pdf) | 이전 제품(서류 검수)의 고객용 소개 발표(13장). TTS 기준 발표는 없다 | TTS 발표를 만들면 교체 |
| [research/tts-literature.md](research/tts-literature.md) | TTS 전환 근거 조사(2026-10-23): 이름 발음 방법론·평가, 아랍어 TTS·디아크리타이저·엔진 발음 제어, 실시간 파이프라인, 옛 음성 계획 문헌, 공백 | 새 조사를 하거나 원문을 다시 확인하면 |
| [research/document-review-quality.md](research/document-review-quality.md) | 전환 직전 서류 검수 제품 품질 진단과 문헌(실행하지 않음, 기록용) | 서류 검수를 다시 열 때 |
| [experiments/](experiments/README.md) | 실험 요약(TTS: EXP-006 [제안]·EXP-007 [제안]; 서류 검수: M0·EXP-001~003 한 줄 결과)과 실험별 기록. [EXP-006](experiments/EXP-006.md) 사전 등록 초안 | 실험을 하거나 결과를 고칠 때 |
| [adr/](adr/README.md) | 기술 결정 ADR-001~023(배경 · 결정 · 결정 이유 · 고려한 대안 · 최종 결정) | 중요한 결정. 뒤집으면 새 ADR을 추가해 연결 |
| [troubleshooting.md](troubleshooting.md) | 재현 가능한 오류와 해결 과정 TS-001~005(서류 검수 때) | 오류를 찾거나 고칠 때 |
| [changelog.md](changelog.md) | 계획·범위·구조 변경 이력(날짜, 내용, 이유, 영향) | 모든 계획·범위·구조 변경 |
| [../data/synthetic/README.md](../data/synthetic/README.md), [../data/synthetic-hard/README.md](../data/synthetic-hard/README.md) | 서류 검수용 합성 문서 파일 형식(테스트가 쓴다) | 생성기 출력 형식 |

## 보관 문서

[archive/](archive/README.md)에 둔다. 지금 제품을 설명하지는 않지만 결정의 근거나 과정을 찾아볼 때 쓴다.

| 문서 | 내용 |
| --- | --- |
| [archive/document-review/](archive/document-review/problem-and-goals.md) | 이전 제품(서류 검수, 제출본 2026-10-22)의 정의·범위·구조·데이터·측정·로드맵과 실험 요약. 코드가 아직 이 제품이므로 코드를 읽을 때는 이 문서가 맞다 |
| [archive/business/](archive/business/feasibility.md) | 사업성 검토와 시장 조사(KYC·셀프서브 기준) |
| [archive/progress-log.md](archive/progress-log.md) | 단계별 완료 기록(2026-10-13 ~ 10-21) |
| [archive/README.md](archive/README.md) | 보관 목록, 정리 때 지운 것과 찾는 방법 |

## 절 번호

- 지금 기준 문서의 절 번호는 2026-10-23에 새로 시작했다(problem-and-goals 1.1~1.4, scope 2·3, architecture 4.1~4.9, data 5.1~5.6, evaluation 6.1~6.11). 문서별 번호대(1·2/3·4·5·6)는 이전과 같다.
- 코드 주석·ADR-001~022·실험 기록 EXP-001~003·troubleshooting이 인용하는 옛 절 번호(예: architecture 4.5절, data 5.3절, evaluation 6.4절)는 [archive/document-review/](archive/document-review/)의 보관본을 가리킨다. 보관본의 절 번호는 바꾸지 않았다.

## 근거 표기

| 표시 | 뜻 |
| --- | --- |
| [확인] | 이 프로젝트에서 직접 실행하거나 조회한 결과 |
| [문헌○] | 조사로 확인한 외부 자료(URL을 열어 봄). 인용 전에 원문을 다시 확인한다 |
| [미확인] | 2차 요약·초록·모델 카드만 본 것, 또는 아직 모르는 값 |
| [제안] | 아직 확정·검증하지 않은 설계안이나 수치 |
| [가설] | 실험으로 확인할 추정 |
| [추정] | 계산이나 외삽으로 낸 값 |

## 문서 규칙

- 지금 기준 문서는 TTS 앞단 층 계획을 현재형으로 쓰되, 코드가 아직 이전 제품임을 숨기지 않는다. 날짜별 경과는 changelog·ADR·archive에 둔다.
- 짧게, 결론부터 쓴다. 확인한 사실과 가정을 구분하고, 출처 없는 수치는 만들지 않는다.
- 공개 이름 벤치 결과를 고객 이름의 오류율로 쓰지 않는다. 측정하지 않은 엔진·설정의 성능을 쓰지 않는다. 서류 검수 때의 측정값을 TTS 제품의 성능으로 쓰지 않는다.
- 고유명사는 사람·회사·기관·지명 등 명명된 대상 전체를 가리킨다. 사람 이름만인 것처럼 쓰지 않는다.
- "엔진 정확도가 떨어진다"는 일반 주장은 쓰지 않는다. 엔진·모델·로케일·입력 형식·날짜를 붙인다. "reward hacking" 대신 "모호성 은폐(specification gaming의 한 형태)"라고 쓴다.
- 발음 정확도는 사람 청취로 잰 값만 "정확도"라고 쓴다. MOS·자동 심판·ASR 왕복 값은 그 이름대로 쓴다.
- 대용량 데이터와 합성 음성은 문서에 넣지 않고 저장 위치와 해시·재현 방법을 적는다.
- 새 문서를 만들면 이 지도에 한 줄을 더한다. 문서를 보관하면 [archive/README.md](archive/README.md)에 사유와 원래 위치를 적는다.

## 테스트 원칙

- 서류 검수 코드의 테스트(단위·골든 160건·LLM 입력 해시·`live`·`db` 마커)는 동작 보존 기준으로 그대로 둔다([ADR-013](adr/ADR-013.md)).
- TTS 코드가 생기면: 실시간 경로는 같은 입력에 같은 출력(결정성) 테스트, 자음 골격 불변 테스트, 교차 고객 노출 0 테스트, 엔진 어댑터는 녹음된 응답으로 결정적 테스트를 둔다. 실제 엔진·LLM이 필요한 테스트는 `live` 마커로 분리한다 [제안].
