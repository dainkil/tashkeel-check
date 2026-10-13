# 합성 문서 (SYNTHETIC)

이 폴더의 문서는 합성 데이터다. 실존 인물·회사·서류가 아니다.

- 생성: `uv run tashkeel make-synthetic` (`src/tashkeel_check/data/synthetic.py`, 생성기 `synthetic-v0`)
- 분할: `dev/` 10개(seed 1001, 프롬프트 디버깅용), `eval/` 30개(seed 2002, EXP-002 조건 비교에 한 번만 사용)
- 문서 유형: 위임장(`poa`), 법인 확인서(`company_letter`). 약 절반은 아랍어·영어 이중 언어
- 이름: Wikidata 걸프 인명(CC0)에서 뽑은 이름 단위를 무작위로 조합했다. 조합한 전체 이름이 Wikidata 레이블과 같으면 버렸다
- 신분증·여권·등록 번호: 형식 출처가 없어 자리표시 숫자를 썼다
- 템플릿의 아랍어 문장은 사람이 검수하지 않았다

반영한 업무 규칙과 출처는 `PROJECT_PLAN.md` 5.2절(R1~R5)에 있다.

각 파일의 `gold`는 정답 라벨이다. 그래프는 이 값을 대조 단계에서만 쓰고 프롬프트에는 넣지 않는다.

- `gold.names[]`: 이름이 나온 자리마다 역할, 구간, 토큰 ID, 토큰별 실제 영문 표기 목록(`english_variants`)과 문서에 쓴 표기(`english_used`), 문서 안 근거(이중 언어일 때 영문 줄의 인용)
- `gold.neutral_token_ids`: 지명, 국가명, 발급 기관, 법인 형태 약어. 과잉 표시를 셀 때 빼는 토큰

이 문서로 낸 결과는 "합성 문서 기준"이다. 실제 서류의 오류율이나 포착률로 쓰지 않는다.
