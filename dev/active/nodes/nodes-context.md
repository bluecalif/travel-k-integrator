# nodes Phase Context
> Gen: bronze
> Last Updated: 2026-05-01

## 핵심 파일

### 읽어야 할 기존 코드

| 파일 | 용도 | 분류 |
|------|------|------|
| `src/state.py` | BronzeState, KU, EU, GU, EntityMeta, CategorySaturation | 필수 |
| `src/config.py` | BronzeConfig (max_gus_per_cycle, similarity_threshold 등) | 필수 |
| `src/utils/entity_resolver.py` | `similarity(a, b)` — entity_gen de-dup | 필수 |
| `src/utils/invariant_checker.py` | `check_active_ku_uniqueness`, `check_evidence_first` 등 | 필수 |
| `src/utils/llm_parse.py` | `extract_json(response_text)` — LLM 응답 파싱 | 필수 |
| `src/adapters/llm_adapter.py` | `LLMAdapter.complete(prompt)` 시그니처 | 필수 |
| `src/adapters/search_adapter.py` | `SearchAdapter.search(query)` 시그니처 | 필수 |
| `bench/japan-travel/seed-pack.json` | seed 노드 입력 | 필수 |
| `bench/japan-travel/domain-skeleton.json` | applicable_fields 계산 기준 | 필수 |
| `docs/masterplan_v0-reference.md` §C | 노드별 의사코드 + LLM 프롬프트 골격 | 필수 |

### domain-k-evolver 참조 (재해석)

| 파일 | 참조 포인트 |
|------|------------|
| `nodes/seed.py` | `_build_field_matrix` 패턴 — wildcard/risk_level 제거 |
| `nodes/collect.py` | `_search_for_gu`, `_build_provenance` — fallback chain 단순화 |
| `nodes/integrate.py` | `_find_matching_ku`, Rule 1 — Rule 2/3 제거, D4-A multi-KU 추가 |
| `nodes/critique.py` | `_check_convergence` C1/C2 — C3~C6 제거 |

---

## 데이터 인터페이스

### LangGraph 노드 시그니처

```python
def node_name(state: BronzeState) -> dict:
    # state를 읽고 변경할 필드만 dict로 반환
    return {"field_to_update": new_value, ...}
```

LangGraph가 반환된 dict를 기존 state에 병합. 전체 state 교체 아님.

### 노드별 입출력

| 노드 | 읽는 state 필드 | 반환(갱신) state 필드 |
|------|----------------|----------------------|
| seed | `domain_skeleton` | `entity_registry`, `knowledge_units`, `evidence_units`, `gap_map`, `category_saturation` |
| entity_gen | `entity_registry`, `category_saturation`, `domain_skeleton` | `entity_registry`, `gap_map`, `category_saturation` |
| plan | `entity_registry`, `gap_map`, `domain_skeleton` | `target_entities`, `plan_queue`, `gap_map` |
| collect | `plan_queue`, `gap_map` | `evidence_units`, `pending_claims`, `gap_map` |
| integrate | `pending_claims`, `knowledge_units`, `gap_map` | `knowledge_units`, `evidence_units`, `gap_map`, `pending_claims` |
| critique | `category_saturation`, `gap_map`, `current_cycle` | `terminate_reason` or `current_cycle` |

---

## 주요 결정사항

| ID | 결정 | 이유 |
|----|------|------|
| nodes-1 | LangGraph 노드 시그니처: `(BronzeState) → dict` | LangGraph StateGraph 요구사항. state 전체 반환 아님 |
| nodes-2 | L1 테스트: `unittest.mock.patch`로 LLMAdapter/SearchAdapter 대체 | API key 없이 결정론적 테스트 |
| nodes-3 | seed.py: BronzeState를 직접 받지 않고 파일 경로에서 로드 | seed는 1회성 초기화 노드. config에서 bench_root 읽음 |
| nodes-4 | integrate.py `_same_value`: 정확 일치 + 숫자 정규화만 | 의미적 동치 LLM 비교는 Silver(D11) |
| nodes-5 | entity_gen.py: 카테고리당 1개 후보만 생성 (배치 아님) | 비용 제어 + 단순성 |
| nodes-6 | critique.py: `terminate_reason` 설정 후 graph routing에서 END/CONTINUE 분기 | 노드 자체가 END를 직접 반환하지 않음 — graph.py에서 처리 |
| nodes-7 | entity_gen.py: 전역 de-dup 추가 — 모든 카테고리 slug 대비 sim≥0.85 거부 | 크로스-카테고리 중복 방지 (예: transport:jr-pass가 있으면 pass-ticket:jr-pass 거부) |
| nodes-8 | entity_gen.py: LLM 프롬프트에 전체 레지스트리 entity 목록 + 추상 개념 금지 조건 추가 | 실제 실행 결과에서 dining:sushi (추상) 생성 → 품질 개선 필요 확인 후 반영 |
| nodes-9 | entity_gen.py: `_llm_generate_candidate`에서 API 에러는 propagate (saturation 카운터 오염 방지) | API 인증 오류 시 전 카테고리 failures=1 오염 발생 → except 범위를 ValueError로 한정 |
| nodes-10 | plan.py: `target_entity: str \| None` → `target_entities: dict[str, str]` (카테고리당 1개 entity 선정) | 카테고리별 독립 entity selection으로 multi-category 병렬 처리 가능. downstream (collect, integrate)은 plan_queue GU ID만 사용 — target_entities 직접 참조 없음 |
| nodes-11 | collect.py: EU는 claim 추출 실패해도 생성 (evidence-first). 1 GU = 1 Tavily query | EU는 GU 처리 즉시 생성. snippet 없는 result도 EU로 기록 |
| nodes-12 | integrate.py: `_same_value` — 정확 일치 + 숫자 정규화 (`"50,000"` ↔ `50000`). 의미적 동치 LLM 비교 Silver 이후 | D4-A: Case C에서 active KU 절대 수정 금지, conflicting KU 신규 생성만 |
| nodes-13 | critique.py: `BronzeConfig.max_cycles` 추가 (env: `BRONZE_MAX_CYCLES`, 기본값 20) | run_bronze.py `--cycles` 플래그와 연동. dev-smoke=5, dev-baseline=10, bronze-v1=20 |

---

## L1 테스트 전략

### Mock 패턴

```python
# LLM mock
from unittest.mock import patch, MagicMock

def test_entity_gen_registers_new_entity(base_state):
    mock_response = '{"slug": "shinkansen", "name": "신칸센"}'
    with patch("src.nodes.entity_gen.LLMAdapter") as MockLLM:
        MockLLM.return_value.complete.return_value = mock_response
        result = entity_gen(base_state)
    assert "japan-travel:transport:shinkansen" in result["entity_registry"]
```

### 픽스처 설계

- `conftest.py` 에 `base_state` fixture: 최소 BronzeState (seed 완료 후 상태)
- 각 테스트 파일은 해당 노드에만 필요한 state 필드 설정
- 절대 실제 API 호출 없음 (OPENAI_API_KEY, TAVILY_API_KEY 환경변수 불필요)

### 불변원칙 검증 항목 (integrate.py L1 필수)

```python
# 불변원칙 2: (entity_key, field) active KU ≤ 1
active_for_field = [
    ku for ku in state.knowledge_units
    if ku.entity_key == ek and ku.field == f and ku.status == "active"
]
assert len(active_for_field) == 1

# 불변원칙 3: active KU는 evidence_links ≥ 1
for ku in state.knowledge_units:
    if ku.status == "active":
        assert len(ku.evidence_links) >= 1
```

---

## 컨벤션 체크리스트

**노드 구현:**
- [ ] 모든 노드: `(BronzeState) → dict` 시그니처
- [ ] seed.py: `_resolve_applicable_fields(category, skeleton)` 헬퍼 — `["*"]` 처리
- [ ] entity_gen.py: consecutive_failures 카운터는 CategorySaturation.consecutive_failures 사용
- [ ] plan.py: `plan_queue = open_gus[:config.max_gus_per_cycle]` (25 hard cap)
- [ ] collect.py: EU는 GU당 최대 3개 snippet, Claim 없으면 attempts+1
- [ ] integrate.py: Case C는 conflicting KU 신규 생성 (active KU 절대 수정 금지)
- [ ] critique.py: prescription 생성 로직 추가 금지 (D11)

**테스트:**
- [ ] 모든 테스트: mock으로 실제 API 호출 없음
- [ ] `conftest.py`: `base_state` fixture 정의
- [ ] 각 테스트: 단일 노드의 state 변화만 검증

**인코딩/LLM:**
- [ ] 파일 I/O: `encoding='utf-8'`
- [ ] LLM 호출: `model=gpt-4.1-mini`, `temperature=0.0`, `max_tokens=1024`

---

## ID 생성 규칙

```python
import uuid

def new_ku_id(knowledge_units: list) -> str:
    return f"KU-{len(knowledge_units)+1:04d}"

def new_eu_id(evidence_units: list) -> str:
    return f"EU-{len(evidence_units)+1:04d}"

def new_gu_id(gap_map: list) -> str:
    return f"GU-{len(gap_map)+1:04d}"
```

순번 기반. 충돌 없음 (per-run 단일 프로세스).
