# Project Overall Tasks
> Gen: bronze
> Last Updated: 2026-04-30
> scaffold: ✅ Complete | data: ✅ Complete | nodes: 🔵 In Progress (2/6)

## Summary

- **총 Steps**: 14
- **총 Tasks**: 23 (S: 10, M: 10, L: 2, XL: 1)
- **Phases**: scaffold / data / nodes / runner / validation

---

## Phase 1: scaffold (Steps 1–3) ✅

| # | Task | Size | Status | Commit |
|---|------|------|--------|--------|
| 1.1 | Step 1: 프로젝트 골격 (src/, tests/, schemas/, .env.example, pyproject.toml, .gitignore) | M | ✅ | 3e9a686 |
| 1.2 | Step 2: src/state.py — BronzeState, KU, EU, GU, EntityMeta, CategorySaturation dataclass | M | ✅ | 8075941 |
| 1.3 | Step 2: src/config.py — BronzeConfig.from_env(), redact(), write_config_snapshot() | S | ✅ | 8075941 |
| 1.4 | Step 2: schemas/ — knowledge-unit.json, evidence-unit.json, gap-unit.json, domain-skeleton.json, entity-registry.json | S | ✅ | 8075941 |
| 1.5 | Step 3: adapters/llm_adapter.py (OpenAI gpt-4.1-mini 래핑) | S | ✅ | bbbe14a |
| 1.6 | Step 3: adapters/search_adapter.py (Tavily 래핑) | S | ✅ | bbbe14a |
| 1.7 | Step 3: utils/llm_parse.py (extract_json, LLM 응답 → JSON) | S | ✅ | bbbe14a |
| 1.8 | Step 3: utils/state_io.py (load_state, save_state, snapshot_state) | S | ✅ | bbbe14a |
| 1.9 | Step 3: utils/cost_guard.py (LLM+Tavily 비용 누적 + budget_cap 초과 중단) | S | ✅ | bbbe14a |
| 1.10 | Step 3: utils/entity_resolver.py (canonicalize_entity_key, similarity) | S | ✅ | bbbe14a |
| 1.11 | Step 3: utils/invariant_checker.py (4대 불변원칙 검증) | S | ✅ | bbbe14a |
| 1.12 | Step 3: utils/metrics.py (gap_resolution_rate, avg_confidence, evidence_rate) | S | ✅ | bbbe14a |
| 1.13 | Step 3: utils/schema_validator.py (KU/EU/GU JSON Schema 검증) | S | ✅ | bbbe14a |

---

## Phase 2: data (Step 4)

| # | Task | Size | Status | Commit |
|---|------|------|--------|--------|
| 2.1 | Step 4: bench/japan-travel/domain-skeleton.json (8 categories × 11 fields 매트릭스) | M | ✅ | ce09b73 |
| 2.2 | Step 4: bench/japan-travel/seed-pack.json (8 categories × 1–2 entity, 초기 KU 값) | M | ✅ | ce09b73 |

---

## Phase 3: nodes (Steps 5–10)

| # | Task | Size | Status | Commit |
|---|------|------|--------|--------|
| 3.1 | Step 5: nodes/seed.py + tests/test_nodes/test_seed.py (L1) | M | ✅ | 2d8249e |
| 3.2 | Step 6: nodes/entity_gen.py + tests/test_nodes/test_entity_gen.py (L1) | M | ✅ | c6ef50e |
| 3.3 | Step 7: nodes/plan.py + tests/test_nodes/test_plan.py (L1) | S | ⬜ | — |
| 3.4 | Step 8: nodes/collect.py + tests/test_nodes/test_collect.py (L1) | M | ⬜ | — |
| 3.5 | Step 9: nodes/integrate.py (D4-A) + tests/test_nodes/test_integrate.py (L1) | L | ⬜ | — |
| 3.6 | Step 10: nodes/critique.py + tests/test_nodes/test_critique.py (L1) | S | ⬜ | — |

---

## Phase 4: runner (Step 11)

| # | Task | Size | Status | Commit |
|---|------|------|--------|--------|
| 4.1 | Step 11: src/graph.py (LangGraph StateGraph 6-node + routing) | M | ⬜ | — |
| 4.2 | Step 11: scripts/run_bronze.py (CLI: --phase, --trial-id, --cycles, --bench-root) | M | ⬜ | — |

---

## Phase 5: validation (Steps 12–14)

| # | Task | Size | Status | Commit |
|---|------|------|--------|--------|
| 5.1 | Step 12: L2 dev-smoke (5 cycles) — E2E 합격 확인 | L | ⬜ | — |
| 5.2 | Step 13: L3 dev-baseline (10 cycles) — metrics 임계치 합격 | L | ⬜ | — |
| 5.3 | Step 14: L4 bronze-v1 (20 cycles) — budget + 수렴 합격 | XL | ⬜ | — |
