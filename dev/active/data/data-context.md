# data Phase Context
> Gen: bronze
> Last Updated: 2026-04-30

## 핵심 파일

| 파일 | 용도 |
|------|------|
| `docs/masterplan_v0-reference.md` §A | domain-skeleton.json 인스턴스 (8 categories, 11 fields 전체 명세) |
| `docs/masterplan_v0-reference.md` §B.1 | entity-registry 예시 — entity_key 형식 확인 |
| `schemas/domain-skeleton.json` | domain-skeleton.json 유효성 검증 JSON Schema |
| `schemas/entity-registry.json` | entity key 형식 정의 |
| `src/state.py` | BronzeState, KU, EU, GU dataclass — seed 노드 입력 타입 |

## 데이터 인터페이스

**입력**: 없음 (수작업 큐레이션)

**출력**:
- `bench/japan-travel/domain-skeleton.json` → seed 노드가 `state.domain_skeleton`으로 로드
- `bench/japan-travel/seed-pack.json` → seed 노드가 entity 등록 + 초기 KU/EU 생성에 사용

## 주요 결정사항

| ID | 결정 | 이유 |
|----|------|------|
| data-1 | seed-pack.json 포맷: entities 배열, initial_knowledge 배열(field+value+EU정보) | seed 노드가 단일 파일에서 entity 등록 + KU/EU 생성을 모두 처리 |
| data-2 | domain-skeleton.json은 §A 인스턴스 그대로 사용 (수정 금지) | masterplan과 정합성 유지 |
| data-3 | seed-pack entity: 카테고리당 1–2개, initial_knowledge: 필드당 1개 | nodes Phase L1 테스트에 충분한 데이터, 과도한 사전 입력 방지 |
| data-4 | source_url 더미 허용 시 "manual-curation" 명시 | evidence_rate 검증 시 혼동 방지 |

## seed-pack.json 포맷 상세

```
{
  "domain": "japan-travel",
  "entities": [
    {
      "category": "<slug>",
      "slug": "<slug>",
      "name": "<표시명>",
      "initial_knowledge": [
        {
          "field": "<field명>",
          "value": <string | object>,
          "source_url": "<URL 또는 'manual-curation'>",
          "source_title": "<출처명>",
          "snippet": "<핵심 사실 1문장>"
        }
      ]
    }
  ]
}
```

seed 노드 처리 흐름:
1. entity → entity_registry 등록 (source="seed")
2. initial_knowledge 각 항목 → EU 생성 + KU(status=active) 생성
3. entity 등록 후 applicable_fields 조회 → 아직 KU 없는 필드에 mandatory GU 생성

## 컨벤션 체크리스트

- [ ] entity_key 형식: `japan-travel:{category}:{slug}` (소문자 + 하이픈만)
- [ ] domain-skeleton.json: §A 인스턴스와 100% 동일
- [ ] seed-pack entity: 카테고리당 ≥ 1개 (8 categories 전부 커버)
- [ ] initial_knowledge value: BronzeState KU.value 타입 (string | object)
- [ ] source_url 더미 시 `"manual-curation"` 명시
- [ ] 인코딩: UTF-8 (BOM 없음)

## Category × Field 적용 매트릭스 (§A 기준)

| field | transport | accommodation | attraction | dining | regulation | pass-ticket | connectivity | payment |
|-------|-----------|---------------|------------|--------|------------|-------------|--------------|---------|
| price | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| tips  | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| hours | — | — | ✅ | ✅ | ✅ | — | — | — |
| policy | — | — | — | — | ✅ | ✅ | — | ✅ |
| location | — | ✅ | ✅ | ✅ | — | — | — | — |
| duration | ✅ | — | — | — | — | ✅ | — | — |
| eligibility | — | — | — | — | ✅ | ✅ | — | — |
| how_to_use | ✅ | — | — | — | — | ✅ | ✅ | ✅ |
| etiquette | — | — | ✅ | ✅ | — | — | — | — |
| acceptance | — | — | — | — | — | ✅ | — | ✅ |
| where_to_buy | — | — | — | — | — | ✅ | ✅ | — |

> seed entity 큐레이션 시 해당 카테고리의 ✅ 필드 중 initial_knowledge 선택.
> GU는 나머지 ✅ 필드에 자동 생성됨 (mandatory GU).
