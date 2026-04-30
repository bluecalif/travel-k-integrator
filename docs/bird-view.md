# Bird View — travel-k-integrator
> Updated: 2026-04-30
> Status: nodes Phase 진행 중 (2/6 구현 완료)

---

## Pipeline Flow

```
START → seed → [ entity_gen → plan → collect → integrate → critique ] → END
                ↑___________________________________________________|
                         (loop until convergence or max_cycles)
```

- **구현 완료**: `seed` ✅, `entity_gen` ✅
- **미구현 (stub/예정)**: `plan`, `collect`, `integrate`, `critique`, `graph.py`

---

## State (`src/state.py`)

```
BronzeState:
  domain_skeleton       dict        — categories + fields (Category↔Field 매트릭스)
  entity_registry       dict[str, EntityMeta]   — entity_key → meta (source/cycle/category)
  knowledge_units       list[KU]    — (entity_key, field)별 정규화 주장
  evidence_units        list[EU]    — Claim 단위 출처 (URL + snippet)
  gap_map               list[GU]    — open/resolved/failed
  category_saturation   dict[str, CategorySaturation]  — consecutive_failures, is_saturated
  target_entity         str | None  — 현 cycle 처리 대상
  current_cycle         int
  plan_queue            list[str]   — GU ID 목록 (이번 cycle 처리 대상)
  pending_claims        list[dict]
  metrics               dict
  terminate_reason      str | None  — "converged" | "max_cycles"
```

**ID 규칙**: `KU-{n:04d}`, `EU-{n:04d}`, `GU-{n:04d}` (len+1 순번)
**entity_key 형식**: `{domain}:{category}:{slug}` (예: `japan-travel:transport:jr-pass`)

---

## Modules

### seed (`src/nodes/seed.py`)
**역할**: seed-pack.json → entity 등록 + 초기 KU/EU + 모든 vacant field → mandatory GU. 1회성 초기화 (entity_registry가 이미 있으면 no-op).
**핵심 함수**: `seed(state, config: dict) -> dict`
**State 변경**: reads `domain_skeleton`; writes `entity_registry`, `knowledge_units`, `evidence_units`, `gap_map`, `category_saturation`

```python
def seed(state: BronzeState, config: dict) -> dict:
    if state.entity_registry:          # 재진입 방지
        return {}
    bench_root = Path(config["configurable"]["bench_root"])
    seed_pack = json.load(bench_root / "seed-pack.json")

    for entity in seed_pack["entities"]:
        entity_key = f"{domain}:{category}:{slug}"
        entity_registry[entity_key] = EntityMeta(source="seed")

        for ik in entity["initial_knowledge"]:
            eu = EU(eu_id=f"EU-{n:04d}", ...)
            ku = KU(status="active", evidence_links=[eu_id], confidence=0.8)

        for field in _resolve_applicable_fields(category, skeleton):
            if field not in covered:   # GU: vacant fields만
                gap_map.append(GU(status="open"))
```

**주의**: `_resolve_applicable_fields` — `categories: ["*"]` 와일드카드 처리 필수.
bench_root는 `config["configurable"]["bench_root"]`에서 읽음 (LangGraph configurable 패턴).

---

### entity_gen (`src/nodes/entity_gen.py`)
**역할**: 비포화 카테고리별 LLM으로 entity 후보 1개 생성·등록. 카테고리 내 + 전역 de-dup.
**핵심 함수**: `entity_gen(state: BronzeState) -> dict`
**State 변경**: reads `entity_registry`, `category_saturation`, `domain_skeleton`; writes `entity_registry`, `gap_map`, `category_saturation`

```python
def entity_gen(state: BronzeState) -> dict:
    for cat in categories:
        sat = category_saturation[cat]
        if sat.is_saturated: continue

        existing_slugs = [extract_slug(ek) for ek in existing_in_cat]
        candidate = _llm_generate_candidate(domain, cat, existing_slugs, all_names, llm)

        if candidate is None:                               # null 응답
            sat.consecutive_failures += 1
        elif max_similarity(candidate["slug"], existing_slugs) >= 0.85:  # 카테고리 내 de-dup
            sat.consecutive_failures += 1
        elif max_similarity(candidate["slug"], all_slugs) >= 0.85:       # 전역 de-dup
            sat.consecutive_failures += 1
        elif len(existing_in_cat) >= config.max_entities_per_category:   # cap
            sat.is_saturated = True; continue
        else:
            sat.consecutive_failures = 0
            entity_registry[entity_key] = EntityMeta(source="entity_gen", cycle=N)
            gap_map += [GU(field=f) for f in _resolve_applicable_fields(cat, skeleton)]

        if sat.consecutive_failures >= 2:
            sat.is_saturated = True
```

**LLM 프롬프트**: 전체 레지스트리 entity 목록 + 추상 개념 금지 조건 포함.
**주의**: `_llm_generate_candidate`의 except는 ValueError만 (API 오류는 propagate — saturation 오염 방지).
**LLM 호출**: `create_llm(config).invoke(prompt)` → `response.content`

---

### plan, collect, integrate, critique
> **미구현** (Steps 7–10 예정). 설계는 `docs/masterplan_v0-reference.md §C` 참조.

---

## Adapters & Utils

| 모듈 | 핵심 인터페이스 |
|------|----------------|
| `adapters/llm_adapter.py` | `create_llm(config) → LLMCallCounter` (`.invoke(prompt) → response.content`). `MockLLM([responses])` 테스트용 |
| `adapters/search_adapter.py` | Tavily 래핑 (stub 구현) |
| `utils/llm_parse.py` | `extract_json(text) → dict \| list` — markdown fence 제거 후 JSON 파싱 |
| `utils/entity_resolver.py` | `max_similarity(candidate, slugs)` — difflib 기반. `extract_slug(entity_key)` |
| `utils/state_io.py` | `load_state()` / `save_state()` / `snapshot_state()` |
| `utils/cost_guard.py` | LLM+Tavily 비용 누적. `budget_cap_usd` 초과 시 중단 |
| `utils/invariant_checker.py` | 4대 불변원칙 검증 (active KU uniqueness, evidence-first 등) |
| `utils/metrics.py` | `gap_resolution_rate`, `avg_confidence`, `evidence_rate` |

---

## Key Config (`src/config.py` — BronzeConfig)

| 파라미터 | 기본값 | 의미 |
|---------|--------|------|
| `max_gus_per_cycle` | 25 | plan 노드 hard cap |
| `max_entities_per_category` | 20 | entity_gen 상한 |
| `similarity_threshold` | 0.85 | de-dup 임계치 |
| `saturation_consecutive_threshold` | 2 | 연속 실패 → 포화 |
| `gu_max_attempts` | 3 | 0-claim 누적 → failed |
| `budget_cap_usd` | 1.2 | 전체 API 예산 |

---

## Debugging Hints

- **entity_gen 전 카테고리 failures=1**: API 키 미설정 가능성. `_llm_generate_candidate`는 ValueError만 catch — 인증 오류(401)는 propagate됨.
- **entity_gen 추상 entity 생성** (예: `dining:sushi`): 프롬프트의 전체 레지스트리/추상 금지 조건이 제거됐는지 확인.
- **크로스-카테고리 중복** (예: `transport:jr-pass` + `pass-ticket:jr-pass`): 전역 de-dup 로직(`all_slugs`) 확인.
- **active KU 2개 존재**: `invariant_checker.check_active_ku_uniqueness()` 실행. integrate Case B/C 분기 확인.
- **GU가 resolved 안 됨**: `collect`의 0-claim 여부 → `gu.attempts` 체크. 3회면 `failed`.
