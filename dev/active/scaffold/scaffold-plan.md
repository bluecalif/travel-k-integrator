# scaffold Phase Plan
> Gen: bronze
> Last Updated: 2026-04-30
> Status: Complete

---

## 1. Summary

**목적**: 모든 구현의 기반이 되는 프로젝트 골격을 확립.
코드 0줄 상태에서 `python -m pytest`가 통과하는 상태까지 도달.

**범위**: Steps 1–3
- Step 1: 디렉토리 구조 + 설정 파일
- Step 2: 데이터 모델 (state.py, config.py, schemas/*.json)
- Step 3: Adapters + Utils (공유 인프라)

**예상 결과물**:
- `src/` 전체 구조 (import 성공)
- `schemas/` JSON Schema 5개
- `tests/` 구조 + `python -m pytest` 통과 (0 테스트도 OK)
- `.env.example`, `.gitignore`, `pyproject.toml`

**후속 Phase 잠금 해제**: scaffold 완료 후 data(Step 4) + nodes(Steps 5–10) 동시 착수 가능

---

## 2. Current State

**✅ Complete (2026-04-30)** — Steps 1/2/3 커밋 완료. `python -m pytest` error 없음.

- Step 1 (3e9a686): 프로젝트 골격 — src/, tests/, schemas/, pyproject.toml 등 14 files
- Step 2 (8075941): state.py (BronzeState 전체), config.py (BronzeConfig), schemas 5개
- Step 3 (bbbe14a): adapters 2개 + utils 7개 구현

---

## 3. Target State

```
travel-k-integrator/
├── src/
│   ├── __init__.py
│   ├── state.py          ← BronzeState + KU/EU/GU/EntityMeta/CategorySaturation
│   ├── config.py         ← BronzeConfig.from_env(), redact(), write_config_snapshot()
│   ├── graph.py          ← stub (TODO placeholder)
│   ├── nodes/__init__.py
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── llm_adapter.py
│   │   └── search_adapter.py
│   └── utils/
│       ├── __init__.py
│       ├── llm_parse.py
│       ├── state_io.py
│       ├── cost_guard.py
│       ├── entity_resolver.py
│       ├── invariant_checker.py
│       ├── metrics.py
│       └── schema_validator.py
├── schemas/
│   ├── knowledge-unit.json
│   ├── evidence-unit.json
│   ├── gap-unit.json
│   ├── domain-skeleton.json
│   └── entity-registry.json
├── tests/
│   ├── __init__.py
│   ├── test_nodes/__init__.py
│   └── test_utils/__init__.py
├── .env.example
├── .gitignore
└── pyproject.toml
```

**합격 기준**: `python -m pytest` 실행 시 error 없음 (collected 0 items도 OK)

---

## 4. Implementation Stages

### Stage A — Step 1: 프로젝트 골격
디렉토리 구조 + 설정 파일 생성. 실제 로직 없음.

산출물: 모든 `__init__.py`, `graph.py` (stub), `.env.example`, `.gitignore`, `pyproject.toml`

**pyproject.toml 핵심**:
```toml
[project]
name = "travel-k-integrator"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "openai>=1.0",
    "tavily-python",
    "langgraph",
    "python-dotenv",
    "jsonschema",
    "difflib",      # stdlib, 명시 불필요 — entity_resolver similarity
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[build-system]
requires = ["setuptools"]
build-backend = "setuptools.backends.legacy:BuildBackend"
```

커밋: `Step 1: 프로젝트 골격 생성`

---

### Stage B — Step 2: 데이터 모델

#### 2-A: `src/state.py`
masterplan_v0-reference.md §D 그대로 구현:
- `EntityMeta`, `KU`, `EU`, `GU`, `CategorySaturation`, `BronzeState` dataclass
- 주의: LangGraph는 dict 기반 state를 선호 → `BronzeState`를 LangGraph에 등록할 때 `dataclasses.asdict()` / `from_dict()` 헬퍼 필요. 또는 TypedDict 방식 검토.

> **결정**: dataclass 유지. `graph.py`에서 LangGraph와 연결 시 wrapper 추가. state.py는 순수 Python dataclass.

#### 2-B: `src/config.py`
```python
@dataclass
class BronzeConfig:
    llm_model: str
    llm_temperature: float
    llm_max_tokens: int
    max_gus_per_cycle: int
    max_search_calls_per_cycle: int
    max_entities_per_category: int
    similarity_threshold: float
    saturation_consecutive_threshold: int
    gu_max_attempts: int
    budget_cap_usd: float
    bench_root: Path
    openai_api_key: str
    tavily_api_key: str

    @classmethod
    def from_env(cls, bench_root: str | Path) -> "BronzeConfig": ...
    def redact(self) -> dict: ...          # API key 마스킹
    def write_config_snapshot(self, path): ...
```

#### 2-C: `schemas/*.json`
5개 JSON Schema 파일. masterplan_v0-reference.md §B 인스턴스 기준으로 reverse-engineer.

커밋: `Step 2: state.py + config.py + schemas 구현`

---

### Stage C — Step 3: Adapters + Utils

domain-k-evolver 참조 후 Bronze 단순화 적용. 각 파일은 독립적 → 병렬 구현 가능.

| 파일 | 참조 | Bronze 단순화 |
|------|------|-------------|
| `llm_adapter.py` | G.1 직접 재사용 | model=gpt-4.1-mini override |
| `search_adapter.py` | G.1 직접 재사용 | 그대로 |
| `llm_parse.py` | G.1 직접 재사용 | `extract_json()` 그대로 |
| `state_io.py` | G.1 직접 재사용 | `load_state/save_state/snapshot_state` |
| `cost_guard.py` | G.1 직접 재사용 | budget_cap_usd 파라미터 |
| `entity_resolver.py` | G.2 재해석 | alias registry 제거, canonicalize + similarity만 |
| `invariant_checker.py` | G.2 재해석 | **5대 → 4대** (Prescription-compiled 제거) |
| `metrics.py` | G.2 재해석 | 3개만: gap_resolution_rate, avg_confidence, evidence_rate |
| `schema_validator.py` | G.1 직접 재사용 | schemas/ 경로 수정 |

커밋: `Step 3: adapters + utils 구현`

---

## 5. Task Breakdown

| # | Task | Size | 의존 | 비고 |
|---|------|------|------|------|
| 1.1 | Step 1: 프로젝트 골격 | M | — | pyproject.toml pythonpath 설정 필수 |
| 1.2 | Step 2: state.py | M | 1.1 | §D 그대로. LangGraph 연동은 Step 11로 |
| 1.3 | Step 2: config.py | S | 1.2 | from_env() + redact() + snapshot |
| 1.4 | Step 2: schemas/ (5개) | S | 1.2 | §B 인스턴스 기준 역설계 |
| 1.5 | Step 3: adapters/llm_adapter.py | S | 1.3 | G.1 직접 재사용 |
| 1.6 | Step 3: adapters/search_adapter.py | S | 1.3 | G.1 직접 재사용 |
| 1.7 | Step 3: utils/llm_parse.py | S | 1.2 | G.1 직접 재사용 |
| 1.8 | Step 3: utils/state_io.py | S | 1.2 | G.1 직접 재사용 |
| 1.9 | Step 3: utils/cost_guard.py | S | 1.3 | G.1 직접 재사용 |
| 1.10 | Step 3: utils/entity_resolver.py | S | 1.2 | G.2 재해석. difflib 사용 |
| 1.11 | Step 3: utils/invariant_checker.py | S | 1.2 | G.2 재해석. 4대로 축소 |
| 1.12 | Step 3: utils/metrics.py | S | 1.2 | G.2 재해석. 3개 지표만 |
| 1.13 | Step 3: utils/schema_validator.py | S | 1.4 | G.1 직접 재사용 |

**총계**: 13개 (M: 2, S: 11)

---

## 6. Risks & Mitigation

| Risk | 확률 | 영향 | 대응 |
|------|------|------|------|
| domain-k-evolver에서 불필요 코드 포함 | 중 | 중 | §G.4 금지 파일 목록 매번 확인. 함수 단위로 선택적 복사 |
| LangGraph와 dataclass 호환성 | 중 | 고 | Step 11까지 연동 보류. state.py는 순수 dataclass |
| Python path 문제 (pytest 실행) | 저 | 중 | pyproject.toml `pythonpath = ["."]` 설정으로 해결 |
| Windows 경로 (backslash) | 중 | 중 | `pathlib.Path` 일관 사용. 문자열 경로 금지 |
| API key 미설정으로 adapter 테스트 실패 | 저 | 저 | scaffold는 unit test 없음. adapters는 연결 테스트 skip |

---

## 7. Dependencies

**외부 라이브러리**:
- `openai>=1.0` — llm_adapter
- `tavily-python` — search_adapter
- `langgraph` — graph.py (Step 11에서 실사용)
- `python-dotenv` — config.py from_env()
- `jsonschema` — schema_validator
- `difflib` (stdlib) — entity_resolver similarity

**내부 의존 순서**:
```
state.py → config.py → adapters/* → utils/*
```
state.py가 최우선. config.py는 state.py import 없어도 독립 가능.
