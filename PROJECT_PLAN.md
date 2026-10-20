# Tashkeel Check — 프로젝트 계획 허브

- 프로젝트/레포 이름: `tashkeel-check`
- 마지막 업데이트: 2026-10-20
- 현재 단계: 단계 1 구현 완료, EXP-001 완료, EXP-002 미실행. 사업 구조를 걸프 영어권 최종 사용자·사람 검수 없음으로 바꾸고 사업성 검토를 다시 추정함(ADR-008). 판매는 KYC·컴플라이언스 팀에 멀티 에이전트 API 우선(ADR-009). 인터뷰와 사람 검수는 추후 과제. 과제 2 요건에 따라 단계 1.5(서비스화: 웹 화면·API·Postgres·최소 MCP)를 계획에 추가함(ADR-012). 단계 1.5 전 리팩토링 완료(ADR-013, 동작 동일 확인). M0 항목 2·3 완료(실제 모델 C1·C2 첫 실행 통과, temperature 0 미지원 확인). M0 관찰을 바탕으로 EXP-002 전에 채점 정의와 합성 문서를 고침(ADR-014: 모호 판정 규칙은 유지, 일반 단어 미처리는 보조 지표, 중립 토큰 제외, 토큰 단위 집계, 보류 후보 적중률, 합성 문서 synthetic-v1). M0 항목 5로 EXP-002 합격선·중단 기준을 확정해 코드로 고정함(`docs/scope.md` 3절). EXP-001 개발용 표본에서 표기 일치·정렬 규칙을 v1로 고쳐 고정하고, 이름 풀과 합성 문서를 다시 만듦(ADR-015, synthetic-v2). EXP-001 main 측정 완료: M5(방언 허용) 0.502로 기준 0.5를 겨우 넘어(95% 구간 0.485~0.519) 분석기를 이름 후보 출처로 유지, 가문명은 0.418. **EXP-002는 미실행, 단계 1.5는 미구현**
- 문서 역할: 현재 상태·다음 작업·사용자가 정할 것만 여기 둔다. 본문(정의·범위·구조·데이터·측정·로드맵·ADR·이력)은 `docs/`에 있고, 지도는 [docs/README.md](docs/README.md)다. 2026-10-20에 1,118줄 단일 문서를 이 구조로 분할했다([changelog](docs/changelog.md)).

> **작업을 시작하기 전에 이 문서와 [docs/README.md](docs/README.md)를 읽는다. 작업 중 계획·범위·구조·데이터·평가 방식이 바뀌면 해당 `docs/` 문서를 최신 상태로 수정하고, [docs/changelog.md](docs/changelog.md)에 이유와 영향을 기록한다. 중요한 기술적 결정은 [docs/adr/](docs/adr/README.md)에, 문제와 해결 과정은 [docs/troubleshooting.md](docs/troubleshooting.md)에, 측정 결과는 [docs/experiments/](docs/experiments/README.md)에 남긴다. 작업을 마칠 때 이 문서의 상태·다음 작업과 [docs/roadmap.md](docs/roadmap.md) 체크리스트를 갱신한다.**
>
> 완료 여부는 실제 구현·실행·확인 결과를 기준으로 쓴다. 실행하지 않은 실험이나 검증을 완료했다고 기록하지 않는다.

## 문서 지도 (요약)

| 알고 싶은 것 | 문서 |
| --- | --- |
| 무엇을 왜 만드는가, 목표 G1~G6, 질문 Q0~Q3, 요구사항 | [docs/problem-and-goals.md](docs/problem-and-goals.md) |
| 단계와 범위, 사용자가 확정한 것 | [docs/scope.md](docs/scope.md) |
| 그래프·조건·스키마·툴·스택·모듈 구조 | [docs/architecture.md](docs/architecture.md) |
| Wikidata 인명, 합성 문서 | [docs/data.md](docs/data.md) |
| 지표 정의와 판정 규칙 | [docs/evaluation.md](docs/evaluation.md) |
| 기능 F1~F14, 제품 스택·API·DB 초안, 마일스톤, 체크리스트, 위험 | [docs/roadmap.md](docs/roadmap.md) |
| 무엇이 언제 왜 바뀌었나 | [docs/changelog.md](docs/changelog.md) |
| 기술 결정 ADR-001~015 | [docs/adr/](docs/adr/README.md) |
| 오류 기록, 실험 기록 | [docs/troubleshooting.md](docs/troubleshooting.md), [docs/experiments/](docs/experiments/README.md) |
| 사업성 검토, 시장 조사 | [docs/business/feasibility.md](docs/business/feasibility.md), [docs/business/market/](docs/business/market/) |

주요 명령은 [docs/architecture.md](docs/architecture.md) 4.8절, 실행 방법은 [README.md](README.md)에 있다.

## 아직 하지 않은 것

- EXP-002 실행
- 실제 모델의 실패율, 그리고 한 문서 안에서 확정과 보류를 나누는지. synthetic-v0의 dev_004·dev_001 C1·C2를 각 1회만 돌렸고(`docs/changelog.md` M0 기록), 섞인 문서는 아직 돌리지 않았다 [미확인]
- 실제 모델로 C0·C3 실행
- C0 판정 규칙의 사람 확인(20건)

## 다음 작업

과제 2 서비스화(단계 1.5, 사용자 지시 후 착수, `docs/roadmap.md` 4절 체크리스트 순서):

1. API와 작업 실행(`web/app.py`, `web/jobs.py`, `runner.Reviewer`의 `on_node` 콜백. 응답 형식은 `results.ReviewResult`, 오류는 `errors`로 400·503) → 2. Postgres(`web/db.py`, `web/models.py`, Alembic, `docker-compose.yml`) → 3. 화면(`web/static/index.html`) → 4. MCP(`mcp/`) → 5. `tashkeel serve`·`run.sh`·`Dockerfile` → 6. 테스트와 `docs/과제2-테스트-기록.md`, 화면 캡처 → 7. README 실행 방법·변경 파일 설명 갱신, `docs/architecture.md` 4.8절을 [확인]으로 바꿈.

실험(기존):

1. ~~`.env`에 `OPENAI_API_KEY`를 넣는다~~ (2026-10-20 확인: 있음). LangSmith 추적을 쓰려면 `LANGSMITH_API_KEY`를 더한다.
2. ~~M0 항목 2·3: 실제 모델로 dev 문서 1개를 C1·C2로 돌리고 temperature를 확인한다~~ (2026-10-20 완료, `docs/changelog.md` M0 기록). dev_001 C1·C2도 실행해 둘 다 이름을 전부 보류했다. 다음 확인 [제안]: 새 dev 문서(synthetic-v2) 가운데 "일부 역할만" 배치 문서 하나(예: dev_005, 위임장, 회사만 근거 있음)를 C0·C1로 돌려, 지시 없이도 후보를 표시하는지(Q1)와 한 문서 안에서 확정·보류를 나누는지 본다(2회 호출).
3. ~~M0 항목 4: 모호 판정 규칙과 묶인 지표 정의, 합성 문서 보강~~ (2026-10-20 완료, ADR-014). ~~M0 항목 5: 합격선과 중단 기준~~ (2026-10-20 사용자 확정, `docs/scope.md` 3절).
4. ~~EXP-001: dev로 규칙 고정 → main 1회~~ (2026-10-20 완료. M5 방언 허용 0.502, 기준 통과, 여유 거의 없음).
5. EXP-002: `uv run tashkeel exp002 --split eval --yes`(360회).

사업 쪽(ADR-008 이후, 인터뷰·사람 검수 없이):

1. ~~EXP-002의 중단 기준을 실행 전에 정한다~~ (2026-10-20 확정: C1이 합격선을 넘으면 중단, `docs/scope.md` 3절).
2. 공개 이중언어 문서 후보(사우디 법령 공식 영역본, 상장사 아랍어·영어 공시의 이사 이름, UAE 법령 포털)의 공개 여부와 이용 조건을 확인한다. 사람 라벨 없이 실제 문서를 잴 유일한 경로다.
3. UAE 번역료(장당 150디르함, 이전 판 값)를 다시 확인한다. 걸프 가중 가격의 42%가 이 값에 달려 있다.
4. 합성 KYC 온보딩 묶음(아랍어 상업등기 + 영문 여권 MRZ + 정관)을 생성기로 만들고, 묶음 근거 검색(`rag/bundle.py` 틀)으로 상업등기 이름이 여권 표기로 확정되는 비율과 근거 없는 확정 비율을 잰다(ADR-009).
5. 단계 3 멀티 에이전트를 같은 지표로 비교한다. 격리된 검증 에이전트가 단일 에이전트보다 말없이 찍는 비율을 낮추지 못하면 단일 에이전트 API로 판다.

추후 과제(할 수 없음): 실무자 인터뷰, 아랍어 검수자를 쓰는 사전 감사, 이름 외 보류 구간의 번역가 연결, 무료 체험과 판매 경로 시험, 엔터프라이즈 인증. 이전 구조의 사업 작업(수출바우처 요건, 한국어 출력 확인, 검수자 단가, 수출입은행 법인 수 재확인)은 ADR-008로 범위에서 빠졌다.

## 사용자가 정할 것

- `uv run pre-commit install`로 커밋 훅을 켤지
- 단계 1.5 구현 착수 시점. `all_total_vue_student/`를 언제 삭제할지(지금은 untracked로 둠)
- MCP를 C2 서비스 경로에 실제로 끼울지(`USE_MCP_TOOLS`), 아니면 MCP 서버를 외부 노출용으로만 두고 `/v1/samples`의 리소스 조회로 연동 확인을 갈음할지
- 실험 실행 시점과 API 비용 한도. dev_004 기준 외삽으로 EXP-002는 약 5시간, 약 200만 토큰(`docs/changelog.md` M0 기록)
- `exp/grading-data-v2` 브랜치(ADR-014)를 push·PR·병합할지
- 개발 계획(`docs/roadmap.md`) M0 시작일, M4의 업로드 화면(F11) 포함 여부
- 경제성의 기본 가정을 급여 있는 2명으로 둘지 대학생 팀으로 둘지. 판정이 둘 사이에서 갈린다
- 긍정 근거 조사에서 보인 방향 전환 선택지(이름 스크리닝 업체에 독법 후보를 부품으로 공급, 라벨 일치 검증)를 검토할지. 지금 범위 밖이다
