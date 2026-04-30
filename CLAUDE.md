# CLAUDE.md

> Rule: This file must stay under 100 lines.

travel-k-integrator — Gap-driven 지식 통합 파이프라인. 0th Rule: 단순해야 한다.

## Core Rules

1. **Phase 순서 불변** — dev-smoke → dev-baseline → bronze-v1 순서. 앞 Phase 합격 전 다음 Phase 진입 금지.
2. **active KU 1개 제한** — `(entity_key, field)` 조합당 `status=active` KU는 정확히 1개. 위반 시 state 오염.
3. **Evidence-first** — `evidence_links`가 빈 KU는 active 불가. EU 없이 active로 올리면 불변원칙 3 위반.
4. **Conflict-preserving** — 충돌 Claim은 삭제하지 말고 `status=conflicting` KU로 보존. 덮어쓰기 금지.
5. **Prescription-compiled Bronze 폐기** — critique 노드는 수렴/강제종료 판정만. prescription 생성 로직 추가 금지 (D11).
6. **failed GU 재시도 없음** — Bronze에서 failed GU는 방치. 0-claim 3회 누적 카운터 초기화 금지. 재시도는 post-Bronze.

## Common Commands

```bash
python scripts/run_bronze.py --phase dev-smoke    --trial-id 1 --cycles 5  --bench-root bench/japan-travel
python scripts/run_bronze.py --phase dev-baseline --trial-id 1 --cycles 10 --bench-root bench/japan-travel
python scripts/run_bronze.py --phase bronze-v1    --trial-id 1 --cycles 20 --bench-root bench/japan-travel
python -m pytest
```

## Dev Workflow

- `/step-update` runs once per **Phase** completion — 모든 Step 구현 완료 후 1회. Step마다 실행 금지.
- Step 구현 후: `git add <파일> && git commit -m "Step X: ..."` 직접 커밋 (phase docs 업데이트 없음).

## Naming Conventions

- **entity_key**: `{domain}:{category}:{slug}` → e.g., `japan-travel:transport:jr-pass`
- **run-id**: `<phase>-t<trial-id>` → e.g., `dev-smoke-t1`
- **Commits**: `Step X: description` (숫자 prefix 필수, 없으면 roadmap 추적 불가)

## Constraints

- 새 runner 스크립트 추가 금지 — `run_bronze.py`에 flag로 확장.
- `--snapshot-every` 기본 OFF — 명시 시에만 활성화. 기본 실행에 추가 금지.
- `max_gus_per_cycle = 25` hard cap — plan 노드에서 초과 생성 금지.
- LLM 모델 고정: `gpt-4.1-mini`, `temperature=0.0`, `max_tokens=1024`. 임의 변경 금지.

## Encoding / Environment

- 파일 I/O 전체: `encoding='utf-8'` 명시 필수. Windows 기본 인코딩 의존 금지.
- API 키: `OPENAI_API_KEY`, `TAVILY_API_KEY` 필수. `.env.example` 참조.
