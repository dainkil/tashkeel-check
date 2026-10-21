# 어려운 합성 문서 (SYNTHETIC, synthetic-hard)

이 폴더의 문서는 합성 데이터다. 실존 인물·회사·서류가 아니다. 이메일·URL은 예약 도메인(`example.com`, `example.net`)만 쓴다.

- **생성:** `uv run tashkeel make-synthetic-hard --split dev|eval`. 생성기는 `src/tashkeel_check/data/synthetic_hard.py`, 버전 `synthetic-hard-v2`, gold 형식 2다(2026-10-21, ADR-017). v2는 dev 실제 모델 점검 뒤 고친 판이다(`docs/data.md` 5.3절 "v2에서 바뀐 것").
- **분할:**
  - `dev/` 20개(seed 3001): 프롬프트·형식 점검용이다.
  - `eval/` 70개(seed 4002부터 최소 수량을 처음 채우는 seed, 최대 20번): EXP-003 조건 비교에 한 번만 쓴다. 2026-10-21에 만들었다(seed 4002 첫 시도, 이름 부분 1,457개). 다시 만들지 않는다. 튜닝에 쓰지 않는다.
  - 유형별 수량 보고는 `quota_<split>.json`에 있다.
- **문서 유형(`doc_type`):** `poa`(여권 칸이 있는 위임장), `letter`(고용 확인서, 레터헤드 URL·인사부 문의 이메일), `cr`(상업등기 발췌, 파트너 7~9명, 관리자·서명권자 줄에 파트너 번호), `minutes`(총회 의사록).
- **유형:** `case_types`(문서), `gold.names[].tokens[].case_types`(이름 부분)에 있다. A1~D5 정의와 정답 규칙은 `docs/data.md` 5.3절이다.
- **이름:** Wikidata 걸프 인명(CC0)의 이름 단위를 조합했다. 전체 이름이 Wikidata 레이블과 같으면 버렸다.
- **검수:** 템플릿의 아랍어 문장은 사람이 검수하지 않았다(`meta.arabic_reviewed_by_human: false`).

## gold 형식 2

그래프는 `gold`를 대조 단계에서만 쓰고 프롬프트에 넣지 않는다.

- **`gold.names[]`(등장):** `person_id`, `mention`(`full`·`short`·`title_short`), 구간, 토큰 ID, `tokens[]`가 있다. `tokens[]`는 이름 부분마다 한 줄이며 필드는 아래와 같다.
  - `token_ids`: 토큰 둘인 부분도 하나로 센다. `token_id`는 마지막 토큰이다.
  - `slot`: `given`·`father`·`grandfather`·`ggf`·`family`
  - `expected`: `adopt`·`hold`
  - `expected_spelling`: 확정일 때 기대 표기(엄격 철자로 비교)
  - `evidence[]`: 그 부분의 철자가 든 그 사람의 표기 전부
  - `must_include`: 충돌일 때 후보에 들어야 하는 두 철자
  - `english_variants`: 걸러 낸 후보 표기
  - `raw_variants`: Wikidata 별칭 원본
  - `english_used`: 그 사람의 신분증 표기
  - `case_types`, `arguable`
- **`gold.persons[]`:** 사람·회사마다 이름 부분과 신분증 표기, `renderings[]`(그 사람의 로마자 표기: 구간, 인용, 형태, 라벨 유무, 완전한 철자가 나온 부분, 이니셜로만 나온 부분)가 있다.
- **`gold.decoys[]`:** 회사명·이메일·URL처럼 근거가 아닌 라틴 문자와, 닮은 이름 부분이 있다.
- **`gold.neutral_token_ids`·`title_token_ids`:** 채점하지 않는 토큰(법인 형태·발급 기관·도시·국가, 칭호)이다.
- **`gold.lookalikes[]`·`lookalike_token_ids`:** 이름과 같은 일반 단어, nisba와 같은 국적 형용사다. 정확도에는 넣지 않고, 이름으로 표시했는지만 본다.
- **확인 방법:** `uv run tashkeel inspect-gold --case B3 --n 2`로 구간별 정답을 읽기 좋게 볼 수 있다.

이 문서로 낸 결과는 "합성 문서(synthetic-hard) 기준"이다. 실제 서류의 오류율이나 포착률로 쓰지 않는다.
