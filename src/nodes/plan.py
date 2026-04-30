from __future__ import annotations

from datetime import datetime, timezone

from src.config import BronzeConfig
from src.nodes.seed import _resolve_applicable_fields
from src.state import BronzeState, GU


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def plan(state: BronzeState) -> dict:
    """카테고리별 target entity 선정 → gap_gen → plan_queue 구성.

    open GU 최다 entity를 카테고리마다 1개 선정.
    선정 entity의 applicable fields 중 GU가 전혀 없는 field에 open GU 생성.
    모든 카테고리 target entity의 open GU를 합쳐 max_gus_per_cycle cap 적용.
    """
    config = BronzeConfig.from_env()
    skeleton = state.domain_skeleton
    categories = [cat["slug"] for cat in skeleton.get("categories", [])]

    entity_registry = state.entity_registry
    gap_map = list(state.gap_map)

    target_entities: dict[str, str] = {}
    all_plan_gus: list[GU] = []
    now = _now_iso()

    for cat in categories:
        cat_entity_keys = [ek for ek, meta in entity_registry.items() if meta.category == cat]
        if not cat_entity_keys:
            continue

        open_counts = {
            ek: sum(1 for g in gap_map if g.entity_key == ek and g.status == "open")
            for ek in cat_entity_keys
        }
        entities_with_open = [ek for ek, cnt in open_counts.items() if cnt > 0]
        if not entities_with_open:
            continue

        selected = max(entities_with_open, key=lambda ek: open_counts[ek])
        target_entities[cat] = selected

        # gap_gen: applicable fields 중 GU가 전혀 없는 field에 open GU 추가
        applicable = _resolve_applicable_fields(cat, skeleton)
        existing_gu_fields = {g.field for g in gap_map if g.entity_key == selected}
        for f in applicable:
            if f not in existing_gu_fields:
                gap_map.append(GU(
                    gu_id=f"GU-{len(gap_map) + 1:04d}",
                    entity_key=selected,
                    field=f,
                    status="open",
                    created_at=now,
                ))

        open_gus = [g for g in gap_map if g.entity_key == selected and g.status == "open"]
        all_plan_gus.extend(open_gus)

    plan_queue = [g.gu_id for g in all_plan_gus[:config.max_gus_per_cycle]]

    return {
        "target_entities": target_entities,
        "plan_queue": plan_queue,
        "gap_map": gap_map,
    }
