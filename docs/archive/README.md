# 보관 문서

- 마지막 업데이트: 2026-10-23 (TTS 전환으로 서류 검수 기준 문서 보관)
- 여기 있는 문서는 지금 제품을 설명하지 않는다. 결정의 근거나 진행 과정을 나중에 찾아볼 때 쓴다. 지금 기준 문서는 [문서 지도](../README.md)에 있다.
- 보관한 문서의 내용은 고치지 않는다(옮기면서 링크 경로와, 2026-10-23 보관본에는 맨 위 안내 줄 하나만 고쳤다).

## 보관 목록

| 문서 | 무엇인가 | 왜 남겼나 | 원래 위치 |
| --- | --- | --- | --- |
| [document-review/](document-review/problem-and-goals.md) | 서류 검수 제품(제출본 2026-10-22)의 정의·목표(problem-and-goals), 범위(scope), 구조(architecture), 데이터(data), 측정(evaluation), 기능·로드맵(roadmap), 실험 요약(experiments-README) | 2026-10-23 TTS 전환(ADR-023). **코드는 아직 이 제품이므로 코드를 읽을 때는 이 문서가 맞다.** ADR-001~022·EXP-001~003·코드 주석이 인용하는 옛 절 번호(architecture 4.5절 등)는 이 보관본을 가리킨다. 복사 보관이라 원래 위치에는 TTS 기준으로 다시 쓴 같은 이름의 문서가 있다 | `docs/{problem-and-goals,scope,architecture,data,evaluation,roadmap}.md`, `docs/experiments/README.md` |
| [../발표자료.pptx](../발표자료.pptx), [../발표자료.pdf](../발표자료.pdf) | 서류 검수 제품의 고객용 소개 발표(13장). 파일은 `docs/`에 그대로 있다(이 폴더로 옮기지 않음) | TTS 기준 발표가 생기면 교체한다. 수치·화면이 서류 검수 기준이라 TTS 제품 설명에 쓰지 않는다 | `docs/발표자료.*` |
| [business/feasibility.md](business/feasibility.md) | 사업성 검토(시장성·기술성·경제성), KYC·컴플라이언스 팀 API와 셀프서브 기준 | 고객·가격 판단의 근거였고 ADR-008·009가 인용한다. 지금 고객(ADR-021, 중소기업 내부 검토) 기준으로 다시 계산하지 않았다 | `docs/business/` |
| [business/market/](business/market/saudi-price-customers.md) | 시장 조사(사우디 가격·고객 수, 긍정 근거, 수요·공급·경쟁 보고서와 조사 노트), 출처 목록 `sources.csv`, 재계산 스크립트 `recalc_*.py` | 위 검토의 수치 출처. 스크립트는 `python3 -I <경로>`로 다시 돌릴 수 있다 | `docs/business/market/` |
| [progress-log.md](progress-log.md) | 단계별 완료 기록(2026-10-13 ~ 10-21): M0 실제 모델 첫 점검, 실험 실행 수치, 구현 때 본 것 | 실험·결정의 세부 경과. 핵심 결과는 [실험 요약](../experiments/README.md)에 옮겨 두었다 | `docs/changelog.md`의 "상세 기록" |
| [test-records-bundle-review.md](test-records-bundle-review.md) | 묶음 검수(단계 2) 기능별·예외 테스트 기록과 화면 캡처 | 보류한 기능이지만 코드와 테스트는 남아 있다. 다시 열 때의 기준 기록 | `docs/과제2-테스트-기록.md` 5절 |

## 정리 때 지운 것

2026-10-22 제출본 정리에서 지금 기준 문서에서 뺀 내용이다. 따로 보관하지 않았고, 정리 직전 커밋 `d2e7fc9`에 그대로 있다. 예: `git show d2e7fc9:docs/roadmap.md`.

| 뺀 것 | 원래 위치 | 지금 어디서 보나 |
| --- | --- | --- |
| 마일스톤 M0~M6, 단계별 체크리스트, API·데이터 모델 초안, KYC 온보딩 흐름 | `docs/roadmap.md` | 실제 API·DB 표는 [architecture.md 4.8절](../architecture.md), 기능 상태는 [roadmap.md](../roadmap.md) |
| 날짜별 "정한 것·확인한 것" 목록 | `docs/scope.md` | 지금 유효한 결정은 [scope.md](../scope.md)와 [ADR](../adr/README.md) |
| 진행 상황 서술, 취소선으로 지운 다음 작업, 끝난 결정 항목 | `PROJECT_PLAN.md` | [PROJECT_PLAN.md](../../PROJECT_PLAN.md), [changelog.md](../changelog.md) |
| 단계별로 덧붙인 저장소 구조 블록, 구현 중 관찰 | `docs/architecture.md` | 하나로 합친 구조는 [architecture.md 4.8절](../architecture.md) |
| 분할 전 절 번호 대응표, 구 7절 산출물 표 | `docs/README.md` | [문서 지도](../README.md) "절 번호" |
| ADR의 옛 형식(8칸)과 관련 코드·테스트 목록 | `docs/adr/*.md` | 커밋 `2ec18f4` |
