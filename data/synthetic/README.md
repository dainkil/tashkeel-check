# 합성 문서 (SYNTHETIC)

이 폴더의 문서는 합성 데이터다. 실존 인물·회사·서류가 아니다.

- 생성: `uv run tashkeel make-synthetic` (`src/tashkeel_check/data/synthetic.py`, 생성기 `synthetic-v2`, 2026-10-20. v2는 v1과 템플릿이 같고 이름 풀을 정렬 규칙 v1로 다시 만든 것이다. 이전 버전은 git 기록에만 있다)
- 분할: `dev/` 10개(seed 1001, 프롬프트 디버깅용), `eval/` 30개(seed 2002, EXP-002 조건 비교에 한 번만 사용)
- 문서 유형: 위임장(`poa`), 법인 확인서(`company_letter`)
- 근거 배치(`evidence_layout`): 이름의 영문 근거 줄이 붙는 역할이 없음(`none`, 아랍어만) / 일부(`mixed`) / 전부(`all`). 문서 유형마다 세 배치를 같은 수에 가깝게 나눴다. 근거가 붙은 역할은 `evidence_roles`, 영문 줄이 하나라도 있는지는 `bilingual`. eval은 10/10/10, dev는 4/4/2(없음/일부/전부)
- 이름: Wikidata 걸프 인명(CC0)에서 뽑은 이름 단위를 무작위로 조합했다. 조합한 전체 이름이 Wikidata 레이블과 같으면 버렸다. 이름 풀(`data/wikidata/name_tokens.json`)의 정렬 버전은 문서 `meta.name_pool_align_version`에 있다
- 신분증·여권·등록 번호: 형식 출처가 없어 자리표시 숫자를 썼다
- 템플릿의 아랍어 문장은 사람이 검수하지 않았다

반영한 업무 규칙과 출처는 `docs/data.md` 5.2절(R1~R5)에 있다.

각 파일의 `gold`는 정답 라벨이다. 그래프는 이 값을 대조 단계에서만 쓰고 프롬프트에는 넣지 않는다.

- `gold.names[]`: 이름이 나온 자리마다 역할, 구간, 토큰 ID, 토큰별 실제 영문 표기 목록(`english_variants`)과 문서에 쓴 표기(`english_used`, 근거가 없는 문서에서는 신분증 표기 역할), 문서 안 근거(그 역할에 영문 줄이 있을 때 인용)
- `gold.neutral_token_ids`: 지명, 국가명, 발급 기관, 법인 형태 약어. 처분을 기대하지도 감점하지도 않는 토큰(미처리·근거 없는 확정·과잉 표시에서 뺀다, ADR-014)

이 문서로 낸 결과는 "합성 문서 기준"이다. 실제 서류의 오류율이나 포착률로 쓰지 않는다.
