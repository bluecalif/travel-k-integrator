from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.state import BronzeState, CategorySaturation, EU, EntityMeta, GU, KU


def _resolve_applicable_fields(category: str, skeleton: dict) -> list[str]:
    """skeleton fields 중 category에 적용 가능한 field 이름 목록 반환.

    categories: ["*"] → 모든 카테고리 적용.
    그 외 → 명시된 카테고리에만 적용.
    """
    result = []
    for field_def in skeleton.get("fields", []):
        cats = field_def.get("categories", [])
        if "*" in cats or category in cats:
            result.append(field_def["name"])
    return result


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def seed(state: BronzeState, config: dict) -> dict:
    """seed-pack.json → entity_registry + 초기 KU/EU + mandatory GU 생성.

    entity_registry가 이미 채워진 경우 no-op (재진입 방지).
    config["configurable"]["bench_root"] 에서 bench 디렉토리 경로를 읽는다.
    """
    if state.entity_registry:
        return {}

    bench_root = Path(config["configurable"]["bench_root"])
    with open(bench_root / "seed-pack.json", encoding="utf-8") as f:
        seed_pack = json.load(f)

    skeleton = state.domain_skeleton
    domain = seed_pack["domain"]

    entity_registry: dict[str, EntityMeta] = {}
    knowledge_units: list[KU] = []
    evidence_units: list[EU] = []
    gap_map: list[GU] = []
    category_saturation: dict[str, CategorySaturation] = {
        cat["slug"]: CategorySaturation()
        for cat in skeleton.get("categories", [])
    }

    now = _now_iso()

    for entity in seed_pack.get("entities", []):
        category = entity["category"]
        slug = entity["slug"]
        entity_key = f"{domain}:{category}:{slug}"

        entity_registry[entity_key] = EntityMeta(
            category=category,
            name=entity["name"],
            registered_at=now,
            source="seed",
        )

        covered_fields: set[str] = set()
        for ik in entity.get("initial_knowledge", []):
            field = ik["field"]
            eu_id = f"EU-{len(evidence_units) + 1:04d}"
            evidence_units.append(EU(
                eu_id=eu_id,
                url=ik.get("source_url", "manual-curation"),
                title=ik.get("source_title", ""),
                snippet=ik.get("snippet", ""),
                retrieved_at=now,
                search_query=f"{entity['name']} {field}",
            ))

            knowledge_units.append(KU(
                ku_id=f"KU-{len(knowledge_units) + 1:04d}",
                entity_key=entity_key,
                field=field,
                value=ik["value"],
                confidence=0.8,
                status="active",
                evidence_links=[eu_id],
                created_at=now,
                updated_at=now,
            ))
            covered_fields.add(field)

        for field in _resolve_applicable_fields(category, skeleton):
            if field not in covered_fields:
                gap_map.append(GU(
                    gu_id=f"GU-{len(gap_map) + 1:04d}",
                    entity_key=entity_key,
                    field=field,
                    status="open",
                    created_at=now,
                ))

    return {
        "entity_registry": entity_registry,
        "knowledge_units": knowledge_units,
        "evidence_units": evidence_units,
        "gap_map": gap_map,
        "category_saturation": category_saturation,
    }
