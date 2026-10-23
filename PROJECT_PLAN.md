# Tashkeel Check — 현재 상태

- 프로젝트/레포 이름: `tashkeel-check`
- 마지막 업데이트: 2026-10-23 (TTS 전환, 문서 전체를 TTS 기준으로 다시 씀)
- 상태: **방향 전환, 계획 단계.** 제품을 "실시간 아랍어 TTS의 이름 발음 앞단 층"으로 바꿨다([ADR-023](docs/adr/ADR-023.md)). 코드는 이전 제품(서류 검수 서비스, 2026-10-22 제출본) 그대로이고 TTS 코드·측정값은 없다. 첫 실험 EXP-006(엔진 베이스라인)은 사전 등록 초안만 있다.
- 문서 역할: 현재 상태, 남은 일, 정할 것만 둔다. 제품 설명은 [README.md](README.md), 본문은 `docs/`([문서 지도](docs/README.md)), 이전 제품 문서는 [docs/archive/document-review/](docs/archive/document-review/)에 있다.

> **작업을 시작하기 전에 이 문서와 [docs/README.md](docs/README.md)를 읽는다. 계획·범위·구조·데이터·평가 방식이 바뀌면 해당 `docs/` 문서를 고치고 [docs/changelog.md](docs/changelog.md)에 이유와 영향을 적는다. 기술 결정은 [docs/adr/](docs/adr/README.md), 재현 가능한 오류는 [docs/troubleshooting.md](docs/troubleshooting.md), 측정은 [docs/experiments/](docs/experiments/README.md)에 남긴다. 작업을 마칠 때 이 문서와 [docs/roadmap.md](docs/roadmap.md)의 기능 상태를 실제 결과에 맞게 고친다.**
>
> 완료 여부는 실제 구현·실행·확인 결과를 기준으로 쓴다. 실행하지 않은 실험이나 검증을 완료했다고 기록하지 않는다.

## 한눈에

| 항목 | 내용 | 근거 |
| --- | --- | --- |
| 제품 | 음성 에이전트가 말할 텍스트의 고유명사(사람·회사·지명)마다 올바른 독법을 근거와 함께 정해 TTS 엔진에 넘기는 앞단 층. 근거 없으면 기본 독법 + 낮은 확신 + 사후 확정 큐. 확정한 발음은 고객 발음 사전에 | [problem-and-goals.md](docs/problem-and-goals.md), ADR-023 |
| 고객 | 사우디·UAE에서 아랍어 음성 봇·IVR을 운영하는 은행·통신사·정부 서비스, CPaaS | ADR-023 |
| 사용자 결정(2026-10-23) | 1차 용도 실시간 음성 / 기존 제품 완전 전환 / 앞단 층만(자체 모델 없음) | [scope.md](docs/scope.md) |
| 구조 | 오프라인(후보 생성 → 근거 검사 → 사람 확정 → 사전)과 실시간(`/v1/pronounce`: 사전 조회 + 결정적 디아크리타이저 + 엔진 형식 치환, LLM 없음, p95 ≤ 50ms [제안]) | [architecture.md](docs/architecture.md) |
| 확정 규칙 | 사전 등록은 사람 확정·녹음 정렬·라틴 표기 일치 중 하나의 근거가 있을 때만. 디아크리타이저·LLM 출력은 확정이 아님. 자음 골격이 바뀐 출력은 폐기 | ADR-023, [evaluation.md 6.6절](docs/evaluation.md) |
| 코드 | 서류 검수 제출본 그대로. 테스트 559개·골든 160건. 재사용·변경·신규 대조는 architecture 4.3절 | [architecture.md](docs/architecture.md) |
| 측정한 것 | **없음.** 서류 검수 때의 값(C1 엄격 0.9993)은 보관 문서에만 | [experiments](docs/experiments/README.md) |
| 조사 | 아랍어 TTS·이름 발음·실시간 파이프라인 문헌(2026-10-23), 전환 전 서류 검수 품질 진단 | [research/](docs/research/tts-literature.md) |

## 아직 하지 않은 것

- EXP-006(엔진 베이스라인) 판정 기준·예산 확정과 실행. 이름 세트(CamelProp 걸프 하위 집합) 라이선스 확인. 자체 라벨러 2인 확보 여부.
- 디아크리타이저 3종의 이름 단위 정확도·문장당 지연 점검(EXP-007 [제안], 비용 0).
- TTS 앞단 층 코드 전부(새 모듈·API·DB는 [architecture.md 4.4~4.6절](docs/architecture.md)에 [제안]으로만).
- 사업성 검토 재계산(보관된 검토는 서류 검수·KYC 기준).
- 서류 검수에서 남긴 것 중 이번에도 해당하는 것: LangSmith 키 교체(401), pre-commit 훅.

## 다음 작업

[README 향후 계획](README.md#향후-계획), [roadmap.md 2절](docs/roadmap.md)과 같은 순서다. 모두 [제안]이고 시작은 사용자가 정한다.

1. **EXP-006 사전 등록 확정과 실행.** 판정 기준(제안: 어느 엔진이든 무디아크리틱스 오류율 5% 이상이면 앞단 층이 할 일이 있음, 모두 5% 미만이면 ADR-023 재검토), 엔진 목록(Azure ar-SA·ar-AE, Polly ar-AE, Google ar-XA Chirp 3 HD, ElevenLabs, 선택 오픈 모델 1개), 이름 세트, 청취자 2인, 예산을 정한다.
2. **디아크리타이저 점검(EXP-007).** CATT-EO ONNX, libtashkeel, CAMeL GLF를 CamelProp dev 50개에서 이름 단위 DER·ms로 비교.
3. **사전 스키마(Alembic 0005)와 후보 생성.** `english_name` NULL 허용, `pronunciation`·`phonemes`·`source`·`engine_overrides`·`previous_value`. `exp001` 라틴 필터 확장.
4. **엔진 어댑터 2개와 G2P 첫 판.** EXP-006에서 "존중"으로 판정된 엔진부터.
5. **확정 큐와 피드백 기록.** 확정 출처·이전 값·확정자를 처음부터.
6. **실시간 API `/v1/pronounce`와 합성 발화 생성기로 지연 측정.**
7. **사업성 검토 재계산.**
8. **서류 검수 코드 유지 여부.**

## 사용자가 정할 것

- EXP-006의 판정 기준(제안 5%)·예산·엔진 목록·1차 로케일(사우디/UAE)과 실행 여부
- 자체 라벨러(아랍어 원어민 2인)를 구할지. 못 구하면 CamelProp만으로 돌리고 걸프 방언 독법은 재지 않는다
- 지연 목표 수치(제안 p95 50ms)
- 녹음 수집 여부와 동의 절차. 어려우면 근거를 라틴 표기·사람 확정으로 줄인다
- 걸프 방언 독법과 MSA 독법의 기본값
- 디아크리타이저 선택과 라이선스(CATT Apache-2.0 / libtashkeel MIT / CAMeL GLF)
- 1차 고객 유형과 가격 단위, 사업성 검토를 다시 할지
- 서류 검수 코드(테스트 559개·골든 160건)를 언제까지 유지할지, 재사용 모듈을 분리할지
- 서류 검수 때 쓴 "99.9%" 표기를 보관 문서에서 "≥ 99.6%(합성, 반복 1회)"로 고칠지(보관본은 내용을 고치지 않는 원칙이라 주석으로만 달 수 있다)
- LangSmith 키 교체, `uv run pre-commit install`
