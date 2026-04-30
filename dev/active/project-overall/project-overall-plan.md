# Project Overall Plan
> Gen: bronze
> Last Updated: 2026-04-30
> Status: scaffold ✅ — data Phase 대기

## Summary

travel-k-integrator Bronze Gen: Gap-driven 지식 통합 파이프라인 MVP.
Japan Travel 도메인에서 entity별 순차 처리로 Knowledge Graph 구축.
목표: dev-smoke(5c) → dev-baseline(10c) → bronze-v1(20c) 순차 합격.

## Gen Roadmap

| Gen | Label | 목적 |
|-----|-------|------|
| **A (current)** | bronze | MVP. 단일 entity 순차 처리, Gap-driven KG 파이프라인 |
| B | silver | Prescription-compiled critique, HITL gate, staleness TTL |
| C | gold | 다중 도메인, 확장성 |

---

## Phase Overview

| Phase | Steps | 목적 | 합격 기준 | Status |
|-------|-------|------|----------|--------|
| **scaffold** | 1–3 | 프로젝트 골격 + state + adapters + utils | 전체 import 성공, `python -m pytest` 통과 | ✅ Complete |
| **data** | 4 | bench/japan-travel 데이터 수작업 큐레이션 | seed-pack.json + domain-skeleton.json 완성 | ⬜ |
| **nodes** | 5–10 | 6개 노드 구현 + L1 단위 테스트 | 각 노드 L1 100% pass | ⬜ |
| **runner** | 11 | graph.py + scripts/run_bronze.py | 1-cycle dry-run 오류 없음 | ⬜ |
| **validation** | 12–14 | dev-smoke → dev-baseline → bronze-v1 순차 합격 | L2 → L3 → L4 | ⬜ |

---

## Current State

- 프로젝트 인프라 완비 (CLAUDE.md, 글로벌 커맨드, 설정)
- `docs/` 완성: masterplan_v0.md, masterplan_v0-reference.md, bird-view.md (preliminary)
- `dev/active/project-overall/` 완성 (2026-04-30)
- **scaffold Phase ✅ Complete** — Steps 1–3 커밋 완료 (3e9a686 / 8075941 / bbbe14a)
  - `python -m pytest` 통과, 전체 import 성공
- **data Phase 대기 중** — bench/japan-travel/ 큐레이션 착수 전

---

## Phase Detail

### Phase 1: scaffold (Steps 1–3)

**목적**: 구현 시작 전 모든 인프라 확보

**Stages:**
- Stage A (Step 1): 프로젝트 골격 생성
  - `src/__init__.py`, `src/state.py` (stub), `src/graph.py` (stub), `src/config.py` (stub)
  - `src/nodes/__init__.py`, `src/adapters/__init__.py`, `src/utils/__init__.py`
  - `tests/__init__.py`, `tests/test_nodes/__init__.py`, `tests/test_utils/__init__.py`
  - `schemas/.gitkeep`, `.env.example`, `.gitignore`, `pyproject.toml`
- Stage B (Step 2): 데이터 모델 구현
  - `src/state.py`: BronzeState, KU, EU, GU, EntityMeta, CategorySaturation dataclass
  - `src/config.py`: BronzeConfig.from_env(), redact(), write_config_snapshot()
  - `schemas/`: knowledge-unit.json, evidence-unit.json, gap-unit.json, domain-skeleton.json, entity-registry.json
- Stage C (Step 3): Adapters + Utils
  - `adapters/llm_adapter.py`, `adapters/search_adapter.py`
  - `utils/llm_parse.py`, `utils/state_io.py`, `utils/cost_guard.py`
  - `utils/entity_resolver.py`, `utils/invariant_checker.py`, `utils/metrics.py`, `utils/schema_validator.py`

**참조**: masterplan_v0-reference.md §D (State dataclass), §F (.env.example), §G.1 (domain-k-evolver 재사용 파일)
**산출물**: 전체 src/ 구조, `python -m pytest` 통과

---

### Phase 2: data (Step 4)

**목적**: L2/L3/L4 실행에 필요한 bench 데이터 수작업 큐레이션

**Stages:**
- Stage A: `bench/japan-travel/domain-skeleton.json`
  - 8 categories × 11 fields Category↔Field 매트릭스 (masterplan_v0-reference.md §A 기준)
- Stage B: `bench/japan-travel/seed-pack.json`
  - 8개 카테고리 × 1–2 entity, 각 entity 1–2개 초기 KU 값

**참조**: masterplan_v0-reference.md §A (domain-skeleton 인스턴스), §B.1 (entity-registry 예시)
**산출물**: bench/japan-travel/domain-skeleton.json, bench/japan-travel/seed-pack.json

---

### Phase 3: nodes (Steps 5–10)

**목적**: 파이프라인 6개 노드 구현 + L1 단위 테스트

**Stages:**
- Stage A (Step 5): `nodes/seed.py` + `tests/test_nodes/test_seed.py`
  - seed-pack 로드 → entity 등록 + 초기 KU/EU + mandatory GU 생성
- Stage B (Step 6): `nodes/entity_gen.py` + `tests/test_nodes/test_entity_gen.py`
  - LLM 후보 생성, de-dup (sim≥0.85), 포화 마킹 (연속 2회 실패)
- Stage C (Step 7): `nodes/plan.py` + `tests/test_nodes/test_plan.py`
  - entity_select (vacant 최다), gap_gen (재확인), slicing (max_gus_per_cycle=25)
- Stage D (Step 8): `nodes/collect.py` + `tests/test_nodes/test_collect.py`
  - 1 GU → 1 Tavily query → snippets → LLM Claim 추출, 0-claim 카운트
- Stage E (Step 9): `nodes/integrate.py` + `tests/test_nodes/test_integrate.py`
  - Case A (신규) / Case B (동일값 보강) / Case C (충돌→conflicting KU, D4-A)
- Stage F (Step 10): `nodes/critique.py` + `tests/test_nodes/test_critique.py`
  - 수렴(all_saturated AND open=0) / 강제종료(max_cycles) 판정만

**참조**: masterplan_v0-reference.md §C (의사코드 + 프롬프트)
**산출물**: 6개 노드 파일 + 6개 테스트 파일. 전체 L1 100% pass

---

### Phase 4: runner (Step 11)

**목적**: 전체 파이프라인 연결 + CLI 엔트리포인트

**Stages:**
- Stage A: `src/graph.py`
  - LangGraph StateGraph: seed → entity_gen → plan → collect → integrate → critique
  - routing: critique → CONTINUE (loop) / END
- Stage B: `scripts/run_bronze.py`
  - `--phase`, `--trial-id`, `--cycles`, `--bench-root`
  - `[--resume]`, `[--snapshot-every N]`, `[--evaluate-only]`
  - run-id = `<phase>-t<trial-id>`, 출력 `<bench-root>/runs/<run-id>/`

**참조**: masterplan_v0-reference.md §C.5 (routing 로직), §G.2 (graph.py 패턴)
**산출물**: `python scripts/run_bronze.py --phase dev-smoke --trial-id 1 --cycles 1` 실행 가능

---

### Phase 5: validation (Steps 12–14)

**목적**: 3단계 검증 순차 합격. 앞 Phase 실패 시 nodes/runner 수정 후 재시도.

**Stages:**
- Stage A (Step 12): L2 dev-smoke — 5 cycles
  - 합격: E2E 진행, KU 증가, GU ≥1 resolve, 정상 종료
- Stage B (Step 13): L3 dev-baseline — 10 cycles
  - 합격: gap_resolution_rate ≥ 0.4, avg_confidence ≥ 0.6, evidence_rate = 1.0, 모든 카테고리 entity ≥ 1
- Stage C (Step 14): L4 bronze-v1 — 20 cycles
  - 합격: 수렴 또는 open gap ≥80% 해결, budget ≤ $1.2

**제약**: Phase 순서 불변. dev-smoke 실패 시 bronze-v1 진입 금지.
