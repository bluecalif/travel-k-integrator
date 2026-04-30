# nodes Phase Plan
> Gen: bronze
> Last Updated: 2026-04-30
> Status: In Progress

## Summary

파이프라인 6개 노드 구현 + L1 단위 테스트. 각 노드는 `BronzeState → dict` 순수 함수(LangGraph 노드 시그니처). LLM/Search는 mock으로 L1 격리.

**산출물**: `src/nodes/` 6개 파일 + `tests/test_nodes/` 6개 테스트. 전체 L1 100% pass.

---

## Current State

data Phase ✅ 완료:
- `bench/japan-travel/domain-skeleton.json` — 8 categories, 11 fields
- `bench/japan-travel/seed-pack.json` — 8 categories × 1 entity, initial_knowledge 포함
- `src/state.py` BronzeState/KU/EU/GU/EntityMeta/CategorySaturation dataclass 정의됨
- `src/config.py` BronzeConfig, `src/utils/` 전체 (llm_parse, state_io, cost_guard, entity_resolver, invariant_checker, metrics, schema_validator), `src/adapters/` 전체

---

## Target State

```
src/nodes/
├── seed.py           ← seed-pack 로드 → entity 등록 + 초기 KU/EU + mandatory GU
├── entity_gen.py     ← LLM 후보 생성, de-dup, 포화 마킹
├── plan.py           ← entity_select + gap_gen + slicing
├── collect.py        ← GU → Tavily → Claim 추출, 0-claim 카운트
├── integrate.py      ← Claim → KU (Case A/B/C, D4-A)
└── critique.py       ← 수렴/강제종료 판정만

tests/test_nodes/
├── test_seed.py
├── test_entity_gen.py
├── test_plan.py
├── test_collect.py
├── test_integrate.py
└── test_critique.py
```

`python -m pytest tests/test_nodes/` 전체 pass.

---

## Implementation Stages

### Stage A — Step 5: seed.py

**책임**: seed-pack.json + domain-skeleton.json 로드 → BronzeState 초기화.

```
seed-pack entities:
  → entity_registry 등록 (source="seed")
  → initial_knowledge 각 항목: EU 생성 + KU(status=active) 생성
  → applicable_fields 조회 → KU 없는 필드마다 GU(status=open) 생성
```

핵심 헬퍼: `_resolve_applicable_fields(category, skeleton)` — `categories:["*"]` or 명시 카테고리 필터링.

**L1 테스트**: domain-skeleton.json + seed-pack.json (소규모 픽스처) → BronzeState 검증.
- entity_registry 키 수 == seed entity 수
- active KU 수 == initial_knowledge 총 항목 수
- EU 수 == active KU 수 (Evidence-first 불변원칙 3)
- GU open 수 == (applicable_fields 합계) - (initial_knowledge 항목 수)

---

### Stage B — Step 6: entity_gen.py

**책임**: 비포화 카테고리별 LLM 후보 1개 생성, de-dup(sim≥0.85), 등록 + mandatory GU 생성.

```
for cat in categories (비포화만):
    candidate = llm_generate(cat, existing)
    if candidate is None or sim(candidate, existing) >= 0.85:
        consecutive_failures += 1
        if consecutive_failures >= 2: is_saturated = True
    else:
        consecutive_failures = 0
        register(candidate, source="entity_gen")
        create_mandatory_gus(candidate)
```

참조: `src/utils/entity_resolver.py` similarity 함수.

**L1 테스트**: mock LLM 응답 제어.
- 신규 후보 → entity_registry 등록 + GU 생성 확인
- 중복 후보(sim≥0.85) → 등록 안 됨 + consecutive_failures +1 확인
- 연속 2회 실패 → is_saturated=True 확인

---

### Stage C — Step 7: plan.py

**책임**: target entity 선정 + plan_queue 구성.

```
entity_select: open GU 보유 entity 중 vacant_field_count 최다 → target_entity
gap_gen: target_entity의 applicable_fields 재확인 → GU 누락분 생성
slicing: open GU 중 target_entity 것만 → plan_queue[:max_gus_per_cycle]
```

**L1 테스트**: 미리 구성한 BronzeState → plan_queue 길이/내용 확인.
- vacant 최다 entity가 target으로 선정 확인
- max_gus_per_cycle=25 hard cap 확인
- open GU 없는 entity는 target 후보 제외 확인

---

### Stage D — Step 8: collect.py

**책임**: plan_queue 각 GU → Tavily 검색 → LLM Claim 추출 → pending_claims 누적.

```
for gu_id in plan_queue:
    query = build_query(entity_key, field)
    results = search_adapter.search(query)
    for r in results:
        eu = create_eu(r, query)
        claim = llm_extract_claim(entity_key, field, r.snippet, eu.eu_id)
        if claim: pending_claims.append(claim)
    if no_claims_for(gu_id):
        gu.attempts += 1
        if gu.attempts >= 3: gu.status = "failed"
```

참조: `src/adapters/llm_adapter.py`, `src/adapters/search_adapter.py`.

**L1 테스트**: mock search + mock LLM.
- Claim 추출 성공 → pending_claims 증가 + EU 생성 확인
- Claim 없음 → gu.attempts +1 확인
- attempts≥3 → gu.status="failed" 확인

---

### Stage E — Step 9: integrate.py

**책임**: pending_claims → KU 반영 (D4-A).

```
Case A (match is None):     KU(status=active) 신규 + GU resolved
Case B (same value):        active KU.evidence_links 추가 + confidence 갱신
Case C (different value):   KU(status=conflicting) 신규 (active KU 유지)
```

`_same_value`: (a) 정확 일치 (b) 정규화 일치 (`"50,000"` ↔ `50000`). 의미적 동치 LLM 비교는 Silver 이후.

**L1 테스트**: 불변원칙 검증에 집중.
- Case A: active KU 1개 생성, GU resolved 확인
- Case B: active KU evidence_links +1, conflicting KU 없음 확인
- Case C: conflicting KU 신규, active KU 유지, (entity_key, field) active는 여전히 1개 확인
- active KU per (entity_key, field) ≤ 1 확인 (불변원칙 2)

---

### Stage F — Step 10: critique.py

**책임**: 수렴/강제종료 판정. prescription 생성 금지(D11).

```
if all_saturated AND open_gu_count == 0:
    return {"terminate_reason": "converged"}  → END
if current_cycle >= max_cycles:
    return {"terminate_reason": "max_cycles"}  → END
return {"current_cycle": current_cycle + 1}   → CONTINUE
```

**L1 테스트**:
- 수렴 조건 충족 → terminate_reason="converged" 확인
- max_cycles 도달 → terminate_reason="max_cycles" 확인
- 계속 진행 → current_cycle +1 확인

---

## Task Breakdown

| # | Task | Size | 의존 |
|---|------|------|------|
| 3.1 | nodes/seed.py + tests/test_nodes/test_seed.py | M | state.py, bench/japan-travel/ |
| 3.2 | nodes/entity_gen.py + tests/test_nodes/test_entity_gen.py | M | seed.py, entity_resolver |
| 3.3 | nodes/plan.py + tests/test_nodes/test_plan.py | S | entity_gen.py |
| 3.4 | nodes/collect.py + tests/test_nodes/test_collect.py | M | plan.py, adapters |
| 3.5 | nodes/integrate.py + tests/test_nodes/test_integrate.py | L | collect.py |
| 3.6 | nodes/critique.py + tests/test_nodes/test_critique.py | S | integrate.py |

---

## Risks & Mitigation

| Risk | 가능성 | 대응 |
|------|--------|------|
| seed.py의 _resolve_applicable_fields 오류 → GU 과생성/미생성 | 중간 | L1에서 픽스처 기반 GU 수 정밀 검증 |
| integrate.py Case B _same_value 정규화 누락 → conflicting KU 과다 | 중간 | 테스트에 "50,000" ↔ 50000 케이스 명시 |
| entity_gen.py sim threshold 오계산 → de-dup 미작동 | 낮음 | entity_resolver.similarity 단위 테스트가 이미 커버 |
| collect.py mock과 실제 adapter 인터페이스 불일치 | 낮음 | adapter 시그니처를 scaffold에서 확정했으므로 mock 쉬움 |

---

## Dependencies

**내부 (이미 구현됨):**
- `src/state.py` — BronzeState, KU, EU, GU, EntityMeta, CategorySaturation
- `src/config.py` — BronzeConfig (max_gus_per_cycle 등)
- `src/utils/entity_resolver.py` — similarity()
- `src/utils/invariant_checker.py` — check_* 함수
- `src/utils/llm_parse.py` — extract_json()
- `src/adapters/llm_adapter.py`, `src/adapters/search_adapter.py`

**외부:**
- `pytest` — L1 테스트 실행
- `unittest.mock` — LLM/Search adapter mock
