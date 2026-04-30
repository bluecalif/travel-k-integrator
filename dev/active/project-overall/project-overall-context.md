# Project Overall Context
> Gen: bronze
> Last Updated: 2026-04-30

## 핵심 파일

| 파일 | 용도 |
|------|------|
| `docs/masterplan_v0.md` | 파이프라인 구조, 4대 불변원칙, 검증 전략, 데이터 모델 |
| `docs/masterplan_v0-reference.md` | §A 도메인 스키마, §B 인스턴스 예시, §C 노드 의사코드+프롬프트, §D State dataclass, §F env 예시, §G 참조 파일 분류 |
| `docs/bird-view.md` | 파이프라인 조감도 (preliminary — 코드 생성 후 갱신 필요) |
| `CLAUDE.md` | Core Rules, 명령어, Constraints, Naming 규약 |

## 참조 프로젝트

**domain-k-evolver** (`C:\Users\User\Learning\KBs-2026\domain-k-evolver`):

| 분류 | 파일 | 처리 방향 |
|------|------|----------|
| 직접 재사용 | `utils/llm_parse.py`, `utils/schema_validator.py`, `utils/state_io.py`, `utils/cost_guard.py`, `adapters/llm_adapter.py`, `adapters/search_adapter.py`, `config.py` | 그대로 복사 후 최소 수정 |
| 재해석 필요 | `utils/entity_resolver.py`, `utils/invariant_checker.py`, `nodes/collect.py`, `nodes/integrate.py`, `nodes/seed.py`, `nodes/critique.py`, `graph.py`, `utils/metrics.py` | 참조하되 Bronze 단순화 반영 |
| 사용 금지 | `nodes/mode.py`, `nodes/remodel.py`, `nodes/audit.py`, `utils/coverage_map.py`, `utils/novelty.py`, `utils/policy_manager.py`, `utils/readiness_gate.py` | Dead copy 절대 금지 |

## 주요 결정사항

| ID | 결정 | 이유 |
|----|------|------|
| D1-B | Category↔Field 매트릭스 domain-skeleton.json에 명시 | entity 등록 시 적용 가능 필드만 mandatory GU 생성 |
| D2-A | Claim 1개 = EU 1개 (1:1) | 출처 추적성 확보 |
| D3-A | GU lifecycle: open→resolved(EU≥1) / open→failed(0-claim×3) | failed GU 재시도 없음 (post-Bronze) |
| D4-A | 충돌 Claim → conflicting KU 보존 (삭제 금지) | Conflict-preserving 불변원칙 |
| D7-A | seed→entity_gen→plan→collect→integrate→critique 6노드 | Silver 6노드와 정합 |
| D8 | entity_gen: 연속 2회 후보 실패 → 카테고리 포화 마킹 | LLM 호출 낭비 방지 |
| D9 | trajectory.json 누적, state snapshot 기본 OFF | 비용 제어 |
| D10 | Staleness/TTL Bronze Drop | 단순화 |
| D11 | Prescription-compiled Bronze 폐기. Critique = 수렴 판정만 | 복잡도 제거 |
| scaffold-1 | State 구현: Python dataclass (Pydantic 아님) | LangGraph 호환. asdict/from_dict 헬퍼로 연동 |
| scaffold-2 | entity_resolver similarity: difflib.SequenceMatcher | 외부 embedding 없이 slug 기반 비교 |
| scaffold-3 | adapters L1 테스트: scaffold 단계 없음 | API key 의존. nodes Phase에서 mock 테스트 작성 |
| data-1 | seed-pack.json 포맷: entities 배열 + initial_knowledge(field+value+EU정보) | seed 노드가 단일 파일로 entity 등록 + KU/EU 생성 처리 |
| data-2 | domain-skeleton.json: §A 인스턴스 그대로 사용 | masterplan 정합성 유지 |

## 4대 불변원칙 (Bronze)

1. **Gap-driven** — Plan은 GU가 구동
2. **Claim→KU 착지성** — 모든 Claim은 KU로 변환
3. **Evidence-first** — KU는 EU≥1 없이 active 불가
4. **Conflict-preserving** — 충돌 값은 conflicting KU로 보존 (덮어쓰기 금지)

> **불변원칙 5 (Prescription-compiled)**: Bronze에서 명시적 폐기 (D11). Critique는 수렴 판정만.

## 데이터 인터페이스

**입력**:
- `bench/japan-travel/seed-pack.json` — seed entity + 초기 KU 값 (수작업 큐레이션)
- `bench/japan-travel/domain-skeleton.json` — Category↔Field 매트릭스

**출력** (`bench/japan-travel/runs/<run-id>/`):
- `state/entity-registry.json` — 등록된 전체 entity
- `state/knowledge-units.json` — 전체 KU (active + conflicting + archived)
- `state/evidence-units.json` — 전체 EU
- `state/gap-map.json` — 전체 GU (open + resolved + failed)
- `state/metrics.json` — gap_resolution_rate, avg_confidence, evidence_rate
- `trajectory/trajectory.json` — cycle별 record 누적
- `report.md` — 자동 생성 요약

## 컨벤션 체크리스트

**Naming:**
- [ ] entity_key 형식: `{domain}:{category}:{slug}` (소문자 + 하이픈)
- [ ] run-id 형식: `<phase>-t<trial-id>` (예: `dev-smoke-t1`)
- [ ] Commit 형식: `Step X: 한국어 설명`

**코드:**
- [ ] LLM: `model=gpt-4.1-mini`, `temperature=0.0`, `max_tokens=1024` (고정)
- [ ] `max_gus_per_cycle=25` hard cap — plan.py 슬라이싱
- [ ] active KU per (entity_key, field) = 정확히 1개
- [ ] evidence_links 비면 active 불가 (불변원칙 3)
- [ ] 새 runner 스크립트 추가 금지 — `run_bronze.py`에 flag로 확장
- [ ] `--snapshot-every` 기본 OFF

**인코딩:**
- [ ] 파일 I/O 전체: `encoding='utf-8'` 명시 필수
- [ ] Python 실행: `PYTHONUTF8=1`

## Metrics 합격 임계치

| Phase | 지표 | 임계치 |
|-------|------|--------|
| L2 (dev-smoke, 5c) | KU 증가, GU≥1 resolved, 정상 종료 | 정성 확인 |
| L3 (dev-baseline, 10c) | gap_resolution_rate | ≥ 0.4 |
| L3 | avg_confidence | ≥ 0.6 |
| L3 | evidence_rate | = 1.0 |
| L3 | 모든 카테고리 entity 수 | ≥ 1 |
| L4 (bronze-v1, 20c) | open gap 해결 비율 또는 수렴 | ≥ 80% 또는 converged |
| L4 | budget | ≤ $1.2 |
