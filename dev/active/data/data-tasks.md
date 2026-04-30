# data Phase Tasks
> Gen: bronze
> Last Updated: 2026-04-30
> Status: Complete (2/2, 100%)

## Summary

- **총 Tasks**: 2 (M: 2)
- **완료**: 2/2 (100%)
- **Step**: 4 ✅
- **합격 기준**: domain-skeleton.json + seed-pack.json 완성, seed 노드가 오류 없이 로드 가능

---

## Stage A — Step 4a: domain-skeleton.json

| # | Task | Size | Status | Commit |
|---|------|------|--------|--------|
| 2.1 | `bench/japan-travel/domain-skeleton.json` — §A 인스턴스 그대로 작성 (8 categories, 11 fields) | M | ✅ | ce09b73 |

**완료 조건**:
- [ ] §A 인스턴스와 100% 동일
- [ ] `schemas/domain-skeleton.json` 유효성 검증 통과

---

## Stage B — Step 4b: seed-pack.json

| # | Task | Size | Status | Commit |
|---|------|------|--------|--------|
| 2.2 | `bench/japan-travel/seed-pack.json` — 8 categories × 1–2 entity, 각 initial_knowledge 1–2개 | M | ✅ | ce09b73 |

**완료 조건**:
- [ ] 8 categories 전부 커버 (category당 ≥ 1 entity)
- [ ] entity_key 형식 `japan-travel:{category}:{slug}` 준수
- [ ] initial_knowledge 각 항목: field + value + source(url/title/snippet)
- [ ] data-context.md 포맷과 일치

---

## 완료 체크

- [x] 2/2 Tasks ✅
- [x] bench/japan-travel/ 디렉토리에 두 파일 존재
- [x] Step 4 커밋 완료: `ce09b73 Step 4: bench/japan-travel 데이터 큐레이션`
