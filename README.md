# Tashkeel Check

아랍어 문서 검수 도구: 번역에서 독법과 표기가 갈리는 곳을 드러낸다

*A review aid for people who are responsible for Arabic documents but cannot read Arabic. It surfaces the spots where an Arabic → English translation had to choose between readings, especially names and short fields, and refuses to settle them without evidence.*

> **현재 상태 (2026-10-20): 단계 1 실험 장치를 구현했고, 실험은 아직 돌리지 않았습니다.** 측정 결과는 없습니다. 아래 질문들은 답을 가정하지 않은 실험 질문입니다. 사업 쪽 대상은 걸프(사우디·UAE)에서 아랍어 문서를 영어로 읽어야 하는 사람으로 정했고, 제품에 사람 검수는 넣지 않습니다.

## 무엇을 하는가

번역기가 아닙니다. 아랍어는 단모음을 생략해서 같은 철자에 여러 독법이 생깁니다. 문맥으로 풀리지 않는 곳, 특히 인명·회사명과 표의 셀 같은 짧은 필드에서 번역이 어느 독법을 골랐는지 드러내고, 근거가 없으면 확정하지 않고 보류합니다.

| 아랍어 | 가능한 표기 |
| --- | --- |
| مسلم | Muslim, Musallam |
| حمد | Hamad, Hamd |
| رشيد | Rashid, Rashed |

서류의 이름은 여권이나 신분증 표기와 맞아야 합니다. 이 표기는 아랍어 실력으로 정해지지 않고 외부 근거가 있어야 확정됩니다.

이 도구가 약속하는 것은 "정확한 번역"이 아니라 "모호한 구간을 얼마나 잡아내는가"입니다.

## 왜 필요한가

번역하는 LLM은 모호한 단어를 만나면 표시하지 않고 하나로 정해 넘길 수 있습니다. 이 프로젝트는 이것을 "모호성 은폐"라고 부릅니다(specification gaming의 한 형태이며 의도적 조작이 아닙니다). 읽는 사람은 아랍어를 모르니 그런 선택이 있었다는 사실조차 알 수 없습니다. 이것이 실제로 얼마나 일어나는지가 단계 1에서 잴 첫 질문입니다.

## 단계 1에서 하는 것

기능은 적게, 측정은 많이 넣은 단일 에이전트 실험 장치를 만듭니다.

| 질문 | 데이터 |
| --- | --- |
| 형태소 분석기가 실제 걸프 인명에서 독법 후보를 얼마나 내는가 | Wikidata 인명(실제 데이터, CC0) |
| 에이전트가 모호한 곳을 정말 말없이 찍는가 | 업무 규칙 기반 합성 문서 |
| "모호하면 표시하라"는 지시만으로 해결되는가 | 〃 |
| 형태소 분석기를 주면 더 잡는가 | 〃 |

구성: LangGraph 그래프(입력 → 분석기 → 에이전트 → 검증 → 대조 → 출력), LangChain 모델·툴 인터페이스, LangSmith 추적. 형태소 분석은 CAMeL Tools를 씁니다. 처분 누락 확인과 지표 계산은 LLM이 아니라 코드가 합니다.

## 실행

Python 3.11과 [uv](https://docs.astral.sh/uv/)가 필요합니다.

```bash
uv sync
```

```bash
uv run camel_data -i morphology-db-msa-r13
```

API 키 없이 연습 모드(가짜 모델)로 문서 하나를 네 조건 모두 돌려 봅니다.

```bash
uv run tashkeel run --doc data/synthetic/dev/dev_001.json --condition all --fake
```

실제 모델로 돌리려면 `.env.example`을 `.env`로 복사해 `OPENAI_API_KEY`를 넣고 `--fake`를 뺍니다. LangSmith 키가 있으면 추적이 켜지고, 없으면 추적만 꺼집니다. 결과는 `results/debug/<문서>/<조건>/`에 `segments.json`, `proper_nouns.csv`, `metrics.json`, `run_meta.json`으로 남습니다.

```bash
uv run pytest
```

## 하지 않는 것 (단계 1)

스캔본 문자 인식, 고객별 이름 사전, 사람 검토 화면, 멀티 에이전트, 한글 표기, 번역 문장 품질 평가. 서류 묶음 검색(RAG·벡터 DB)은 단계 2용 틀만 있고 꺼져 있습니다.

## 알려진 한계

- 에이전트 실험은 합성 문서로 합니다. 결과를 실제 서류의 오류율이나 포착률로 일반화하지 않습니다.
- Wikidata 인명은 공개 인물 위주라 일반 고객 서류의 이름 분포와 다를 수 있습니다.
- 단계 1에서 고유명사의 근거로 인정하는 것은 같은 문서 안의 영문 표기뿐입니다.
- 아랍어 사람 검수를 하지 않으므로 실제 고객 서류의 포착률은 재지 않습니다. 실제 문서 측정은 공식 영문본이 함께 공개된 문서로만 계획합니다.

## 라이선스 참고

CAMeL Tools의 기본 형태소 DB(calima-msa-r13)는 GPL v2입니다. 이 프로젝트는 내부 측정에만 쓰며, 배포 형태로 넘어가기 전에 법률 검토가 필요합니다.

## 문서

- [PROJECT_PLAN.md](PROJECT_PLAN.md): 계획, 측정 설계, ADR, 진행 기록
- [사업성 검토](사업성%20검토%20아랍어%20문서%20검증%20도구.md): 시장성, 기술성, 경제성 검토
