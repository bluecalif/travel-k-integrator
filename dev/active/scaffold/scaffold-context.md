# scaffold Phase Context
> Gen: bronze
> Last Updated: 2026-04-30
> Status: Complete

---

## 0. 구현 완료 파일 (2026-04-30)

| 파일 | Step | Commit |
|------|------|--------|
| `src/__init__.py`, `src/graph.py` (stub), `src/state.py` (stub) | 1 | 3e9a686 |
| `src/config.py` (stub), `src/nodes/__init__.py`, `src/adapters/__init__.py`, `src/utils/__init__.py` | 1 | 3e9a686 |
| `tests/__init__.py`, `tests/test_nodes/__init__.py`, `tests/test_utils/__init__.py` | 1 | 3e9a686 |
| `.env.example`, `.gitignore`, `pyproject.toml`, `schemas/.gitkeep` | 1 | 3e9a686 |
| `src/state.py` (BronzeState 전체 dataclass), `src/config.py` (BronzeConfig) | 2 | 8075941 |
| `schemas/knowledge-unit.json`, `schemas/evidence-unit.json`, `schemas/gap-unit.json` | 2 | 8075941 |
| `schemas/domain-skeleton.json`, `schemas/entity-registry.json` | 2 | 8075941 |
| `src/adapters/llm_adapter.py`, `src/adapters/search_adapter.py` | 3 | bbbe14a |
| `src/utils/llm_parse.py`, `src/utils/state_io.py`, `src/utils/cost_guard.py` | 3 | bbbe14a |
| `src/utils/entity_resolver.py`, `src/utils/invariant_checker.py`, `src/utils/metrics.py`, `src/utils/schema_validator.py` | 3 | bbbe14a |

### 주요 구현 결정

- `cost_guard.py`: USD 누적 비용 기반 kill-switch (domain-k-evolver의 call-count 방식 대신)
- `state_io.py`: BronzeState 8개 JSON 파일로 분리 저장 (entity-registry, knowledge-units, evidence-units, gap-map, domain-skeleton, metrics, category-saturation, run-meta)
- `schema_validator.py`: Draft202012Validator → Draft7Validator (schemas/가 draft-07 기반)

---

## 1. 핵심 파일

### 반드시 읽어야 할 문서

| 파일 | 읽어야 할 섹션 | 용도 |
|------|--------------|------|
| `docs/masterplan_v0-reference.md` | §D State Dataclass | state.py 구현 기준 |
| `docs/masterplan_v0-reference.md` | §F 환경변수 | .env.example + config.py |
| `docs/masterplan_v0-reference.md` | §B Instance 예시 | schemas/*.json 역설계 |
| `docs/masterplan_v0-reference.md` | §G.1 직접 재사용 | adapters + utils 복사 기준 |
| `docs/masterplan_v0-reference.md` | §G.2 재해석 필요 | invariant_checker, metrics, entity_resolver |
| `docs/masterplan_v0-reference.md` | §G.4 사용 금지 | 절대 포함하지 말 것 |

### 참조 프로젝트 경로

`C:\Users\User\Learning\KBs-2026\domain-k-evolver\src\`

| 파일 | Bronze 처리 | 주의사항 |
|------|------------|---------|
| `utils/llm_parse.py` | 직접 재사용 | extract_json 함수만 사용 |
| `utils/schema_validator.py` | 직접 재사용 | schemas/ 경로를 이 프로젝트로 수정 |
| `utils/state_io.py` | 직접 재사용 | BronzeState 타입으로 교체 |
| `utils/cost_guard.py` | 직접 재사용 | budget_cap_usd 파라미터 확인 |
| `adapters/llm_adapter.py` | 직접 재사용 | default model을 gpt-4.1-mini로 |
| `adapters/search_adapter.py` | 직접 재사용 | 그대로 |
| `config.py` | 직접 재사용 | from_env 패턴, BRONZE_ prefix env var |
| `utils/entity_resolver.py` | 재해석 | alias registry 제거. canonicalize + similarity만 |
| `utils/invariant_checker.py` | 재해석 | 불변원칙 5 (Prescription-compiled) 제거 |
| `utils/metrics.py` | 재해석 | 3개만: gap_resolution_rate, avg_confidence, evidence_rate |

---

## 2. 데이터 인터페이스

**입력**: 없음 (scaffold는 외부 데이터 의존 없음)

**출력**:
- `src/state.py` → 모든 노드가 import
- `src/config.py` → 모든 노드가 import
- `schemas/*.json` → schema_validator가 로드
- `src/utils/*`, `src/adapters/*` → 노드 구현 시 import

---

## 3. 주요 결정사항

| 결정 | 내용 | 이유 |
|------|------|------|
| State 구현 방식 | Python dataclass (Pydantic 아님) | LangGraph 호환성 확보. asdict/from_dict 헬퍼로 연동 |
| LangGraph 연동 | Step 11 (graph.py)로 보류 | scaffold에서 langgraph import 최소화 |
| invariant_checker | 4대 불변원칙 (Prescription-compiled 제거) | D11 결정. Bronze critique = 수렴 판정만 |
| metrics | gap_resolution_rate + avg_confidence + evidence_rate 3개만 | coverage/novelty 제거 (SI-P4 Drop) |
| entity_resolver | difflib.SequenceMatcher for similarity | 외부 embedding 없이 slug 기반 비교 |
| 테스트 전략 | scaffold 단계는 L1 테스트 없음 | adapters는 API key 의존. nodes Phase에서 mock 테스트 작성 |
| 경로 처리 | `pathlib.Path` 일관 사용 | Windows/Unix 호환 |

---

## 4. 컨벤션 체크리스트

### 코드 컨벤션

- [ ] 모든 파일 `encoding='utf-8'` 명시 (파일 read/write 시)
- [ ] 경로: `pathlib.Path` 사용. 문자열 경로 join 금지
- [ ] import 순서: stdlib → 서드파티 → 내부 모듈
- [ ] dataclass field default: `field(default_factory=...)` 사용 (mutable default 금지)
- [ ] config.py: API key는 `redact()` 통해서만 로그 출력

### 4대 불변원칙 반영 위치

| 원칙 | scaffold에서 반영 |
|------|-----------------|
| Gap-driven | state.py `gap_map` 필드 존재 |
| Claim→KU 착지성 | state.py `pending_claims` → `knowledge_units` 경로 명확 |
| Evidence-first | state.py KU에 `evidence_links: list[str]` 필드 |
| Conflict-preserving | state.py KU `status: Literal["active", "conflicting", "archived"]` |

### invariant_checker.py 체크 항목 (4대)

```python
def check_evidence_first(state: BronzeState) -> list[str]:
    """active KU 중 evidence_links=[] 인 것 반환"""

def check_active_ku_uniqueness(state: BronzeState) -> list[str]:
    """(entity_key, field) 조합에 active KU 2개 이상인 것 반환"""

def check_gap_driven(state: BronzeState) -> list[str]:
    """resolved GU 없이 생성된 active KU 탐지"""

def check_conflict_preserving(state: BronzeState) -> list[str]:
    """conflicting value가 active로 덮어써진 흔적 탐지"""
```

### metrics.py 계산식

```python
gap_resolution_rate = resolved / (resolved + open + failed)  # failed 포함 분모
avg_confidence = sum(ku.confidence for ku in active_kus) / len(active_kus)
evidence_rate = len([ku for ku in active_kus if ku.evidence_links]) / len(active_kus)
# evidence_rate는 불변원칙 3에 의해 항상 1.0이어야 함
```

### schemas/ JSON Schema 구조

각 스키마 파일은 JSON Schema draft-07 형식:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "<schema-name>",
  "type": "object",
  "required": [...],
  "properties": { ... }
}
```

masterplan_v0-reference.md §B 인스턴스를 보고 역설계.

### .gitignore 필수 항목

```
.env
__pycache__/
*.pyc
.venv/
bench/*/runs/       # 실행 결과 (대용량 JSON)
*.log
```

### .env.example (§F 기준)

```bash
OPENAI_API_KEY=
TAVILY_API_KEY=
LLM_MODEL=gpt-4.1-mini
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=1024
BRONZE_MAX_GUS_PER_CYCLE=25
BRONZE_MAX_SEARCH_CALLS_PER_CYCLE=25
BRONZE_MAX_ENTITIES_PER_CATEGORY=20
BRONZE_SIMILARITY_THRESHOLD=0.85
BRONZE_SATURATION_CONSECUTIVE_THRESHOLD=2
BRONZE_GU_MAX_ATTEMPTS=3
BRONZE_BUDGET_CAP_USD=1.2
```
