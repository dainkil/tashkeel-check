# Tashkeel Check — 현재 상태

- 프로젝트/레포 이름: `tashkeel-check`
- 마지막 업데이트: 2026-10-22 (제출본 기준으로 문서 전체 정리)
- 상태: **제출본 확정.** 단일 문서 검수 서비스(파일 업로드 → 조건 M2 → 회사 사전·보관함 덧씌움 → 사람 확정 → 회사 사전)를 Docker Compose 패키지로 낸다. 정확도는 C1(지시문 p1)을 합성 시험지로만 쟀고, 기본 경로 M2는 재지 않았다.
- 문서 역할: 현재 상태, 남은 일, 정할 것만 둔다. 제품 설명은 [README.md](README.md), 본문은 `docs/`([문서 지도](docs/README.md)), 지난 진행 기록은 [docs/archive/](docs/archive/README.md)에 있다.

> **작업을 시작하기 전에 이 문서와 [docs/README.md](docs/README.md)를 읽는다. 계획·범위·구조·데이터·평가 방식이 바뀌면 해당 `docs/` 문서를 고치고 [docs/changelog.md](docs/changelog.md)에 이유와 영향을 적는다. 기술 결정은 [docs/adr/](docs/adr/README.md), 재현 가능한 오류는 [docs/troubleshooting.md](docs/troubleshooting.md), 측정은 [docs/experiments/](docs/experiments/README.md)에 남긴다. 작업을 마칠 때 이 문서와 [docs/roadmap.md](docs/roadmap.md)의 기능 상태를 실제 결과에 맞게 고친다.**
>
> 완료 여부는 실제 구현·실행·확인 결과를 기준으로 쓴다. 실행하지 않은 실험이나 검증을 완료했다고 기록하지 않는다.

## 제출본 한눈에

| 항목 | 내용 | 근거 |
| --- | --- | --- |
| 제품 | 아랍어 서류의 이름(사람·회사·기관)마다 읽기 후보를 근거와 함께 보여 주고, 근거가 없으면 보류한다. 사람이 확정한 표기만 회사 사전에 쌓아 다음 서류에서 바로 확정한다 | [ADR-021](docs/adr/ADR-021.md) |
| 고객 | 걸프(사우디·UAE)에 진출한 외국 중소기업의 내부 검토 | [ADR-021](docs/adr/ADR-021.md) |
| 기본 경로 | 조건 M2: 번역 agent와 검증 agent가 동시에 돌고, 회사 기록 MCP 툴로 사전과 지난 서류(보관함)를 찾고, 코드 중재자가 확정한다. `REVIEW_CONDITION=C1`로 측정한 설정으로 되돌린다 | [ADR-022](docs/adr/ADR-022.md), [architecture.md 4.7절](docs/architecture.md) |
| 확정 규칙 | 이번 문서 안 근거(두 agent 일치 + 코드 근거 검사) 또는 사람이 확정한 사전만 확정. 보관함과 LLM은 제안만 | [ADR-010](docs/adr/ADR-010.md), [ADR-022](docs/adr/ADR-022.md) |
| 전달 형태 | FastAPI + 화면(`#/upload`, `#/result/{id}`), API 키 인증·고객 분리·사용량, Postgres(없으면 메모리), Docker Compose | [ADR-019](docs/adr/ADR-019.md), [deploy.md](docs/deploy.md) |
| 확인한 것 | 테스트 559개 통과(Postgres 포함, ADR-022 기록). 실제 모델로 M2 작동 확인 2회(형식 통과, 오류 0)와 README 화면 촬영 | [과제2-테스트-기록 8.3·8.6절](docs/과제2-테스트-기록.md) |
| 측정한 것 | 합성 시험지(70문서, 이름 부분 1,457개)에서 C1(지시문 p1) 엄격 0.9993·안전 1.0 | [EXP-003](docs/experiments/EXP-003.md), [실험 요약](docs/experiments/README.md) |
| 알려진 한계 | M2 미측정, M2 전체 이름·단어별 항목 겹침(TS-005, 미해결), 보관함은 같은 철자의 다른 대상을 제안할 수 있음, 실제 서류 측정 없음 | [README 알려진 한계](README.md#알려진-한계), [TS-005](docs/troubleshooting.md) |

## 아직 하지 않은 것

- 조건 M2(서비스 기본값)의 측정: 단일 문서 정확도(C1 대비), 보관함 제안 적중률, 이름이 같은 다른 대상을 잘못 제안하는 비율, 문서당 비용·시간(EXP-005 [제안], [evaluation.md 6.6절](docs/evaluation.md)). 합성 보관함 사례 데이터도 없다.
- TS-005 해결(제출본에서는 고치지 않고 알려진 한계로 둔다).
- EXP-003 사전 등록한 사람 확인(`errors.csv`: C1~C3 오류 5건과 정답 표본, C1p0·C0 오류)과 synthetic-hard 아랍어 문장의 사람 검수.
- 실제 서류 측정(공개 이중언어 문서 후보의 이용 조건 확인부터).
- OCR 실제 호출(키 없음), Postgres 보관함에 실제 OpenAI 임베딩을 넣은 실행, M2 반영 뒤 `docker compose up --build` 재확인.
- 보류한 것: EXP-002 나머지 240회, 묶음 검수와 M1의 실제 모델 실행.

## 다음 작업 (제출 뒤)

[README 향후 계획](README.md#향후-계획), [roadmap.md 2절](docs/roadmap.md)과 같은 순서다.

1. M2 측정(EXP-005 [제안]). 판정 기준을 먼저 적는다: synthetic-hard dev에서 안전 오류 0·엄격 ≥ C1 − 0.01, 합성 보관함 사례에서 보관함 자동 확정 0·고객 간 노출 0·이름이 같은 다른 대상 잘못 제안 ≤ 0.05, 코드만 쓰는 보관함 조회(A0)와 비교. dev 약 $7 [추정]. 나쁘면 `REVIEW_CONDITION=C1`로 되돌린다.
2. 외부 MCP 클라이언트용 `/mcp` 공개(streamable HTTP, API 키로 고객 결정, 읽기 도구만).
3. TS-005 해결: 중재자에서 겹치는 항목을 짝짓는 방향을 검토한다.
4. 자기 회사 표기 감시(F19 [제안]): 자기 회사를 거래처 0번으로 등록하고 서류의 회사명·등기번호·세금번호가 다르면 경고한다. 근거 규칙은 출처를 찾은 뒤에만 쓴다.
5. OCR 실제 호출 1회(연결 확인만)와 무료 등급 제한 확인. 로컬 백엔드는 민감 서류 요구가 생기면.
6. Postgres에 사전·보관함을 둔 실행과 `docker compose up --build` 재확인. 스모크(`scripts/smoke.sh`)는 아직 묶음 검수(보류 기능) 경로로 돌므로 서류 업로드 → M2 흐름으로 바꾼다.
7. 중소기업 서류(거래처 계약, 정부 통지, 임대차, 인보이스, 근로계약)로 합성 문서 생성기 v3. 측정은 사용자 동의 뒤.
8. EXP-003 `errors.csv` 사람 확인과 공개 이중언어 문서로 실제 서류 측정.
9. 사전 키를 거래처 단위로 나눌지 결정.

## 사용자가 정할 것

- M2를 측정할지(EXP-005, dev 약 $7 [추정])와, 결과가 C1보다 나쁘면 기본값을 C1로 되돌릴지
- 외부 `/mcp` 공개 시점
- TS-005를 고치는 방향(중재자에서 겹치는 항목을 짝짓기 / 지시문에서 단어 단위 강제 / 화면에서 단어별 항목 우선)
- 회사 사전 키를 거래처 단위로 나눌지(지금은 고객 전체 `"*"`)
- OCR 백엔드: 무료 API(제3자 전송)를 그대로 둘지, 로컬 백엔드를 만들지
- 보류한 것을 다시 열지: EXP-002 나머지 240회(쉬운 시험지라 조건 차이를 가르지 못함), 묶음 검수(서류 우선순위, 이름 기반 후보 연결을 제안으로 보여 줄지), M1
- 사업성 검토를 지금 고객(ADR-021) 기준으로 다시 계산할지([보관 자료](docs/archive/business/feasibility.md)는 KYC·셀프서브 기준)
- `uv run pre-commit install`로 커밋 훅을 켤지, LangSmith 키를 바꿀지(지금 키는 401로 거부됨)
