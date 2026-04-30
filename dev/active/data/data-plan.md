# data Phase Plan
> Gen: bronze
> Last Updated: 2026-04-30
> Status: Complete

## Summary

bench/japan-travel/ 수작업 큐레이션. nodes Phase(Step 5~10) L1 테스트와 validation Phase(Step 12~14) E2E 실행에 필요한 두 입력 파일 생성.

- `bench/japan-travel/domain-skeleton.json` — 8 categories × 11 fields 매트릭스
- `bench/japan-travel/seed-pack.json` — 8 categories × 1–2 entity + 초기 KU/EU 값

---

## Current State

scaffold Phase ✅ 완료:
- `src/`, `tests/`, `schemas/` 구조 완비
- `src/state.py` BronzeState / KU / EU / GU dataclass 정의됨
- `schemas/domain-skeleton.json`, `schemas/entity-registry.json` (JSON Schema) 완비
- Python import 전체 통과, `python -m pytest` 에러 없음

---

## Target State

```
bench/japan-travel/
├── domain-skeleton.json  ← §A 인스턴스 완성 (8 categories, 11 fields)
└── seed-pack.json        ← 8 categories × 1–2 entity, 각 초기 KU+EU 1–2개
```

`src/nodes/seed.py` 가 두 파일을 읽어 BronzeState 초기화 가능한 상태.

---

## Implementation Stages

### Stage A — Step 4a: domain-skeleton.json

masterplan_v0-reference.md §A 인스턴스를 `bench/japan-travel/domain-skeleton.json`으로 직접 작성.

8 categories: transport, accommodation, attraction, dining, regulation, pass-ticket, connectivity, payment  
11 fields: price, hours, policy, location, duration, eligibility, how_to_use, etiquette, tips, acceptance, where_to_buy  
`categories: ["*"]` 필드: price, tips (모든 카테고리 적용)

**산출물**: `bench/japan-travel/domain-skeleton.json`

---

### Stage B — Step 4b: seed-pack.json

8 categories 각 1–2개 entity, 각 entity 초기 KU 1–2개(EU 포함).  
seed 노드가 읽어 entity_registry 등록 + 초기 KU/EU 생성 + mandatory GU 생성에 사용.

**seed-pack.json 포맷 (결정사항 data-1)**:
```json
{
  "domain": "japan-travel",
  "entities": [
    {
      "category": "transport",
      "slug": "jr-pass",
      "name": "JR Pass",
      "initial_knowledge": [
        {
          "field": "price",
          "value": {"7day_ordinary_jpy": 50000, "14day_ordinary_jpy": 80000},
          "source_url": "https://www.japanrailpass.net/en/",
          "source_title": "Japan Rail Pass Official",
          "snippet": "7-day Ordinary Pass costs 50,000 yen for adults."
        }
      ]
    }
  ]
}
```

**큐레이션 기준**:
- entity slug: 영문 소문자 + 하이픈
- 일반 여행자가 검색할 만한 실명 entity 우선
- initial_knowledge: 검색 가능한 공개 사실 1–2개만 (과도한 사전 입력 금지)
- source_url: 실제 접근 가능한 공개 URL 권장 (더미 허용 단, 명시)

**산출물**: `bench/japan-travel/seed-pack.json`

---

## Task Breakdown

| # | Task | Size | 의존 |
|---|------|------|------|
| 2.1 | bench/japan-travel/domain-skeleton.json (§A 인스턴스) | M | schemas/ 완비 |
| 2.2 | bench/japan-travel/seed-pack.json (8 cat × 1–2 entity) | M | 2.1 |

---

## Risks & Mitigation

| Risk | 가능성 | 대응 |
|------|--------|------|
| seed-pack entity 수가 너무 적어 L3 "모든 카테고리 entity ≥ 1" 미달 | 낮음 (8개 카테고리 커버) | 카테고리당 최소 1개 강제 |
| initial_knowledge 가 실제 실행 시 LLM Claim과 충돌 → conflicting KU 과다 | 중간 | 초기값을 공식 사실(가격 공시 등)로만 제한 |
| source_url 더미 사용 시 EU snippet 검증 실패 | 낮음 | 더미 사용 시 `"source_url": "manual-curation"` 표기 |

---

## Dependencies

**내부:**
- `schemas/domain-skeleton.json` — domain-skeleton.json 유효성 검증용 JSON Schema
- `schemas/entity-registry.json` — entity key 형식 기준
- `src/state.py` — seed 노드 입력 타입 정의

**외부:** 없음 (수작업 큐레이션)
