# nodes Phase Tasks
> Gen: bronze
> Last Updated: 2026-04-30
> Status: In Progress (2/6, 33%)

## Summary

- **총 Tasks**: 6 (M: 3, S: 2, L: 1)
- **완료**: 2/6 (33%)
- **Steps**: 5–10
- **합격 기준**: `python -m pytest tests/test_nodes/` 전체 pass

---

## Stage A — Step 5: seed.py

| # | Task | Size | Status | Commit |
|---|------|------|--------|--------|
| 3.1 | `src/nodes/seed.py` + `tests/test_nodes/test_seed.py` (L1) | M | ✅ | 2d8249e |

**완료 조건**:
- [x] entity_registry 등록 수 == seed entities 수
- [x] active KU 수 == initial_knowledge 총 항목 수
- [x] EU 수 == active KU 수 (불변원칙 3)
- [x] GU open 수 == applicable_fields 합계 − initial_knowledge 수
- [x] L1 pytest pass (15/15)

---

## Stage B — Step 6: entity_gen.py

| # | Task | Size | Status | Commit |
|---|------|------|--------|--------|
| 3.2 | `src/nodes/entity_gen.py` + `tests/test_nodes/test_entity_gen.py` (L1) | M | ✅ | — |

**완료 조건**:
- [x] 신규 후보 → entity_registry 등록 + mandatory GU 생성
- [x] sim≥0.85 중복 → 등록 안 됨 + consecutive_failures +1 (카테고리 내 + 전역)
- [x] consecutive_failures≥2 → is_saturated=True
- [x] L1 pytest pass (11/11)

---

## Stage C — Step 7: plan.py

| # | Task | Size | Status | Commit |
|---|------|------|--------|--------|
| 3.3 | `src/nodes/plan.py` + `tests/test_nodes/test_plan.py` (L1) | S | ⬜ | — |

**완료 조건**:
- [ ] vacant 최다 entity → target_entity 선정
- [ ] plan_queue 길이 ≤ max_gus_per_cycle (25)
- [ ] open GU 없는 entity 제외 확인
- [ ] L1 pytest pass

---

## Stage D — Step 8: collect.py

| # | Task | Size | Status | Commit |
|---|------|------|--------|--------|
| 3.4 | `src/nodes/collect.py` + `tests/test_nodes/test_collect.py` (L1) | M | ⬜ | — |

**완료 조건**:
- [ ] Claim 추출 → pending_claims 증가 + EU 생성
- [ ] 0-claim → gu.attempts +1
- [ ] attempts≥3 → gu.status="failed"
- [ ] L1 pytest pass (mock search + mock LLM)

---

## Stage E — Step 9: integrate.py

| # | Task | Size | Status | Commit |
|---|------|------|--------|--------|
| 3.5 | `src/nodes/integrate.py` + `tests/test_nodes/test_integrate.py` (L1) | L | ⬜ | — |

**완료 조건**:
- [ ] Case A: active KU 신규 + GU resolved
- [ ] Case B: evidence_links +1 (conflicting KU 없음)
- [ ] Case C: conflicting KU 신규, active KU 유지
- [ ] (entity_key, field) active KU = 정확히 1개 (불변원칙 2)
- [ ] active KU evidence_links ≥ 1 (불변원칙 3)
- [ ] L1 pytest pass

---

## Stage F — Step 10: critique.py

| # | Task | Size | Status | Commit |
|---|------|------|--------|--------|
| 3.6 | `src/nodes/critique.py` + `tests/test_nodes/test_critique.py` (L1) | S | ⬜ | — |

**완료 조건**:
- [ ] all_saturated AND open=0 → terminate_reason="converged"
- [ ] current_cycle≥max_cycles → terminate_reason="max_cycles"
- [ ] 계속 → current_cycle +1
- [ ] prescription 생성 로직 없음 확인 (D11)
- [ ] L1 pytest pass

---

## 전체 완료 체크

- [ ] 6/6 Tasks ✅ (현재 2/6)
- [ ] `python -m pytest tests/test_nodes/` 전체 pass
- [ ] 각 Step별 커밋 완료 (Step 5 ✅ / 6 ✅ / 7~10 ⬜)
